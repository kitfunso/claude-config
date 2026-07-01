---
name: build-release
description: "Bump iOS/Android build numbers, build the Android .aab bundle, commit and push. Use this skill whenever the user says 'build release', 'bump build', 'build aab', 'bump and push', 'bump ios build number', 'build the aab file', or any combination of bumping build numbers, building Android bundles, and pushing. Also trigger when user says 'release build' or 'ship the build'."
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

### 2. Read current build numbers

Read these two files to find the current build number:

- **iOS**: `codemagic.yaml` — find the line `agvtool new-version -all N` and extract N
- **Android**: `android/app/build.gradle` — find the line `versionCode N` and extract N
- Also extract `versionName` from build.gradle (e.g., "2.1.0") for the .aab filename

Both should be the same number. The new build number = current + 1.

### 3. Bump build numbers

Edit both files, replacing the old number with the new one:

- `codemagic.yaml`: `agvtool new-version -all {NEW}`
- `android/app/build.gradle`: `versionCode {NEW}`

### 4. Verify lockfile is in sync (CRITICAL — prevents Codemagic CI failure)

**If any dependency changed this session** (`npm install`, `npm audit fix`, version bumps — even indirect ones), run a REAL clean install. `npm ci --dry-run` PASSES FALSELY on lockfiles that real `npm ci` rejects (proven 2026-06-10: dry-run green locally, Codemagic failed with 27 "Missing: <pkg> from lock file" errors):

```bash
cd "C:/Users/skf_s/phzse" && npm ci
```

This wipes node_modules and installs strictly from the lockfile — exactly what Codemagic runs. Takes a few minutes; that is the price of a trustworthy gate. If no dependency changed this session, `npm ci --dry-run` is an acceptable fast path.

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

Why this matters: `npm install` (local) tolerates lockfile drift. `npm ci` (Codemagic) does not. Adding or updating any dependency in a prior step in this session — even indirectly — can orphan peer-dep entries. Always verify, and never trust --dry-run after dependency changes.

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

The .aab is gitignored, so it won't be committed — it's just for local reference / Play Store upload.

### 9. Stage, commit, and push

Stage all modified files (not untracked directories like `.gstack/` or `prototypes/`):

```bash
git add codemagic.yaml android/app/build.gradle
```

Also stage any OTHER unstaged modified files from the current session (check `git status` first). Do NOT stage untracked directories unless they're clearly part of the work.

Commit with:

```
chore: bump build {NEW_BUILD} and release .aab

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

Then push:

```bash
git push
```

### 10. Report

Tell the user:
- Build number bumped: {OLD} → {NEW}
- .aab file: `app-release-v{VERSION}-build{NEW}.aab`
- Committed and pushed to remote
