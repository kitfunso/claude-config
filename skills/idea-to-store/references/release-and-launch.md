# Release and launch

## 1. Release (stage 6)

`/build-release` is written for Phzse; its lessons generalise. Read it once, then follow this order for any app.

1. **Version and build numbers.** Marketing version in one place (`package.json` or the platform config), build numbers monotonic on both platforms, and the CI fetches the last store build number and adds one (Phzse commit `88fc60b` does this from App Store Connect). Enumerate every file that carries the version before bumping; the dev-framework audit rule `version-bump-targets` is the list.
2. **Lockfile and doctor.** `npm ci` clean and `npx cap doctor` clean before the CI runs, so the rented mac does not discover the drift.
3. **Release notes file** committed, and passed to the CI's publish step. Empty notes are a refused submission.
4. **CI run.** Start Codemagic from the app's settings page and pick the workflow; when the workflow list is stale, click the refresh icon beside it. Watch the build to the upload line and record the delivery id in `docs/LAUNCH.md`.
5. **Internal tracks first.** TestFlight internal group and Play internal testing. Install on the real phones from both.
6. **The app's own S-gate.** Every app names one test that only a real phone can pass (locked-screen capture for a recorder, a full day of sync for a tracker, a payment round trip for a paid app) with a numeric pass bar. Run it, write the numbers in `docs/LAUNCH.md`.
7. **External test.** TestFlight external needs the test information page; Play needs the closed test that started in stage 1. Twelve testers on Play is a recruiting task, so the tester list is built during stage 4, not now.
8. **Reviewer path against production.** Delete the app, install the store build, sign in the way the review notes say, do the first action, and read the result. Phzse's web login was broken for weeks by a CI env block and a friend found it; eaves' first recording fails until the model key is set. The screenshot goes in `docs/LAUNCH.md`.
9. **Submit.** Keith presses both buttons. The agent pastes nothing that needs a password.

Secrets on CI go in through the platform's secret store (Codemagic environment groups), pasted by Keith from the clipboard; the agent names the variable and never the value.

## 2. Launch day (stage 7)

- Phased rollout on both stores where the store offers it, starting at the smallest percentage. A halt is the rollback for the app; the backend keeps its own rollback command from `system-design.md` section 8.
- The day-one watch, recorded in `docs/LAUNCH.md`: crash-free rate, error alerts, pipeline dead letters, vendor spend, the first reviews. Twenty-four hours, then a note.
- The film: `/product-launch-video`, from the real app, after the listing is live so the store link is real.
- The announcement follows `~/.claude/voice/` samples; the listing URL, one sentence of what it does, one screenshot.

## 3. Rejection playbook

A rejection is a message with a guideline number. Read the number in the guideline text (`store-prereqs.md` section 3), fix the cause in the repo, bump the build, and reply in Resolution Center with the change and where the reviewer can see it. The three common first-submission causes, in order: the reviewer could not sign in (demo account or backend keys), the privacy policy or labels did not match the app, and a permission or background mode had no explanation. A rejection for 4.2 needs a native capability shown in the notes, never an argument.

Never resubmit the same build for a rejection that names the binary.

## 4. After launch

- 7 days: errors, dead letters, spend, ratings. Reply to every review that reports a bug with the build that fixes it.
- 30 days: the PRD's success metric against its number, in one line, in `docs/LAUNCH.md`. A miss is a Stage 0 question, not a feature request.
- Update cadence decided and written down: what triggers a build (a crash, a store policy deadline, a feature) and who presses submit.
- Memory writeback: the app's memory file and `hippo remember ... --pin` carry the state, the store ids, and the lessons the stores taught this time. New store gotchas go into `store-prereqs.md` in this skill, one line each with the app and the date.
