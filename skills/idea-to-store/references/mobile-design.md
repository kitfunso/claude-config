# Mobile design rules

`/frontend-mix` carries the taste lock, the review gate and the slop blacklist in `~/.claude/skills/frontend-mix/references/design-standards.md` and `anti-slop.md`. Apply all of that, then these, which the web pipeline does not carry. Sources are cited so the numbers can be re-checked; every number below was read from the cited page on 2026-09-05.

## 1. Targets, text, contrast

| Rule | Value | Source |
|---|---|---|
| Tap target, iOS | at least 44 x 44 pt | developer.apple.com/design/tips ("Create controls that measure at least 44 points x 44 points") |
| Tap target, Android | at least 48 x 48 dp | developer.android.com/guide/topics/ui/accessibility/apps |
| Tap target, web view | at least 24 x 24 CSS px (WCAG 2.5.8 AA), 44 x 44 for AAA (2.5.5) | w3.org/WAI/WCAG22/Understanding/target-size-minimum.html |
| Smallest text, iOS | 11 pt | developer.apple.com/design/tips |
| Contrast, small text | 4.5:1; 3:1 for text 18sp+ or bold 14sp+ | developer.android.com/guide/topics/ui/accessibility/apps |

Use the larger of the two platform numbers in a Capacitor app, since one web view serves both.

## 2. No dead space

Dead space is a region of the screen that carries nothing the user can read or do. Every screen is composed to the phone's viewport, then checked at the smallest supported phone and the largest.

- Every screen has a job in one line, and its first viewport shows the job's primary action without scrolling.
- Lists fill from the top; an empty list is an **empty state** with one sentence and one action, never a blank area.
- Bottom of the screen: a primary action bar, a composer, or the last list item. Blank space above the home indicator means the layout was drawn for a taller phone.
- A detail screen with little content pulls the next action up under it; it does not float three lines at the top of an empty page.
- Cards earn their existence (the frontend-mix rule); on a phone that usually means a list with dividers instead.
- Safe areas: content respects the notch and home indicator, and backgrounds extend under them.

## 3. Every screen has five states

Mock and build all five before calling a screen done: loaded, empty, loading, error, offline. The loading state is a skeleton of the loaded layout, so the screen does not jump. The error state says what happened in plain words and offers the retry. The offline state says the app is waiting for a network and what is queued.

## 4. Platform behaviours

- Dynamic type: text scales with the OS setting and the layout survives the largest size.
- Reduced motion: every animation honours `prefers-reduced-motion`; the page reads at rest.
- Labels: every control has an accessible name that says its purpose; decorative graphics are hidden from the screen reader.
- Keyboard: inputs scroll into view above the keyboard, and the keyboard never covers the submit button. Phzse shipped a fix for exactly this in September 2026.
- Back: Android hardware back does what the on-screen back does.
- Permission prompts fire on first use of the feature, with the OS string explaining the reason in one sentence.

## 5. The mark and the icon

The logo and the app icon are a real three.js render, per Keith's standing rule (memory `feedback_real_3d_render_for_creative_design`, which holds the recipe: MeshPhysicalMaterial, baked environment map, Playwright capture). The render is the single source; one script in the repo writes every icon and splash size from it, the way phzse's `scripts/convert-icons.mjs` does.

- iOS 1024 icon: PNG with no alpha channel. Apple rejects alpha.
- Play keeps two icons: the one in the bundle, and the store-listing icon uploaded by hand in Play Console. A release never updates the second one, so the producer script writes it to a named path and the launch checklist uploads it.
- Splash: one image, centred, from the same producer, shown for as short a time as the platform allows.

## 6. Screenshots are the app

Store screenshots come from a script that drives the real app with fixture data at the store's required size, the way eaves' `scripts/store-shots.cjs` does at 1290 x 2796. Apple's guideline 2.3.3 wants the app in use, never the splash or the login page. JPEG, because a browser PNG carries the alpha channel Apple rejects.
