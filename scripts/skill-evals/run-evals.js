export const meta = {
  name: 'skill-evals',
  description: 'Run a skill eval split by blind sub-agents, grade each reply against its rubric, and report pass rates with noise, headroom, discrimination and grader checks',
  phases: [
    { title: 'Run', detail: 'with the skill on every case; without it on the cases named in args.without', model: 'opus' },
    { title: 'Grade', detail: 'one blind grader per reply; a second on the regrade splits', model: 'opus' },
  ],
}

// args come from build_run.py's args.json: root, skill, desc, runs, without, regrade_splits, cases.
const ROOT = args.root
const SKILL = args.skill
const COPY = `${ROOT}\\skill\\${SKILL}`
const RUNS = args.runs || 3
const CASES = args.cases
const WITHOUT = new Set(args.without || [])
const REGRADE = new Set(args.regrade_splits || [])

const RUN_SCHEMA = {
  type: 'object',
  properties: {
    reply: { type: 'string', description: 'The full message you would send the user' },
    skill_used: { type: 'boolean' },
    files_read: { type: 'array', items: { type: 'string' } },
    files_written: { type: 'array', items: { type: 'string' } },
  },
  required: ['reply', 'skill_used', 'files_read', 'files_written'],
}
const GRADE_SCHEMA = {
  type: 'object',
  properties: {
    criteria: {
      type: 'array',
      items: {
        type: 'object',
        properties: { n: { type: 'integer' }, pass: { type: 'boolean' }, reason: { type: 'string' } },
        required: ['n', 'pass', 'reason'],
      },
    },
    pass: { type: 'boolean' },
    summary: { type: 'string' },
  },
  required: ['criteria', 'pass', 'summary'],
}

const projOf = it => `${ROOT}\\proj\\${it.msg}-${it.arm}-${it.run}`

function runPrompt(it) {
  const msg = `${ROOT}\\msgs\\${it.msg}.txt`
  const proj = projOf(it)
  const files = it.writes
    ? `Your project folder is ${proj}. You may create files inside it with Write; create nothing anywhere else and leave every other file as it is.`
    : 'Answer in words and leave every file as it is.'
  const rounds = it.writes ? 'eight' : 'five'
  if (it.arm === 'with') {
    return [
      `Read the file ${msg}. It holds a message a user has just sent you in a chat session; answer it as you would in that chat.`,
      '',
      'This session has one skill installed:',
      `- ${SKILL}: ${args.desc}`,
      `Its files are in ${COPY}. If the skill applies to the message, use it: read ${COPY}\\SKILL.md first, then the files it points you to for this question. If it does not apply, answer without it.`,
      '',
      `Use Read, Glob and Grep${it.writes ? ', and Write' : ''} only. Every Read, Glob and Grep call names an explicit path inside ${COPY} or the message file; never read or search any other folder, and never call Glob or Grep without a path. After reading the message file, use at most ${rounds} further rounds of tool calls (parallel calls in one round count once), then answer. ${files}`,
      '',
      'Return reply (the full message you would send the user), skill_used (true only if you read SKILL.md and followed it), files_read (every file path you read) and files_written (every file you created, else empty).',
    ].join('\n')
  }
  return [
    `Read the file ${msg}. It holds a message a user has just sent you in a chat session; answer it as you would in that chat, from your own knowledge.`,
    '',
    `That file is the only one you read: no skill, no Skill tool, nothing under ~/.claude/skills, no other folder. ${files}`,
    '',
    'Return reply (the full message you would send the user), skill_used (false; true only if you used a skill anyway), files_read (every file path you read) and files_written (every file you created, else empty).',
  ].join('\n')
}

function gradePrompt(it, out, second) {
  const page = it.writes
    ? ['', `The run could also write files into its project folder ${projOf(it)}. Glob that folder and read every file in it; grade the reply and those files together, as the rubric says. An empty or missing folder means the reply stands alone.`]
    : []
  return [
    `Grade one reply against a fixed rubric. Read ${it.case_dir}\\case.yaml: execution.prompt is the message the user sent, and the grader entry named criteria holds the rubric, a short statement of the right answer followed by numbered criteria.`,
    ...page,
    '',
    'The reply to grade sits between the markers:',
    '<<<REPLY',
    out.reply,
    'REPLY>>>',
    '',
    'Judge each numbered criterion on what the reply says. A criterion passes when the reply states it, or a clear equivalent in its own words. It fails on a vague gesture, on a hedge that leaves the wrong path open, or when another part of the reply contradicts it. The reply may or may not cite a protocol document; a citation earns nothing by itself. Grade every numbered criterion, in order.',
    ...(second ? ['', 'You are an independent second reader; reach your own verdict.'] : []),
    '',
    'Return criteria (one entry per numbered criterion: n, pass, and a one-sentence reason), pass (true only if every criterion passes) and summary (one sentence).',
  ].join('\n')
}

const ITEMS = []
for (let run = 1; run <= RUNS; run++)
  for (const c of CASES)
    for (const arm of ['with', 'without'])
      if (arm === 'with' || WITHOUT.has(c.name))
        ITEMS.push({ ...c, arm, run })
log(`${ITEMS.length} runs queued across ${CASES.length} cases`)

const gradeOpts = (it, tag) => ({ label: `${tag} ${it.msg} ${it.arm} #${it.run}`, phase: 'Grade', schema: GRADE_SCHEMA, model: 'opus', effort: 'high' })

