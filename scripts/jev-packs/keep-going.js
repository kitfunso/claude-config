'use strict';
// Campaign J3 in docs/EXPERIMENT-PROTOCOL.md. Rewording a question is a new lane there.
// Cases hold transcript text, so they live in state/jev-cases (outside git); the builder is named in J3.
const fs = require('fs');
const os = require('os');
const path = require('path');

const CASES = path.join(os.homedir(), '.claude', 'state', 'jev-cases', 'keep-going.json');
const CONTEXT = '`reply_tail` is the last part of a reply that ended an AI coding agent\'s turn. `prompt` is the end of the user\'s last message. The user has told the agent to keep working through approved work without stopping to ask permission.';

const QUESTIONS = {
  hands_back: {
    type: 'noul',
    instructions: {
      question: 'Does `reply_tail` end by handing a next step or a decision back to the user, instead of doing it or reporting it done?',
      context: CONTEXT,
      focus: 'Judge only how the reply ends: its last two or three sentences. Ask-for-a-go words that are quoted, or mentioned earlier in the reply, do not count.',
    },
    criteria: {
      true: {
        what: 'The ending asks for a go, a yes or a pick between options; offers more work ("want me to", "shall I", "say the word"); names the next step and stops; or says it is waiting for the user.',
        examples: ['Say yes and I will refactor the parser next.', 'Should I also update the changelog, or leave it?', 'Next up: the migration script, whenever suits you.'],
      },
      false: {
        what: 'The ending reports results or status, says the user has nothing to do, or says the agent is waiting on a running job, a timer or a monitor it set up itself.',
        not_for: 'An optional tweak the user may make to a finished draft, an offer made mid-reply when the ending is status, and quoted phrases.',
        examples: ['All 40 tests pass and the branch is pushed.', 'The import job finishes near 14:00 and a watcher wakes me when it exits.', 'Done. Nothing needs you.'],
      },
    },
  },
  blocker: {
    type: 'noul',
    instructions: {
      question: 'Does `reply_tail` give a reason why the step it leaves for the user truly needs the user?',
      context: CONTEXT,
      focus: 'A real reason is one of: deleting or overwriting data, files or branches; changing a live database schema; spending money or changing billing; publishing, posting, sending, deploying or merging to something live or public; something only the user can do (log in, enter a credential, sign, a physical step, typing code the project says he must write himself, a fact only he knows); a full rewrite of a hand-maintained rules or memory file. Reversible local work is never a real reason.',
    },
    criteria: {
      true: {
        what: 'The reply names at least one of those reasons for the step it hands back.',
        examples: ['Pruning the old backups deletes them for good, so I need a yes.', 'The upgrade moves you to the paid tier; confirm and I will switch.', 'Plug the sensor into port 2, then tell me.'],
      },
      false: {
        what: 'No reason is given, or the step is local and reversible: editing code, running tests, local commits, writing docs or reports, reading or checking things.',
        not_for: 'A note that the step is reversible or needs no key, and the agent\'s own caution or preference.',
        examples: ['Say go and I will tidy the README.', 'Want me to rerun the benchmark?', 'Nothing here needs you.'],
      },
    },
  },
  asked_only: {
    type: 'noul',
    instructions: {
      question: 'Does `prompt` only ask a question or ask for status, advice or ideas, rather than ask the agent to carry out work?',
      context: '`prompt` is the end of the user\'s last message to an AI coding agent. A message telling the agent to continue an earlier task counts as asking for work.',
      focus: 'Judge the request, not the tone. Swearing or frustration does not change the answer. Writing or editing a document counts as work.',
    },
    criteria: {
      true: {
        what: 'A question about status, facts, past work or opinion, or a request for advice, options, ideas or an explanation.',
        examples: ['how far along is the import?', 'which database would you pick for this?', 'explain why the cache misses'],
      },
      false: {
        what: 'An instruction to do, fix, build, run, write, ship or continue work, including a bare go or continue.',
        not_for: 'A question attached to a work instruction, such as "fix it, why is it broken?".',
        examples: ['go', 'fix the flaky test and push', 'carry on with the remaining tasks'],
      },
    },
  },
};

const cases = JSON.parse(fs.readFileSync(CASES, 'utf8'));

// The hook's job: block a stop that hands work back when no real blocker exists and the user asked for work.
const flag = (a, thr) => a.hands_back.noul >= thr && a.blocker.noul < thr && a.asked_only.noul < thr;
const positive = (e) => e.hands_back && !e.blocker && !e.asked_only;

const baselines = {
  // keep_going.verdict() and the lazy upgrade, both precomputed by the builder from the real hook module.
  A0_hook: (input) => input.a0,
  A1_lazy: (input) => input.a1,
};

function build(input) {
  return {
    state: { prompt: String(input.prompt).slice(-300), reply_tail: String(input.reply_tail).slice(-700) },
    questions: QUESTIONS,
  };
}

module.exports = { name: 'keep-going', build, cases, baselines, flag, positive };
