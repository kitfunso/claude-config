---
name: build-release
description: Ships a Phzse or Brain Gym release end to end (version bump, checks, merge, Play publish, site deploy) and starts the Codemagic iOS/Android builds from a release tag with no browser, watching them through GitHub check runs. Use when asked to ship, release or submit a new Phzse or Brain Gym build, or after a merge that changes the app.
---

# Build Release

Ships a Phzse release: bump build numbers, build web assets, compile-check Android, commit, push, then start both Codemagic workflows. **CI builds and uploads the shipping artifacts.** The local gradle run is a pre-flight only, and the iOS IPA is never built here at all.

**Brain Gym runs a different lane: skip to "Brain Gym" at the end.** Both apps start Codemagic from a `release-*` tag (Phzse step 10, Brain Gym step 5), with no browser and no token. Keith's rule: he should not have to walk anyone through a release, and no step may wait on his hands. Run every step yourself, and never ask him for a browser click.

## Prerequisites

- Must be in the `$HOME/phzse` project directory
- Git must be on the correct branch (verify first, never assume)

## Steps

Execute these steps in order. Stop and report if any step fails.

### 1. Verify branch

```bash
git -C "$HOME/phzse" branch
```

Confirm you're on `master`. If not, warn the user before proceeding.

### 2. Read current versions

- **Android**: `android/app/build.gradle` holds `versionCode N` and `versionName "X.Y.Z"`.
- **iOS**: `ios/App/App.xcodeproj/project.pbxproj` holds `MARKETING_VERSION` in
  BOTH build configs. Its `CURRENT_PROJECT_VERSION` is dead weight.
- **In the app**: `src/lib/config.ts` holds `APP_VERSION`, the number the settings
  screen prints. It read 2.1.0 while 2.1.10 shipped, because nothing bumped it.

There is no iOS build number to read anywhere. Since commit d736ad4 the CI step
uses `PROJECT_BUILD_NUMBER`, Codemagic's own per-project build count, which only
ever goes up. Do not put one back in `codemagic.yaml` and do not go back to
`get-latest-build-number`: hardcoding caused two duplicate-cfBundleVersion 409s,
and the App Store Connect query caused a third by answering with the highest
build in the highest TestFlight train instead of the one being shipped.

### 3. Bump versions

- `android/app/build.gradle`: `versionCode` + 1, and `versionName` to the new release.
- `ios/App/App.xcodeproj/project.pbxproj`: `MARKETING_VERSION` to the same release,
  in both configs. Nothing else. The iOS build number sets itself in CI.
- `src/lib/config.ts`: `APP_VERSION` to the same release.

If any image changed, run `npm run icons` and commit what it writes.
`scripts/convert-icons.mjs` owns the icons, the eleven Android splash PNGs, the
three iOS ones and `public/icons/moon.png`. Nothing else may write those files.

### 4. Verify lockfile is in sync (CRITICAL: prevents Codemagic CI failure)

**If any dependency changed this session** (`npm install`, `npm audit fix`, version bumps, even indirect ones), run a REAL clean install. `npm ci --dry-run` PASSES FALSELY on lockfiles that real `npm ci` rejects (proven 2026-06-10: dry-run green locally, Codemagic failed with 27 "Missing: <pkg> from lock file" errors):

```bash
npm --prefix "$HOME/phzse" ci
```

This wipes node_modules and installs strictly from the lockfile, exactly what Codemagic runs. Takes a few minutes; that is the price of a trustworthy gate. If no dependency changed this session, `npm ci --dry-run` is an acceptable fast path.

If `npm ci` reports "Missing: <pkg> from lock file": incremental `npm install`/`npm audit fix` against an existing node_modules can leave stale subtree references with their platform-binary entries pruned (known npm lockfile bug), and `npm install` will NOT repair it. Regenerate from scratch:

```bash
rm package-lock.json && npm install   # full fresh resolution
npm ci                                # re-verify for real
```

Sanity-check the fresh lockfile records ALL platforms' optional binaries (Codemagic is macOS, local is Windows): `grep -c darwin-arm64 package-lock.json` must be non-zero.

If a peer dependency keeps dropping (e.g. `@testing-library/dom` pulled in by `@testing-library/react`), add it as an explicit `devDependency` so the lockfile pins it:
```bash
npm install --save-dev <missing-pkg>@<version>
```

### 5. Build web assets