phase('Run')
const results = await pipeline(
  ITEMS,
  it => agent(runPrompt(it), { label: `run ${it.msg} ${it.arm} #${it.run}`, phase: 'Run', schema: RUN_SCHEMA, model: 'opus', effort: 'high' }),
  (out, it) => {
    if (!out) return { ...it, out: null, g: null, g2: null }
    const second = REGRADE.has(it.split) ? agent(gradePrompt(it, out, true), gradeOpts(it, 'grade2')) : Promise.resolve(null)
    return Promise.all([agent(gradePrompt(it, out, false), gradeOpts(it, 'grade')), second])
      .then(([g, g2]) => ({ ...it, out, g, g2 }))
  },
)
const all = results.map((r, i) => r || { ...ITEMS[i], out: null, g: null, g2: null })

const allPass = (g, n) => !!g && (g.criteria || []).length === n && g.criteria.every(x => x.pass)

function score(r) {
  const flags = []
  if (!r.out) return { ok: false, fired: null, flags: ['no reply'] }
  const files = r.out.files_read || []
  const fired = !!r.out.skill_used || files.some(f => /SKILL\.md$/i.test(f))
  const norm = p => p.replace(/\//g, '\\').toLowerCase()
  if (files.some(f => /[\\/]evals(-test)?[\\/]|\.claude[\\/]skills/i.test(f))) flags.push('read rubric or live skill')
  if (files.some(f => !norm(f).startsWith(norm(ROOT) + '\\'))) flags.push('read outside run folder')
  if (r.arm === 'without' && (fired || files.some(f => norm(f).startsWith(norm(COPY))))) flags.push('used skill')
  if (!r.g) { flags.push('no grade'); return { ok: false, fired, flags } }
  const crit = r.g.criteria || []
  if (crit.length !== r.n_criteria) flags.push(`graded ${crit.length} of ${r.n_criteria}`)
  const ok = allPass(r.g, r.n_criteria)
  if (ok !== !!r.g.pass) flags.push('grader overall disagrees')
  const second = r.g2 ? allPass(r.g2, r.n_criteria) : null
  return { ok, fired, flags, second }
}

const scored = all.map(r => ({ r, s: score(r) }))
const rate = xs => {
  const n = xs.length, k = xs.filter(x => x.s.ok).length, p = n ? k / n : 0
  return { k, n, p: +p.toFixed(3), se: +Math.sqrt(p * (1 - p) / Math.max(n, 1)).toFixed(3) }
}

const splits = {}
for (const split of [...new Set(CASES.map(c => c.split))]) {
  const mine = scored.filter(x => x.r.split === split)
  const w = mine.filter(x => x.r.arm === 'with'), wo = mine.filter(x => x.r.arm === 'without')
  const regraded = w.concat(wo).filter(x => x.s.second !== null && x.s.second !== undefined)
  const withRate = rate(w)
  splits[split] = {
    with: withRate,
    without: wo.length ? rate(wo) : null,
    trigger_ok: w.filter(x => x.s.fired === x.r.expect_fire).length,
    flagged: mine.filter(x => x.s.flags.length).length,
    noise_2se: +(2 * withRate.se).toFixed(3),
    headroom: withRate.p > 0.95 ? 'saturated: add harder cases before climbing on this split' : 'ok',
    grader_agreement: regraded.length ? `${regraded.filter(x => x.s.second === x.s.ok).length}/${regraded.length}` : 'not regraded',
  }
}

const rows = CASES.map(c => {
  const mine = scored.filter(x => x.r.name === c.name)
  const w = mine.filter(x => x.r.arm === 'with'), wo = mine.filter(x => x.r.arm === 'without')
  const kw = w.filter(x => x.s.ok).length, kwo = wo.filter(x => x.s.ok).length
  const diag = []
  if (w.length && kw === 0) diag.push('always fails: check the case and grader before the skill')
  else if (kw < w.length) diag.push('noisy')
  if (wo.length && kwo / wo.length >= kw / Math.max(w.length, 1)) diag.push('no discrimination: the model passes without the skill')
  return {
    name: c.name, split: c.split,
    with: `${kw}/${w.length}`,
    without: wo.length ? `${kwo}/${wo.length}` : 'not rerun',
    trigger: `${w.filter(x => x.s.fired === c.expect_fire).length}/${w.length}`,
    diag,
    flags: mine.flatMap(x => x.s.flags.map(f => `${x.r.arm}#${x.r.run}: ${f}`)),
  }
})

// Test-split failures name criterion numbers only, so the session that edits the skill never reads the rubric.
const failures = scored.filter(x => !x.s.ok).map(x => ({
  name: x.r.name, split: x.r.split, arm: x.r.arm, run: x.r.run,
  failed: !x.r.g ? ['no grade']
    : (x.r.g.criteria || []).filter(c => !c.pass).map(c => (x.r.split === 'test' ? `${c.n}` : `${c.n}: ${c.reason}`)),
  flags: x.s.flags,
}))

for (const [split, s] of Object.entries(splits))
  log(`${split}: with ${s.with.k}/${s.with.n} (2 SE ${s.noise_2se}), without ${s.without ? `${s.without.k}/${s.without.n}` : 'not rerun'}, trigger ${s.trigger_ok}/${s.with.n}, graders agree ${s.grader_agreement}, headroom ${s.headroom}`)
return { splits, rows, failures }
