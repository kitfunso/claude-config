---
name: build-release
description: Bumps iOS/Android build numbers, compile-checks the Android build, commits, pushes, then starts both Codemagic workflows for the Phzse app. Use when asked to ship a new Phzse build.
---

# Build Release

Ships a Phzse release: bump build numbers, build web assets, compile-check Android, commit, push, then start both Codemagic workflows. **CI builds and uploads the shipping artifacts.** The local gradle run is a pre-flight only, and the iOS IPA is never built here at all.

## Prerequisites

- Must be in the `$HOME/phzse` project directory
- Git must be on the correct branch (verify first, never assume)

## Steps

Execute these steps in order. Stop and report if any step fails.

### 1. Verify branch

```bash
cd "$HOME/phzse" && git branch
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
cd "$HOME/phzse" && npm ci
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
cd "$HOME/phzse" && npm run build
```

Wait for completion. This must succeed before proceeding.

### 6. Sync Capacitor

```bash
cd "$HOME/phzse" && npx cap sync android
```

### 7. Compile-check the Android build

```bash
cd "$HOME/phzse/android" && ./gradlew bundleRelease
```

30-60 seconds, must finish with `BUILD SUCCESSFUL`. This is a pre-flight, nothing
more. CI runs the same gradle task and fails the same way four minutes later, so
catch it here.

**The bundle that ships is built by CI, not by this command.** `android-release`
on Codemagic builds and signs its own, with the `phzse_upload_keystore` Codemagic
holds, and uploads it straight to Play. Do not copy the local `.aab` anywhere and
do not upload it by hand while CI works: two sources for one artifact is how a
`versionCode` drifts between the repo and the store. The old step that copied it
to `app-release-v{VERSION}-build{BUILD}.aab` existed only to feed a manual upload
and is gone.

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
file from an earlier session. That shipped a wrong message on 6e4a3f6 (2026-09-04).

Then push:

```bash
git push
```

### 10. Upload to the stores

- **iOS**: start the `ios-release` workflow in Codemagic. There is no
  `triggering:` block, so the push does NOT start a build. Press Start new build
  on the app SETTINGS page,
  https://codemagic.io/app/69ab40d4cb7ed3e0ae357c3e/settings. That page renders
  the dialog; the Applications list and the Builds row menu both offer the same
  button and silently do nothing, and `/app/<id>` renders blank and can freeze
  the renderer (seen 2026-09-04). The settings page also prints the
  codemagic.yaml Codemagic actually read, so it doubles as the check that your
  push landed. Since 46c90a9 the workflow submits
  for App Store review on its own and Apple releases on approval, so no manual
  App Store Connect step is left. It does not ask for TestFlight beta review:
  that submission runs first and 422s while the version train already holds a
  build in review, which cost build #171 its store submission. Removed in
  a2905ab. Do not add `submit_to_testflight` back. The submission runs from a
  script step, not a `publishing:` block, because only the script can pass the
  release notes (`--whats-new "@file:..."`), and Apple rejects a submission
  without them (8b7ff74). There is no Codemagic API token on this box, but the
  Chrome profile IS signed in to Codemagic, so press the button yourself. A tab
  resting on a `/login` URL proves nothing: navigate to the settings page and
  look before you call it logged out. That mistake handed a finished release
  back to Keith on 2026-09-04.
- **Android**: start the `android-release` workflow the same way, from the same
  settings page. It builds the bundle, signs it, and uploads it to the Play
  production track as a draft (`submit_as_draft: true`), so nothing reaches users
  until Keith presses the button. Nothing else is needed from you or from him.
  **This lane is proven end to end** by build `6aa0592a1dafc6b3c2e63184`
  (2026-09-08), which ran every step, `Build AAB` in 4m 0s, and got a real answer
  out of the Play API. Its steps summed to 6m 34s, so expect 6 to 7 minutes from
  Start new build, most of it gradle.
  **The one failure to expect is your own fault, and it is loud:**
  `Version code 118 has already been used`. Play refuses a `versionCode` it has
  seen, so step 3's bump is not optional and re-running the workflow on an
  already-published build number can never succeed. Read the number in
  `android/app/build.gradle` before pressing the button.
  **`instance_type` must stay `mac_mini_m2`.** The Android workflow shipped with
  `linux_x2` and so never started a machine once in its life: that instance is not
  on this billing plan, and the failure reads `The selected instance type is not
  available with the current billing plan`. Fixed in `e7e94ca`. Gradle, node 22 and
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
  **Manual upload is the fallback only, for when CI itself is down.** It needs a
  local `.aab` from step 7 and a separate PLAIN Chrome window driven by Win32
  automation (done for build 114 on 2026-09-02). Do NOT use the Chrome MCP
  extension for the drop: it intercepts the native file chooser. Do NOT use
  `mcp__claude-in-chrome__file_upload` either: it caps at 10 MB and the classifier
  denies app binaries through it. The library dialog re-orders rows between
  screenshot and click, so re-screenshot and confirm the ticked row before Add to
  release. Only if the Win32 route is also blocked, pre-fill the release name and
  notes and hand Keith the .aab path to drag. Two console traps: a release with
  zero bundles shows "You cannot remove all production APKs and Android App
  Bundles", and the fix is uploading the new bundle, never clicking Include on the
  old row, which re-ships the live version. After Save, the submit button is on
  Publishing overview, not the release page.
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
button; it cannot un-publish anything by omission. An earlier note claimed the
opposite and cost Keith a hand step he never needed (2026-09-08).

Do NOT move this into `codemagic.yaml`. The draft is the only human gate between a
green build and every user of a health app, and this one deliberately keeps it.

### 12. Report

Tell the user:
- Build number bumped: {OLD} to {NEW}
- Codemagic build id for `android-release`, and which step it reached
- The Play track read back after publishing: name, versionCode, status
- Committed and pushed to remote
