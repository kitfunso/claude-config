# Mobile Overlay

For Capacitor / React Native / Expo apps targeting iOS + Android.

## Detection signals
- Files: `capacitor.config.{json,ts,js}`
- Dirs: `android/` AND `ios/`
- Deps: `@capacitor/core`, `react-native`, `expo`
- Build configs: gradle, xcodeproj, Podfile

## Required additions per phase

### SCAFFOLD
- Store listing draft (App Store + Play Store text + screenshots)
- Privacy nutrition labels mapped (iOS App Privacy)
- Platform-specific configs documented
- Permission justifications drafted (every iOS/Android permission has a user-facing reason)

### PLAN
- Native module needs identified (camera, location, biometric, etc.)
- Deep linking strategy
- Push notifications strategy
- Offline behavior planned
- Capacitor packages aligned across platforms (per past memory)

### EXECUTE
- Platform parity — don't ship iOS-only features unintentionally
- Test on real device, not just simulator
- Capacitor plugin versions aligned (run `npx cap doctor`)
- Asset paths absolute, not relative
- No web-only APIs (window, document) without Capacitor wrapping

### VERIFY
- iOS build succeeds (`xcodebuild` or via Codemagic)
- Android build succeeds (`./gradlew assembleRelease`)
- Test on PHYSICAL device, not just simulator (simulators miss real-device bugs)
- Test cold start launch time
- Test backgrounding + resume
- Test push notification receipt if applicable

### REVIEW
- App permissions justified (every iOS/Android permission has a reason)
- App size budget (under 50MB ideal, definitely under 100MB)
- Native module updates noted in PR
- Memory leak check on long sessions

### SHIP
- **`/build-release` REQUIRED** — bumps iOS/Android build numbers, builds .aab, commits, pushes
- Codemagic / Fastlane / EAS pipeline runs clean
- Build number monotonically increasing (store rejects duplicates)
- Per past memory: use Codemagic Signing for iOS

### DEPLOY
- Internal testing track first (TestFlight / Internal Testing)
- Watch crash reports first 24h
- Phased rollout if available (Android phased, iOS phased)

### LEARN
- Crash retro if any in first week
- Store review monitoring (1-star reviews are signals)
- Update DESIGN.md with platform-specific patterns learned

## Tools

- `/build-release` skill — bump numbers, build .aab, commit, push
- `/setup-deploy` skill — CI/CD configuration

## Anti-patterns

- Skipping device testing (simulator missed bugs)
- Permission strings missing or generic ("This app needs camera access")
- Build number not bumped (store rejects)
- Native module version drift across platforms
- iOS-only patterns shipped to Android (or vice versa)
- Web-only APIs without Capacitor wrappers
- Splash screen too long (users bail)
- App size bloat from un-tree-shaken deps
- Missing offline state (app appears frozen on no-network)
- Push tokens not refreshed on app update