```bash
npm --prefix "$HOME/phzse" run build
```

Wait for completion. This must succeed before proceeding.

### 6. Sync Capacitor

```bash
cd "$HOME/phzse" && npx cap sync android
```

### 7. Compile-check the Android build

```bash
"$HOME/phzse/android/gradlew" -p "$HOME/phzse/android" bundleRelease
```

30-60 seconds, must finish with `BUILD SUCCESSFUL`. This is a pre-flight, nothing
more. CI runs the same gradle task and fails the same way four minutes later, so
catch it here.

**The bundle that ships is built by CI, not by this command.** `android-release`
on Codemagic builds and signs its own, with the `phzse_upload_keystore` Codemagic
holds, and uploads it straight to Play. Do not copy the local `.aab` anywhere and
do not upload it by hand while CI works: two sources for one artifact is how a
`versionCode` drifts between the repo and the store.

### 8. Write the App Store release notes

Rewrite `store-assets/release-notes/en-GB.txt` to describe THIS release, in plain
words a user reads on the store page. Apple refuses a review submission when the
default locale has no `whatsNew`, and Codemagic's `publishing:` block has no key
for it, so the CI publish step reads this file. Build #172 died on a stale-empty
one. Show Keith the text before committing: it is public copy.

### 9. Stage, commit, and push

Stage all modified files (not untracked directories like `.gstack/` or `prototypes/`):

```bash
git add android/app/build.gradle ios/App/App.xcodeproj/project.pbxproj
```

Also stage any OTHER unstaged modified files from the current session (check `git status` first).

Commit with:

```
chore: bump to {VERSION_NAME} (Android build {NEW_BUILD})
```

Write the message with the Write tool and pass `git commit -F <file>`. Never use a
heredoc: the commit-msg hook denies the WHOLE compound command if any part of it
holds an em dash, so the heredoc never runs and `git commit -F` picks up a stale
file from an earlier session and ships a wrong message.

Then push:

```bash
git push
```

### 10. Upload to the stores

**Phzse: push a tag, no browser.** `git -C "$HOME/phzse" tag release-{VERSION_NAME}`
on the bump commit, then `git -C "$HOME/phzse" push origin release-{VERSION_NAME}`.
Since PR #11 (2026-10-15) `ios-release` and `android-release` start on `release-*`
through GitHub webhook 698407126 to `https://api.codemagic.io/hooks/69ab40d4cb7ed3e0ae357c3e`.
A plain push still starts nothing. Proven by `release-2.3.2`: iOS `6ad0994a12cce3cb996bb52d`
(Publish to App Store Connect 4m 48s) then Android `6ad0994a12cce3cb996bb52f`, both green,
no browser. Watch them with no login: Codemagic posts GitHub check runs on the tagged commit,
`gh api repos/kitfunso/phzse/commits/<sha>/check-runs` (app `codemagic-ci-cd`; the output
text lists every step). The two run one after the other. **A release must never wait on Keith's hands**: on
2026-10-15 the old Chrome route stalled 2.3.2 twice while he was out, because the
Claude in Chrome extension was off and the debugging port needs his Allow click. No
release goes through a browser. **Use ONE starter per release, never both, or each
workflow builds twice.** The tag is the default: it needs no token, and the check runs
show every step. To rerun a one-off failure, push a second tag on the same commit
(`release-{VERSION_NAME}-2`). On Phzse that reruns both workflows; if Android had
already passed, its rerun fails on the used versionCode, which changes nothing. The API script in "Starting a Codemagic build" also saves
failed-step logs and reruns known one-off failures by itself, so when
`CODEMAGIC_AUTH_TOKEN` is set you may run it for each workflow instead, with no tag.

- **iOS**: start the `ios-release` workflow in Codemagic. A plain push does NOT
  start a build; the tag or the script does (`--app 69ab40d4cb7ed3e0ae357c3e
  --workflow ios-release --branch master --report-step "Publish to App Store
  Connect"`). Since 46c90a9 the workflow submits
  for App Store review on its own and Apple releases on approval, so no manual
  App Store Connect step is left. It does not ask for TestFlight beta review:
  that submission runs first and 422s while the version train already holds a
  build in review, which cost build #171 its store submission. Removed in
  a2905ab. Do not add `submit_to_testflight` back. The submission runs from a
  script step, not a `publishing:` block, because only the script can pass the
  release notes (`--whats-new "@file:..."`), and Apple rejects a submission
  without them (8b7ff74).
