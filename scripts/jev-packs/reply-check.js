'use strict';
// Campaign J4 in docs/EXPERIMENT-PROTOCOL.md. Rewording a question is a new lane there.
// Cases hold transcript text, so they live in state/jev-cases (outside git); the builder is named in J4.
const fs = require('fs');
const os = require('os');
const path = require('path');

const CASES = path.join(os.homedir(), '.claude', 'state', 'jev-cases', 'reply-check.json');
const CONTEXT = '`reply` is the opening of an AI coding agent\'s reply to the user, cut at about 1,500 characters. `prompt` is the end of the user\'s message it answers.';

const QUESTIONS = {
  sweeping: {
    type: 'noul',
    instructions: {
      question: 'Does `reply` claim complete coverage (everything, every item, all, nothing left, none remain) without showing what was checked to support it?',
      context: CONTEXT,
      focus: 'Judge completeness claims the agent makes about its own work or findings. A claim is supported when the reply lists the items, names the checks, gives counts or shows the evidence. Ignore every or all inside a description of how a system works, inside quoted words, or inside a draft written for the user.',
    },
    criteria: {
      true: {
        what: 'A blanket claim of completeness with no list, counts or checks behind it, or a claim wider than the evidence shown.',
        examples: ['Everything is migrated and working now.', 'I went through the whole codebase and there are no other callers.', 'All edge cases are covered.'],
      },
      false: {
        what: 'No completeness claim, or a completeness claim followed by the items or checks that back it.',
        not_for: 'A description of a design, a quote of the user\'s words, and a claim that comes with its list.',
        examples: ['All three endpoints return 200: login, health and items.', 'No, the cache is not the cause.', 'Each request carries a trace id by design.'],
      },
    },
  },
  not_answer_first: {
    type: 'noul',
    instructions: {
      question: 'Does the first sentence of `reply` fail to give the answer or result the user is waiting for?',
      context: CONTEXT,
      focus: 'Judge the first sentence only, against what `prompt` asks. When the prompt asks the agent to continue or do work, the answer is the result or state of that work. A short label is fine when the answer follows in the same sentence.',
    },
    criteria: {
      true: {
        what: 'The first sentence is a preamble, an announcement of what is coming, an acknowledgement or apology on its own, process narration, or news about something other than what the user asked.',
        examples: ['Good question, let me walk through it.', 'I looked into this in some detail.', 'Below is an overview of the situation.'],
      },
      false: {
        what: 'The first sentence states the answer, verdict or result, including a bare yes or no, or a heading that is itself the answer.',
        not_for: 'A label such as "short answer:" with the answer in the same sentence, and a one-line label that directly introduces a draft the user asked for.',
        examples: ['No, the cache is not the cause.', 'Short answer: yes, it ships Friday.', 'The deploy failed on the migration step.'],
      },
    },
  },
};

const cases = JSON.parse(fs.readFileSync(CASES, 'utf8'));

const BROAD = /\b(everything|every (?:test|file|check|fix|item|hook|table|page|case|one)|all (?:done|tests?|checks?|green|fixed|good|clean|pass)|nothing (?:left|broke|missing|else)|everywhere|none (?:left|remain))\b/i;
const OPENER = /^\W*(here(?:'s| is)|let me|i'll|i will|fair\b|ok(?:ay)?\b|right\b|understood|got it|you're right|good (?:question|catch)|first,|background|context|<verification>)/i;
const firstSentence = (text) => String(text).trim().split(/(?<=[.!?])\s/)[0];

const baselines = {
  // Today's reply_check.py SWEEPING regex, precomputed by the builder; the hook has no answer-first check.
  A0_hook: (input) => input.a0,
  A1_regex: (input) => ({ sweeping: BROAD.test(input.reply), not_answer_first: OPENER.test(firstSentence(input.reply)) }),
};

function build(input) {
  return { state: { prompt: String(input.prompt).slice(-300), reply: String(input.reply).slice(0, 1500) }, questions: QUESTIONS };
}

module.exports = { name: 'reply-check', build, cases, baselines };
