# Store prerequisites

Three sections: what a human sets up (stage 1), what the listing needs (stage 5), and the review rules that reject a first submission. Every quoted rule was read from the cited page on 2026-09-05; re-read the page when a rule decides something.

## 1. Accounts and records (stage 1, start on day one)

Keith does every row with a credential, a bank detail or a signature. The agent prepares the text and the click-steps (`/click-steps`) and never enters a password or a card.

| Item | Where | Why it is day one |
|---|---|---|
| Apple Developer Program membership | developer.apple.com | Bundle id registration and App Store Connect need it |
| Google Play developer account | play.google.com/console | Identity verification takes days |
| Play closed test: 12 opted-in testers for 14 continuous days | Play Console, Testing | Required for personal accounts created after 13 November 2023 before production access; production access then takes up to 7 days to review (support.google.com/googleplay/android-developer/answer/14151465) |
| Paid Apps Agreement, bank and tax | App Store Connect, Business | In-app purchases cannot be created until it is active (brain-gym, 4 September 2026) |
| Play payments profile | Play Console, Setup | Same, for paid or IAP apps |
| Bundle id and package name | developer.apple.com, `capacitor.config.json` | Fixed once shipped; pick the reverse-domain name now |
| App Store Connect record | appstoreconnect.apple.com | The app id number goes in `docs/LAUNCH.md` |
| Play app record | Play Console | Same |
| Codemagic app connected, iOS signing profile and certificate | codemagic.io, Codemagic Signing | The build cannot upload without it; brain-gym and eaves both use this route |
| Android upload keystore | Codemagic Signing | Lost keystore means a new package name; back it up |
| RevenueCat project, if monetised | app.revenuecat.com | Products must exist in both stores before the app can be reviewed with them |
| Support site with privacy page | Cloudflare Pages or equivalent | The privacy URL is a required field, and the policy must also be linked inside the app |

Test devices: at least one physical iPhone and one physical Android phone on the tester lists.

## 2. The listing (stage 5)

Write `store-assets/APP-STORE.md` and `store-assets/PLAY.md` with everything to paste: name, subtitle, category, age rating answers, keywords, description, what's new, support URL, marketing URL, privacy URL, review notes, demo account instructions, and the privacy answers. Eaves' `store-assets/APP-STORE.md` is the shape.

- Privacy labels (App Store) and Data safety (Play) are copied from `docs/ARCHITECTURE.md` section 7, one row per data kind, one third party per row. Two documents that disagree is a rejection.
- Release notes go in the file and in the CI config's release-notes input. Apple refuses a submission with an empty `whatsNew`, and neither Codemagic publishing block has a key for it (build-release lesson, Phzse build 172).
- Age rating: answer the questionnaire from the PRD, and expect Play's IARC to change the rating in some countries on re-take.
- Screenshots: from the script in `mobile-design.md` section 6, at every size the store marks required. Apple's required iPhone set is the 6.9 inch size; iPad shots are needed only when the target family includes iPad.
- Export compliance: `ITSAppUsesNonExemptEncryption` set to false in `Info.plist` when the app only uses HTTPS. Without it every TestFlight build sits at "Missing Compliance" (eaves build 1).
- Privacy manifest: `PrivacyInfo.xcprivacy` present and registered in the Xcode target.
- TestFlight external testing and Codemagic's beta-review submission need the test information page filled (feedback email, reviewer name, phone, email). Internal groups need none of it.

## 3. Review rules that reject first submissions

From developer.apple.com/app-store/review/guidelines:

- **2.1 Completeness.** Final build, all URLs working, "include demo account info (and turn on your back-end service!) if your app includes a login". The demo account is created before submission, its key goes in the review credentials field, and the backend's API keys are set so a reviewer's first action succeeds.
- **5.1.1(i) Privacy policy.** Linked in the App Store Connect field "and within the app in an easily accessible manner"; it names what is collected, every third party, retention, and how a user requests deletion.
- **1.5 Developer information.** The app and the support URL "include an easy way to contact you".
- **2.3.3 Screenshots.** "Show the app in use, and not merely the title art, login page, or splash screen."
- **5.1.1(v) Account deletion.** "If your app supports account creation, you must also offer account deletion within the app." A settings row, wired to the deletion path in `docs/ARCHITECTURE.md` section 7, before the first submission.
- **3.1.1 In-app purchase.** Unlocking features "must use in-app purchase". Any paid tier goes through the store's IAP (RevenueCat here), never a web checkout link inside the app, and the products exist in both consoles before the review build.
- **2.5.4 Background modes.** Background services "only for their intended purposes"; the review notes say which purpose and what the user sees while it runs.
- **4.2 Minimum functionality.** The app must do more than "a repackaged website". A Capacitor shell earns its place with a native capability (background audio, push, deep links, offline) that the PWA cannot do; say which in the review notes.

Play equivalents live at play.google.com/console under Policy status; the Data safety form and the target API level are the two that stop a rollout. R8 minification on (`minifyEnabled true`) removes Play's obfuscation warning (phzse, September 2026).

Background modes and sensitive permissions (microphone, location, health) get a paragraph in the review notes saying why the app needs them and what the user sees.