- **Android**: start the `android-release` workflow the same way (`--workflow
  android-release --branch master`). It builds the bundle, signs it, and uploads it to the Play
  production track as a draft (`submit_as_draft: true`), so nothing reaches users
  until Keith presses the button. Nothing else is needed from you or from him.
  **This lane is proven end to end** by build `6aa0592a1dafc6b3c2e63184`
  (2026-09-08), which ran every step, `Build AAB` in 4m 0s, and got a real answer
  out of the Play API. Its steps summed to 6m 34s, so expect 6 to 7 minutes from
  the start, most of it gradle.
  **The one failure to expect is your own fault, and it is loud:**
  `Version code 118 has already been used`. Play refuses a `versionCode` it has
  seen, so step 3's bump is not optional and re-running the workflow on an
  already-published build number can never succeed. Read the number in
  `android/app/build.gradle` before starting the build.
  **`instance_type` must stay `mac_mini_m2`.** `linux_x2` is not on this billing
  plan, and the failure reads `The selected instance type is not
  available with the current billing plan`. Gradle, node 22 and
  java 21 all run on the macOS image the iOS lane already uses.
  **Verifying the Play credential when you cannot read it back:** a Codemagic
  Secret is write-only, so the only evidence is *where the build dies*, and each
  fix moves the death later. Bad JSON dies at `Provided Google Play service
  account JSON has invalid format` before any machine work. A good key reaches
  Play and prints the app back at you: `App name`, `Package name: com.phzse.app`,
  `Version`, and the `Phzse Admin` signing certificate. A duplicate-versionCode
  error is therefore a PASS on credentials, not a failure of them.
  The two secrets behind this are installed and were both Keith's to add: keystore
  `phzse_upload_keystore` (Phzse Admin, expires November 09, 2080) under Code
  signing identities > Android keystores, and `GCLOUD_SERVICE_ACCOUNT_CREDENTIALS`
  (group `google_play`, Secret) on the Environment variables tab, beside
  `CERTIFICATE_PRIVATE_KEY` in `signing`. Codemagic has made personal-account
  GLOBAL variables read-only and is removing them, so app-level is the only place
  these go. If either ever needs reinstalling, do not hand-type it: run
  `python ~/brain-gym/scripts/codemagic-install-play-key.py --prompt --app phzse
  --key-file ~/Downloads/phzse-488419-94ef93c9d510.json`, which posts the key from
  the file through the Codemagic v3 API so nobody copies the bytes.
  Everything under those two entries is already built: service account
  `play-publisher@phzse-488419.iam.gserviceaccount.com` in GCP project
  `phzse-488419` (unique id `110060498211983366484`),
  `androidpublisher.googleapis.com` enabled on it, and Active Play Console access
  to `com.phzse.app` with the two Releases permissions. **Play publishing rights
  live in Play Console, not Cloud IAM**: the service account needs no GCP IAM role,
  the grant is an invite under Users and permissions. The `/api-access` path is
  retired and redirects to the developer account home.
  `publishing.google_play` has no key for release notes, so the draft ALWAYS
  arrives without them. Step 11 finishes the job; do not leave it for Keith and do
  not type them in the console.
  **If Codemagic itself is down, wait and start again later.** Never upload through
  the Play Console in a browser. The 2026-09-02 manual upload needed a Win32-driven
  Chrome window and, failing that, Keith's hands. If an upload from this box is ever
  needed, Brain Gym's `scripts/play-release.py` (`publish --aab`) shows the Play API
  route; its package name is fixed to Brain Gym's.
  Play's "native code without debug symbols" warning is EXPECTED and unfixable.
  Do not chase it. `ndk { debugSymbolLevel 'FULL' }` was tested on 2026-09-04
  with `--rerun-tasks` and produced zero symbol entries, because the only native
  libs are prebuilt AndroidX `.so` files that Google already stripped (no
  `.symtab`, no `.debug_*`). We compile no native code, so there is nothing to
  package.

### 11. Publish the Play draft

`android-release` leaves a DRAFT with no release notes. Finish it once the build is
green, from the repo root:

```bash
npm run play:publish -- --key "$HOME/Downloads/phzse-488419-94ef93c9d510.json"
```

