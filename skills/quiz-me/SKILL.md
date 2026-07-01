---
name: quiz-me
description: |
  Forcing function for learning what just shipped. Reads a recent diff,
  generates 5 multiple-choice questions plus 1 explain-back prompt, quizzes
  Keith, grades, and gates future feature work on a passing score. Use when
  asked to "quiz me", "test my understanding", "/quiz-me", "force me to
  learn", or as a mandatory hook at the ship stage of /dev-framework-rl.
triggers:
  - quiz me
  - quiz-me
  - test my understanding
  - force me to learn
  - learning gate
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
---

# /quiz-me — Learning Gate

You are administering a **closed-book quiz** to Keith on code that was just built.
The point is to surface gaps before they compound. Don't help. Don't hint. Don't
reveal answers until after the attempt is recorded.

The CLI lives at `~/.claude/skills/quiz-me/scripts/quiz.py` and stores data in
`~/.claude/quiz-me/{deck,results}.jsonl`. Always invoke via:

```bash
python ~/.claude/skills/quiz-me/scripts/quiz.py <subcommand> ...
```

## Mode dispatch

Parse the user's input:

- `/quiz-me` (no args) → **Quiz due cards** (spaced repetition pull, default 3)
- `/quiz-me from-diff [REF]` → **Generate + quiz** from a git diff (default: `HEAD`)
- `/quiz-me from-feature "<name>"` → **Generate + quiz** from a named feature (Claude picks the diff or asks)
- `/quiz-me gate` → **Check gate**: exit 0 pass, 1 blocked, print reasons
- `/quiz-me stats` → **Show stats**
- `/quiz-me add` → **Manual add** (ask user for fields, store one card)

---

## Generate + quiz (`from-diff`, `from-feature`)

### Step 1 — Read the source material

For `from-diff [REF]`:
```bash
git log -1 --format="%H %s" "${REF:-HEAD}"
git show --stat "${REF:-HEAD}"
git show "${REF:-HEAD}"
```

For `from-feature "<name>"`: find the most recent matching commit
(`git log --grep="<name>" -i --oneline -5`) and confirm with the user which to
quiz on. If nothing matches, ask which file or PR to use.

### Step 2 — Pick concepts a junior engineer would need to understand

Read the diff carefully. Identify **3-5 concepts** where understanding is
non-obvious. Not surface-level ("what does this function do?") — depth
("why this approach over X?", "what does this guarantee?", "what breaks if
this assumption is wrong?", "where is the invariant maintained?").

Skip trivial concepts (renames, formatting, dependency bumps). If the diff is
too thin to generate 3 real questions, tell the user and stop — don't pad.

### Step 3 — Generate cards

For each concept, generate **one MC card**:
- A question that has exactly one correct answer
- 4 options including the correct one. **Plausible distractors** — common
  misconceptions, adjacent-but-wrong answers. Not obvious traps.
- A one-line explanation pointing to `file:line` where the answer lives
- `--source-ref` set to `<file>:<line>` or the commit SHA

Then add **one explain-back card** on the highest-stakes concept:
- Prompt asks the user to explain in their own words (3-5 sentences)
- Rubric lists 2-4 concrete things a passing answer must mention

Store each via:
```bash
python ~/.claude/skills/quiz-me/scripts/quiz.py add-mc \
  --feature "<feature-name-or-commit-sha-short>" \
  --concept "<short-label>" \
  --question "<question>" \
  --options "<opt A>|<opt B>|<opt C>|<opt D>" \
  --answer <0-indexed-int> \
  --explanation "<one line + file:line>" \
  --source-ref "<file:line>"

python ~/.claude/skills/quiz-me/scripts/quiz.py add-explain \
  --feature "<same>" \
  --concept "<short-label>" \
  --prompt "<what to explain>" \
  --rubric "must mention: X, Y, Z" \
  --source-ref "<file:line>"
```

Capture the returned card IDs — you need them in step 4.

### Step 4 — Run the quiz (interactive, one card at a time)

For each MC card (in the order created), use AskUserQuestion:
- Question text = the card's `question`
- 4 options = the card's `options` (in original order — do NOT reshuffle, and
  do NOT mark the correct one)
- header: short concept label
- Do not preface the question with hints, code excerpts, or "this is about X"

After the user answers:
1. Compare to the correct index. Score = `1.0` if match, else `0.0`.
2. Record:
   ```bash
   python ~/.claude/skills/quiz-me/scripts/quiz.py record \
     --card-id <id> --score <0.0|1.0> --feature "<feature>"
   ```
3. Reveal: ✓ or ✗, the correct answer, the explanation, the source ref.

For the explain-back card:
- Ask the user to type their explanation (use AskUserQuestion with a single
  "Type your explanation" option pointing to the rubric prompt, or just say
  "Explain in your own words: <prompt>. Type your answer.")
- Read the response. Grade against the rubric:
  - All rubric items mentioned and correct → `1.0`
  - Most mentioned, minor gaps → `0.7`
  - Major gaps or fundamentally wrong → `0.3`
  - Empty / "I don't know" → `0.0`
- Be honest. Don't grade-inflate. The whole point is the gate.
- Record via `quiz.py record`.
- Reveal the rubric and what was missed.

### Step 5 — Final report

After all cards:
- Total score (X / N correct, average %)
- List what was missed with `file:line` for follow-up reading
- Run `python ~/.claude/skills/quiz-me/scripts/quiz.py gate` and report the
  verdict. If BLOCKED, list reasons.

---

## Quiz due cards (`/quiz-me` no args)

```bash
python ~/.claude/skills/quiz-me/scripts/quiz.py due --count 3 --json
```

Parse the JSON. For each card, run it through the same Step 4 loop above.
This is the spaced-repetition pass — keeps old knowledge from decaying.

If `no cards due`, say so. Don't invent cards.

---

## Gate (`/quiz-me gate`)

```bash
python ~/.claude/skills/quiz-me/scripts/quiz.py gate
```

Report verdict verbatim. Exit code is the contract for hook integration:
- `0` → safe to proceed with new feature work
- `1` → blocked, must quiz before next feature

Do NOT auto-quiz on a blocked gate inside this mode. The user runs
`/quiz-me` to clear.

---

## Stats (`/quiz-me stats`)

```bash
python ~/.claude/skills/quiz-me/scripts/quiz.py stats
```

Print verbatim. If the user wants more detail, offer `--json`.

---

## Manual add (`/quiz-me add`)

Use AskUserQuestion to gather card type (MC vs explain), then the fields.
Store via the same CLI. Confirm the card ID.

---

## Integration with /dev-framework-rl (ship stage hook)

When invoked from the ship stage of `/dev-framework-rl`:
1. Run `from-diff HEAD` against the episode's final commit.
2. After the quiz, run `gate`.
3. Return the gate verdict to the orchestrator as the result of this hook.
4. A BLOCKED gate is a ship-stage blocker — the orchestrator must NOT advance
   to deploy until the user clears it.

Save the quiz summary into the manifest's `quiz_me_summary` field (analogous
to `ship_check_summary`).

---

## Hard rules

- **Never reveal an MC answer before the user attempts.** Not in the question,
  not in the options ordering, not in any preamble.
- **Never grade-inflate the explain-back.** A vague answer scores 0.3 even if
  it sounds confident. The forcing function only works if the grade is honest.
- **Never auto-pass the gate.** If a card was failed, the user re-attempts it.
- **Don't pad to N questions if the diff doesn't support N real ones.** Better
  to ask 2 deep questions than 5 surface ones.
- **Source refs are mandatory.** Every card points to `file:line` so the user
  can go read the answer after failing.
