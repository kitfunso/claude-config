---
name: build-release
description: Bumps iOS/Android build numbers, builds the Android .aab, commits, and pushes. Use for 'build release', 'bump build', 'ship the build'.
---

# Build Release

Automates the full release build workflow for the Phzse app: bump build numbers, build web assets, build the Android .aab, commit everything, and push.

## Prerequisites

- Must be in the `C:/Users/skf_s/phzse` project directory
- Git must be on the correct branch (verify first, never assume)

## Steps

Execute these steps in order. Stop and report if any step fails.

### 1. Verify branch

```bash
cd "C:/Users/skf_s/phzse" && git branch
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

### 4. Verify lockfile is in sync (CRITICAL â€” prevents Codemagic CI failure)

**If any dependency changed this session** (`npm install`, `npm audit fix`, version bumps â€” even indirect ones), run a REAL clean install. `npm ci --dry-run` PASSES FALSELY on lockfiles that real `npm ci` rejects (proven 2026-06-10: dry-run green locally, Codemagic failed with 27 "Missing: <pkg> from lock file" errors):

```bash
cd "C:/Users/skf_s/phzse" && npm ci
```

This wipes node_modules and installs strictly from the lockfile â€” exactly what Codemagic runs. Takes a few minutes; that is the price of a trustworthy gate. If no dependency changed this session, `npm ci --dry-run` is an acceptable fast path.

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

Why this matters: `npm install` (local) tolerates lockfile drift. `npm ci` (Codemagic) does not. Adding or updating any dependency in a prior step in this session â€” even indirectly â€” can orphan peer-dep entries. Always verify, and never trust --dry-run after dependency changes.

### 5. Build web assets

```bash
cd "C:/Users/skf_s/phzse" && npm run build
```

Wait for completion. This must succeed before proceeding.

### 6. Sync Capacitor

```bash
cd "C:/Users/skf_s/phzse" && npx cap sync android
```

### 7. Build Android bundle

```bash
cd "C:/Users/skf_s/phzse/android" && ./gradlew bundleRelease
```

This takes 30-60 seconds. Must finish with `BUILD SUCCESSFUL`.

### 8. Copy .aab to project root

```bash
cp "C:/Users/skf_s/phzse/android/app/build/outputs/bundle/release/app-release.aab" \
   "C:/Users/skf_s/phzse/app-release-v{VERSION_NAME}-build{NEW_BUILD}.aab"
```

The .aab is gitignored, so it won't be committed â€” it's just for local reference / Play Store upload.

### 9. Write the App Store release notes

Rewrite `store-assets/release-notes/en-GB.txt` to describe THIS release, in plain
words a user reads on the store page. Apple refuses a review submission when the
default locale has no `whatsNew`, and Codemagic's `publishing:` block has no key
for it, so the CI publish step reads this file. Build #172 died on a stale-empty
one. Show Keith the text before committing: it is public copy.

### 10. Stage, commit, and push

Stage all modified files (not untracked directories like `.gstack/` or `prototypes/`):

```bash
git add android/app/build.gradle ios/App/App.xcodeproj/project.pbxproj
```

Also stage any OTHER unstaged modified files from the current session (check `git status` first). Do NOT stage untracked directories unless they're clearly part of the work.

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

### 11. Upload to the stores

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
  without them (8b7ff74). There is no Codemagic API token on this box,
  so the Start new build press is Keith's.
- **Android**: start the `android-release` workflow the same way, from the same
  settings page. It builds the bundle and uploads it to the Play production
  track as a draft (`submit_as_draft: true`), so nothing reaches users until
  Keith presses the button. It needs two secrets in Codemagic that only he can
  install: an Android keystore named `phzse_upload_keystore`, and an environment
  group `google_play` holding `GCLOUD_SERVICE_ACCOUNT_CREDENTIALS`. Check both
  exist before starting the build; without them it dies at signing.
  `publishing.google_play` has no key for release notes, so Keith types those in
  the console when he reviews the draft.
  If the secrets are still missing, fall back: drive the browser to the Prepare
  release page, pre-fill the release name and notes, and hand over the .aab path
  for Keith to drag. Do not try to upload it. The classifier denies app-binary
  uploads and `file_upload` caps at 10 MB against an ~11 MB bundle.

### 12. Report

Tell the user:
- Build number bumped: {OLD} â†’ {NEW}
- .aab file: `app-release-v{VERSION}-build{NEW}.aab`
- Committed and pushed to remote