That is a DRY RUN: it stages the change, validates the edit, then discards it. Read
the output, then add `--commit` to publish. `scripts/play-publish.mjs` reads the
package, `versionCode`, `versionName` and the notes file straight out of the
checkout, refuses if the Play draft carries any other `versionCode`, and reads the
track back after committing to prove the notes landed. Nothing takes effect before
the commit, so a run that stops early changes nothing.

**Do not run it, dry run included, until Codemagic shows `Publishing` green.** Every
run opens a Play edit and Play keeps ONE edit per app, so a dry run during the CI
upload kills the upload with `This edit has expired, please create a new Edit`
(build 6aa502b7a0b59d4e46424352, 2026-09-12, caused by a 75-second polling loop).
A failed upload does not consume the `versionCode`: re-run the workflow as is.
Watch the build page, never poll Play, to learn when the draft has landed.

`tracks.update` REPLACES the releases array. Sending the new release alone as
`status: completed` supersedes the live one, exactly like the console's rollout
button; it cannot un-publish anything by omission.

Do NOT move this into `codemagic.yaml`. The draft is the only human gate between a
green build and every user of a health app, and this one deliberately keeps it.

### 12. Report

Tell the user:
- Build number bumped: {OLD} to {NEW}
- Codemagic build id for `android-release`, and which step it reached
- The Play track read back after publishing: name, versionCode, status
- Committed and pushed to remote

## Starting a Codemagic build with the API (optional)

The release tag is the default starter for both apps. This script is the other route,
for when `CODEMAGIC_AUTH_TOKEN` is set. `scripts/codemagic-run.mjs` in this skill starts a workflow through Codemagic's REST API
(`POST /builds`), polls it (`GET /builds/<id>`), saves the log of a failed step, reruns
known one-off failures (twice at most) and prints the report step. **No browser and no
Allow click.** It needs only Node and the API token below. Run it detached, then wait on
its log:

    node ~/.claude/skills/build-release/scripts/codemagic-run.mjs --detach \
      --app <app id> --workflow <workflow key> --branch <branch> --report-step "<submit step>"
    # prints LOG <path>. Then wait in the foreground; exit 2 means still running, so repeat:
    node ~/.claude/skills/build-release/scripts/codemagic-run.mjs --wait <path>

- `--workflow` is the key under `workflows:` in `codemagic.yaml` (`ios-release`,
  `android-release`), not the display name. Phzse builds `master`, Brain Gym `main`.
- `--detach` matters: Claude Code kills background shells when memory runs low while the
  session is idle (twice on 2026-10-15). The detached script has no parent shell to be
  killed with, and `--wait` reads only the log file. Give the wait call a 600000 ms tool
  timeout; it returns by itself after 570 s.
- `RESULT success <id>` ends a good run, after the `--report-step` lines (for iOS: build
  number, review submission id, `WAITING_FOR_REVIEW`). `RESULT failed ... log <path>`
  names the failed step and its saved log: read it, fix the cause, then run again.
- The one-off failures it reruns, both seen on Brain Gym 2026-10-15 and both gone on
  rerun: a Turbopack `next/font/google queries have exactly one entry` error in the web
  build (gone at root since Brain Gym 75af437 committed the font files), and Apple 500s on `CHANGE UPLOAD STATE TO
  COMPLETE`, where altool prints `UPLOAD SUCCEEDED` but cli-tools still exits 1. A rerun
  takes a new build number; the half-uploaded build sits unused in TestFlight, harmless.
