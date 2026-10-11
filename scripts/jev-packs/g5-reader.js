'use strict';
// Campaign J5 in docs/EXPERIMENT-PROTOCOL.md: Clef as hippo Z0's G5 reader. Rewording a question is a new lane there.
// Cases hold agent diffs, so they live in state/jev-cases (outside git); C:/z0-runs/s9/g5-cases.mjs builds them.
const fs = require('fs');
const os = require('os');
const path = require('path');

const CASES = path.join(os.homedir(), '.claude', 'state', 'jev-cases', 'g5-reader.json');
const CONTEXT = 'A coding agent was given `task` and made the change in `diff`, after running `commands`. `rule` is a project rule it was taught.';
// Masked, not skipped: a diff is long, and dropping every pair with one key-shaped string would bias the sample.
const SECRET = /sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._-]{16,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|eyJ[A-Za-z0-9._-]{20,}|xox[abpr]-[A-Za-z0-9-]{10,}/g;

const QUESTIONS = {
  breaks: {
    type: 'noul',
    instructions: {
      question: 'Does the change in `diff` break `rule`?',
      context: CONTEXT,
      focus: 'Judge the lines the diff adds or removes against the rule. A change that does what the rule asks obeys it, even when it also does other things. Ignore code the diff does not touch.',
    },
    criteria: {
      true: {
        what: 'The change does something the rule forbids, or leaves out something the rule requires for this kind of change.',
        examples: ['The rule says commit subjects start with a type prefix, and the commit subject in the diff has none.', 'The rule says each new page is added to the sitemap, and a new page is added with no sitemap entry.'],
      },
      false: {
        what: 'The change does what the rule asks, or the rule is about something this change does not do.',
        not_for: 'A change that obeys the rule but has other faults, such as a failing test or a style issue the rule does not mention.',
        examples: ['The rule asks for a changelog line, and the diff adds one.', 'The rule is about database migrations, and the diff only edits a README.'],
      },
    },
  },
  off_rule: {
    type: 'noul',
    instructions: {
      question: 'Is the change in `diff` outside what `rule` covers?',
      context: CONTEXT,
      focus: 'Ask whether the rule speaks to the kind of change made at all, not whether the change obeys it.',
    },
    criteria: {
      true: {
        what: 'The rule is about a kind of change this diff does not make, so it cannot be obeyed or broken here.',
        examples: ['The rule is about release tags, and the diff fixes a typo in a function.', 'The diff is empty.'],
      },
      false: {
        what: 'The diff makes the kind of change the rule speaks to, whether it obeys the rule or not.',
        examples: ['The rule is about how tests are named, and the diff adds a test.', 'The rule is about commit messages, and the diff carries a commit.'],
      },
    },
  },
};

const clip = (text, n) => String(text ?? '').replace(SECRET, '[masked]').slice(0, n);

function build(input) {
  const state = { task: clip(input.task, 1500), rule: clip(input.rule, 600), commands: clip(input.commands, 1500), diff: clip(input.diff, 8000) };
  return { state, questions: QUESTIONS };
}

// The label the bench scores is `fail`, so a pair Clef calls off the rule is not a flag.
const flag = (answers, thr) => (answers.breaks?.noul ?? 0) >= thr && (answers.off_rule?.noul ?? 0) < thr;
const positive = (expect) => expect.breaks;

const added = (diff) => String(diff).split('\n').filter((l) => l.startsWith('+') && !l.startsWith('+++')).join('\n').toLowerCase();
const baselines = {
  A0_checker: (input) => ({ breaks: input.checker === 'fail', off_rule: input.checker === 'na' }),
  A1_lazy: (input) => {
    const add = added(input.diff);
    const words = [...new Set(String(input.rule).toLowerCase().match(/[a-z]{5,}/g) ?? [])];
    return { breaks: add.length > 0 && !words.some((w) => add.includes(w)), off_rule: add.length === 0 };
  },
};

const cases = fs.existsSync(CASES) ? JSON.parse(fs.readFileSync(CASES, 'utf8')) : [];

module.exports = { name: 'g5-reader', build, cases, baselines, flag, positive, QUESTIONS };
