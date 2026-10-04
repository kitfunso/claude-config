// SHORTCUT: quote-aware split on && || ; | and newlines; no subshells or variable expansion. A full sh parser if real commands slip past.
const SEPARATORS = ['&&', '||', ';', '|', '\n']

export function segments(command) {
  const out = []
  let words = []
  let word = ''
  let hasWord = false
  let quote = null
  const endWord = () => {
    if (hasWord) words.push(word)
    word = ''
    hasWord = false
  }
  for (let i = 0; i < command.length; i++) {
    const c = command[i]
    if (quote !== null) {
      if (c === quote) quote = null
      else if (c === '\\' && quote === '"' && i + 1 < command.length) word += command[++i]
      else word += c
    } else if (c === '"' || c === "'") {
      quote = c
      hasWord = true
    } else if (c === '\\' && i + 1 < command.length) {
      word += command[++i]
      hasWord = true
    } else if (SEPARATORS.some(s => command.startsWith(s, i))) {
      endWord()
      if (words.length > 0) out.push(words)
      words = []
      i += SEPARATORS.find(s => command.startsWith(s, i)).length - 1
    } else if (c === ' ' || c === '\t' || c === '\r') endWord()
    else {
      word += c
      hasWord = true
    }
  }
  endWord()
  if (words.length > 0) out.push(words)
  return out
}

const isAbsolute = p => /^([a-zA-Z]:)?[\\/]/.test(p)
// Git Bash spells C:\ as /c/, which a process spawned without a shell cannot read.
const nativePath = p => p.replace(/^\/([a-zA-Z])(?=\/|$)/, '$1:')
const joinPath = (base, dir) =>
  nativePath(isAbsolute(dir) || base === undefined ? dir : `${base.replace(/[\\/]$/, '')}/${dir}`)

const TOOLS = { git: /(^|[\\/])git(\.exe)?$/i, gh: /(^|[\\/])gh(\.exe)?$/i, npm: /(^|[\\/])npm(\.cmd)?$/i }

// Each git, gh or npm call with the directory it runs in, as far as cd, -C and --prefix say.
export function toolCalls(command, home) {
  const expand = p => (home !== undefined && /^~([\\/]|$)/.test(p) ? home + p.slice(1) : p)
  const calls = []
  let cwd
  for (const words of segments(command)) {
    if (words[0] === 'cd' && words[1] !== undefined) {
      cwd = joinPath(cwd, expand(words[1]))
      continue
    }
    let i = 0
    while (i < words.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(words[i])) i++
    const tool = Object.keys(TOOLS).find(t => TOOLS[t].test(words[i] ?? ''))
    if (tool === undefined) continue
    let dir = cwd
    let repo
    const args = []
    for (i++; i < words.length; i++) {
      const w = words[i]
      if (tool === 'git' && args.length === 0 && w === '-C') dir = joinPath(dir, expand(words[++i] ?? ''))
      else if (tool === 'git' && args.length === 0 && w === '-c') i++
      else if (tool === 'npm' && w === '--prefix') dir = joinPath(dir, expand(words[++i] ?? ''))
      else if (tool === 'npm' && w.startsWith('--prefix=')) dir = joinPath(dir, expand(w.slice(9)))
      else if (tool === 'gh' && (w === '-R' || w === '--repo')) repo = words[++i]
      else if (tool === 'gh' && w.startsWith('--repo=')) repo = w.slice(7)
      else args.push(w)
    }
    calls.push({ tool, cwd: dir, repo, args })
  }
  return calls
}

const positionals = (args, valued = []) => {
  const out = []
  for (let i = 0; i < args.length; i++) {
    if (valued.includes(args[i])) i++
    else if (!args[i].startsWith('-')) out.push(args[i])
  }
  return out
}
const has = (args, ...flags) => args.some(a => flags.includes(a))
const valueOf = (args, ...flags) => {
  const i = args.findIndex(a => flags.includes(a))
  return i === -1 ? undefined : args[i + 1]
}
const isReleaseRef = ref => /^(refs\/tags\/|v\d)/.test(ref)
const claimBranch = name => (name ? [{ mode: 'claim', branch: name }] : [])

function pushActions(args) {
  const isDelete = has(args, '-d', '--delete')
  const out = has(args, '--tags', '--follow-tags') ? [{ mode: 'claim', release: true }] : []
  const refs = positionals(args, ['-o', '--push-option', '--repo', '--receive-pack', '--exec']).slice(1)
  if (refs.length === 0 && !has(args, '--tags', '--all', '--mirror', '-d', '--delete')) out.push({ mode: 'claim', current: true })
  for (const raw of refs) {
    const ref = raw.replace(/^\+/, '')
    const mode = isDelete || ref.startsWith(':') ? 'check' : 'claim'
    const dst = (ref.includes(':') ? ref.slice(ref.indexOf(':') + 1) : ref).replace(/^refs\/heads\//, '')
    if (isReleaseRef(dst)) out.push({ mode, release: true })
    else if (dst === 'HEAD') out.push({ mode, current: true })
    else if (dst !== '') out.push({ mode, branch: dst })
  }
  return out
}

function gitActions([sub, ...rest]) {
  if (sub === 'checkout' || sub === 'switch') return claimBranch(valueOf(rest, '-b', '-B', '-c', '-C', '--create', '--force-create', '--orphan'))
  if (sub === 'worktree') return rest[0] === 'add' ? claimBranch(valueOf(rest, '-b', '-B')) : []
  if (sub === 'branch') {
    const plain = rest.every(a => !a.startsWith('-') || ['-f', '--force', '-t', '--track', '--no-track'].includes(a))
    return plain ? claimBranch(positionals(rest)[0]) : []
  }
  if (sub === 'tag') {
    if (has(rest, '-d', '--delete', '-l', '--list', '-v', '--verify')) return []
    const name = positionals(rest, ['-m', '--message', '-F', '--file', '-u', '--local-user'])[0]
    return name !== undefined && isReleaseRef(name) ? [{ mode: 'claim', release: true }] : []
  }
  return sub === 'push' ? pushActions(rest) : []
}

const MERGE_VALUED = ['-t', '--subject', '-b', '--body', '-F', '--body-file', '--match-head-commit', '-A', '--author-email']

function ghActions([noun, verb, ...rest]) {
  if (noun === 'release' && verb === 'create') return [{ mode: 'claim', release: true }]
  if (noun !== 'pr') return []
  if (verb === 'create') {
    const head = valueOf(rest, '-H', '--head')?.replace(/^[^:]+:/, '')
    return head ? claimBranch(head) : [{ mode: 'claim', current: true }]
  }
  if (verb !== 'merge') return []
  const target = positionals(rest, MERGE_VALUED)[0]
  if (target === undefined) return [{ mode: 'check', current: true }]
  return [/^#?\d+$|\/pull\/\d+/.test(target) ? { mode: 'check', pr: target.replace(/^#/, '') } : { mode: 'check', branch: target }]
}

function npmActions(args) {
  if (args[0] === 'version' && positionals(args.slice(1)).length > 0) return [{ mode: 'claim', release: true }]
  return args[0] === 'publish' && !has(args, '--dry-run') ? [{ mode: 'claim', release: true }] : []
}

const BY_TOOL = { git: gitActions, gh: ghActions, npm: npmActions }

// What the command would take (claim) or touch (check), before branch names are resolved.
export const actions = (command, home) =>
  toolCalls(command, home).flatMap(c => BY_TOOL[c.tool](c.args).map(a => ({ ...a, cwd: c.cwd, repo: c.repo })))