- `--dry-run` proves the token can read the app. `--check <id,id>` reads past builds and
  saves each one's JSON in the temp dir. Neither starts anything. `node --test
  scripts/codemagic-run.test.mjs` runs the script against a stand-in API.
- **Not yet run with a real token** (2026-10-15). The calls follow Codemagic's docs and a
  public script that reads the same JSON (`build.status`, `buildActions[].subactions[]`,
  `logUrl`). Once the token exists, run `--check
  6ad06f91546ce6236ceec0f4,6ad070ea546ce6236ceec144,6ad07473546ce6236ceec1e9 --app
  6a9af25b162dbd9385d77f04`: the first two must read as transient failures, the third as
  success. Delete this bullet once they do.
- Why not Chrome: on 2026-10-15 the Claude in Chrome extension was off, and Chrome's
  debugging port asks Keith to click Allow for every new connection. Two releases stalled
  on his hands that day. Never route a release through a browser again.
- App ids: Phzse `69ab40d4cb7ed3e0ae357c3e`, Brain Gym `6a9af25b162dbd9385d77f04`.

### One-time setup: the API token

The script reads `CODEMAGIC_AUTH_TOKEN` from the environment, or from the Windows User
scope when the session started before it was set. Only Keith can copy the token
(Codemagic > Account settings > API token > Show; the page keeps it masked from agents).
He runs this once in his own PowerShell window, never through the chat, so the token
stays out of transcripts:

    $t = Read-Host 'Codemagic API token' -AsSecureString; [Environment]::SetEnvironmentVariable('CODEMAGIC_AUTH_TOKEN', [Net.NetworkCredential]::new('', $t).Password, 'User')

Then `--dry-run --app 6a9af25b162dbd9385d77f04` must print `RESULT dry-run ok`. Without
the token the script stops at once with `RESULT error no CODEMAGIC_AUTH_TOKEN`; the tag
route still works. The token is optional: it adds logs and automatic reruns. Never ask
Keith for a browser click.

## Brain Gym

Repo `~/brain-gym`; work in a worktree, because the main checkout often holds another
session's branch. Branch `main`. Store records live in `docs/STORE-SUBMISSION.md`.

1. **Version.** `package.json` `version` is the only version, and both Codemagic lanes
   read it. `android/app/build.gradle` stays at the inert `versionCode 2` / `"1.2.0"` in
   git. Rewrite `store/appstore/release-notes/en-US.txt` for this release (Apple refuses a
   submission without it) and show Keith the text: it is public copy.
2. **Checks, as CI runs them.** `npm run test:all` is not the whole CI. Also run
   `python3 scripts/test_asc_store_urls.py`, `scripts/test_asc_listing.py`,
   `scripts/test_play_release.py`, `bash scripts/test_ios_open_version.sh`, and `npm run
   build`, which fails any route over 240 KB gzipped. Open the PR and wait for CI. The
   browser job takes about 45 minutes. Builds no longer fetch Google Fonts (75af437), so
   a font failure there is a real bug, not a flake to rerun.
3. **Merge** with `gh pr merge --squash --match-head-commit <sha>`, then **deploy the
   site** from the merged tree: `npm run build:web` (not `npm run build`, which skips the
   paint script), then `npx wrangler pages deploy out --project-name=brain-gym
   --branch=main`. Check that every sitemap URL answers 200 with the new build id.
4. **Android, from this box.** Brain Gym's Codemagic `android-release` has never run, so
   Play gets the bundle from here:
   - `python scripts/play-release.py read --key ~/Downloads/phzse-488419-94ef93c9d510.json`
     prints the next free versionCode.
   - If the worktree lacks them, copy `signing.keystore`, `keystore.properties` and
     `local.properties` from `~/brain-gym/android/` (all gitignored). Delete the copies
     afterwards.
   - Set `versionCode <next free>` and `versionName "<package.json version>"` in
     `android/app/build.gradle` locally, then run `npm run build`, `npx cap sync android`
     and `android/gradlew -p android bundleRelease`.
   - `python scripts/play-release.py publish --aab
     android/app/build/outputs/bundle/release/app-release.aab --key <key> --track
     production --name <version>` is the dry run. Add `--commit`, then `read` the track.
   - `git restore android/app/build.gradle`.
5. **iOS**: push `release-<version>` on the merge commit (`git -C <worktree> tag
   release-1.2.8 <sha>`, then `git -C <worktree> push origin release-1.2.8`), and watch
   `gh api repos/kitfunso/brain-gym/commits/<sha>/check-runs`. The trigger is on main
   since brain-gym PR #30 (1a63c58); the repo's webhook 698563981 to Codemagic exists since 2026-10-15.
   With `CODEMAGIC_AUTH_TOKEN` set, the script may start it instead (`--app
   6a9af25b162dbd9385d77f04 --workflow ios-release --branch main --report-step "Submit
   for review"`), never both. It takes about 7 minutes once a machine is
   free; the queue added 4 on 2026-10-15. The lane uploads the IPA, opens the version
   record, and writes the listing from `scripts/asc-listing.py`: subtitle, keywords,
   description, promotional text and both captioned screenshot sets. It then submits for
   review as `AFTER_APPROVAL`, so Apple releases it on approval.
6. **Report**: merge commit, site deploy id, the Play track read back, the Codemagic
   build id, and the review submission id and state.
