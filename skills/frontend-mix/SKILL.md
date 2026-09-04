---
name: frontend-mix
description: "Build frontend that looks like nothing the world has seen, from the tech people are actually going viral with on X in 2026: Three.js/WebGPU heroes, Gaussian splats (Spark), Paper Shaders, Canvas-UI-style GPU effects over live DOM, liquid glass, gooey/metal materials, GSAP+Lenis, native scroll-driven CSS, kinetic type, bento vs anti-grid layouts, plus the Claude design-skill stack (frontend-design, taste dials, anti-slop). It ROLLS a seeded random tech mix per variant so techs collide in new ways, builds 5 single-file HTML mockups (web/app) or one HTML-preview MVP video composition (launch/demo video via HyperFrames), then stops for human review. Taste is locked BEFORE the dice roll through the house pipeline folded in here: DESIGN.md via /design-consultation, one committed direction via /frontend-design, a /design-review gate before anything is shown, in /frontend-build order. Dice choose technology, never taste. Use whenever the user asks for a landing page, hero, app UI, mockup, 'make it look amazing', 'viral', 'wow', 'not generic', a launch video, demo video, promo, or says 'surprise me' about visuals - even if they don't name a library."
---

# frontend-mix

You are a design engineer with the 2026 X-viral toolkit in your hands and a dice cup. The job is not to pick the safe stack. The job is to make five things the user has not seen before, show them side by side, and let a human choose. Randomness is the point: two techniques that nobody has stacked yet is where "the world has never seen this" comes from. The roller keeps the chaos honest (seeded, logged, never repeated, never a known clash, never a performance pile-up).

The chaos has a boundary: **dice choose technology, never taste.** The first live round let the roller pick palette and type with no DESIGN.md, and the result was five costumes on the same page. So the skill now carries the house design pipeline inside it, in `/frontend-build` order: lock taste (`/design-consultation` writes `DESIGN.md`), commit to one direction per variant (`/frontend-design`), build, then a `/design-review` gate before the human sees anything. `references/design-standards.md` is the working copy of those four skills; read it once per session.

Two modes. Both end at a human gate.

| Mode | Trigger | Output | Gate |
|---|---|---|---|
| `web` | page, app, hero, dashboard, mockup, "make it look amazing" | 5 single-file HTML variants + contact sheet + review board | user picks / remixes |
| `video` | launch video, demo, promo, teaser, reveal | one HyperFrames composition (2-3 scenes) previewed in the browser, NOT rendered | user approves before render |

Precedence for every visual choice: the user's own words, then `DESIGN.md`, then the rolled recipe. A roll never overrides a stated brand. `DESIGN.md` always exists by the time you roll: either it was there, or Step 1 wrote it with the user's approval. `palette` and `type` are locked from it with `--design`; the dice get hero, material, motion, and layout.

Free and open-source tech only. No ThreeUI Pro, Skiper premium, libraries.dev Pro, 21st.dev API keys, Spline. The catalog is already filtered; do not add a paid item.

## Step 0: read the brief (30 seconds, no questions yet)

Pin three things before rolling: the subject (one product, one audience), the page's single job (convert, explain, impress, operate), and the mode. Pull real content from the repo, README, or the user's words. Never lorem, never "Acme". If the subject is unknown, ask one question and stop. Everything else you decide.

Check `package.json` and `DESIGN.md` if a project exists. Note the port target for later (shadcn on Base UI is the 2026 default; Astryx if they want a Meta-grade agent-readable system).

## Step 1: lock taste (the /design-consultation stage)

Look for `DESIGN.md` at the project root. If it exists, read it and move on. If it does not, do not build anything yet. Run the short-form consultation from `references/design-standards.md` section 1: product context pre-filled from the repo and confirmed in one question, the memorable-thing question, then ONE complete proposal (aesthetic, decoration, layout, colour with hex, typography with roles, spacing, motion, why it coheres, SAFE choices, RISKS). Propose, do not present menus; every line has a "because". Then STOP and wait for the user: ship it, adjust, wilder risks, or start over.

On approval write `DESIGN.md` in the shape given in the standards file (keep the bold labels; the roller parses them) and add the "Design System" pointer to the project `CLAUDE.md`. Record the direction phrase and the memorable thing; every builder brief carries both.

Skip the consultation only when the user says in their own words that they want exploration before a brand exists ("surprise me, no brand yet"). Then roll without `--design`, treat the round as taste discovery, and run the consultation on the winner: its palette and type become the proposal.

## Step 2: roll the recipe

```bash
python ~/.claude/skills/frontend-mix/scripts/roll.py --mode web --n 5 --design DESIGN.md --out <workdir>/mix --brief "<one line>"
python ~/.claude/skills/frontend-mix/scripts/roll.py --mode video --n 1 --design DESIGN.md --out <workdir>/mix --brief "<one line>"
```

`--design DESIGN.md` locks `palette` and `type` from the file (tokens and fonts land in the manifest as `design-md`). Options: `--seed 1234` to reproduce, `--lock hero=splat` to pin a tech slot the user named, `--avoid hero=splat` to exclude. The script writes `manifest.json` (seed, per-variant recipe, CDN imports, warnings) and prints a table. It enforces: all heroes distinct across the round, palettes distinct when they are rolled, no two variants share more than two free slots, no known-clash pairs, at most two GPU-heavy layers per variant, no repeat of a (hero, material, motion) triple from `history.json`, and at least one variant carrying a (hero, material) pair never rolled before. Do not hand-edit a recipe to make it safer; if a roll is genuinely wrong for the brief, re-roll with `--avoid` and say why.

Read `manifest.json`. Then read the catalog entries you rolled in `references/catalog.md` (it has the verified CDN imports, minimal snippets, and the perf caveats per option). Read `references/anti-slop.md` and `references/design-standards.md` once per session.

## Step 3 (web): commit a direction, then build five variants in parallel (the /frontend-design stage)

Before dispatching, write the four `/frontend-design` answers yourself for each variant: purpose, tone in one phrase, constraints, differentiation (the memorable thing restated for this hero). Set the three dials per variant (DESIGN_VARIANCE from `layout`, MOTION_INTENSITY from `motion`, VISUAL_DENSITY from the subject). Five variants share one DESIGN.md and differ in hero, material, motion, layout, and direction phrase. If two briefs read like siblings, rewrite the weaker one.

Fill `assets/builder-brief.md` once per variant (every `{{field}}`, the manifest importmap pasted verbatim, the catalog snippets for that variant's options, the real content) and dispatch five Sonnet sub-agents in ONE message, one per variant, non-overlapping files. Each agent writes exactly one file: `<out>/variants/v<N>-<hero>.html`. Do not build the variants yourself in one pass; the first live round did, and every page came out as the template with an effect bolted on.

What every variant must satisfy:

- Single self-contained HTML. External scripts only from `cdnjs.cloudflare.com` or `cdn.jsdelivr.net/npm/` (pinned versions from the catalog), fonts only from Google Fonts. This is the Artifact CSP allowlist, so a variant can be published straight to a claude.ai artifact for the review. One exception: a splat `.spz` is fetched at runtime, which the Artifact CSP blocks, so a splat variant is reviewed locally or with the file inlined as a `data:` URI.
- The `<script type="importmap">` is the manifest's `importmap` object pasted verbatim, never retyped from memory (first live round: a builder dropped `three/addons/` and Spark failed to resolve `three/addons/postprocessing/Pass.js`, killing the splat hero silently).
- When the hero texture or particle field is sampled from text, position it from the live element's `getBoundingClientRect` / `Range.getClientRects`, never from hard-coded pixel offsets (first live round: a ghost headline drawn at fixed coordinates).
- The rolled recipe is used for real, not name-checked. A `hero: splat` variant loads a real `.spz` through Spark. A `material: liquid-glass` variant has the SVG `feDisplacementMap` refraction, not a `backdrop-filter: blur` alone.
- Visible at rest: the first frame shows the page. Motion adds; it never parks content at `opacity: 0`.
- A tech legend chip in the corner (`.recipe-chip`, already in the template) listing the mix, so the reviewer knows what they are looking at.
- Perf guardrails: `pixelRatio` capped at 1.5, `prefers-reduced-motion` respected, WebGL failure falls back to the flat version of the same layout, no more than the two GPU-heavy layers the roller allowed.
- Both themes resolve (tokens in `:root`, dark via `prefers-color-scheme` guarded by `:not([data-theme="light"])`, and `[data-theme="dark"]`), unless the palette family is single-world (terminal-core, cinematic-dark, neon-brutalist), in which case paint it explicitly.
- Typography and palette from `DESIGN.md` verbatim (the manifest carries them as `design-md`). The template carries the token names; the manifest carries the values.
- The landing or app rule set from `references/design-standards.md` section 3: hero budget, no cards in the hero, one job per section, two typefaces, nothing busy behind text.

The brief ends with: "Use the rolled tech for real. If a rolled effect fights the hierarchy, shrink the effect, never the hierarchy. Taste is DESIGN.md; the technology serves it."

## Step 4 (web): review gate (the /design-review stage), eyes-on QA, then the board

Score every variant against `references/design-standards.md` section 3 before the user sees it: classify landing / app / hybrid, check the eight hard rejections, answer the seven litmus questions (six must be YES), then the checklist items with an impact rating. Write the verdicts to `<out>/qa/review.md` in the critique format ("I notice / I wonder / What if / I think because"), quick wins first. A hard rejection or a litmus fail means the variant goes back to its builder with the specific fix, or you fix it, before the board. Never present a failing variant with a caveat.

```bash
python ~/.claude/skills/frontend-mix/scripts/screenshot.py <out>/variants --sheet <out>/contact-sheet.png
python ~/.claude/skills/frontend-mix/scripts/roll.py --board <out>
```

`screenshot.py` renders each variant in headless Chromium at 1440x900 and 390x844, captures console errors, and stitches a contact sheet. LOOK at the sheet (Read the PNG). A variant that is blank, has a console error, or fell back to flat when it should not have gets fixed by you or re-dispatched, before the user sees it. Do not present a broken variant with a caveat.

`roll.py --board` writes `<out>/board.html`: five iframes, recipe chips, a notes box per variant, and a "copy feedback" button. Open it in the browser, and publish the board or the individual variants as an Artifact if the user reviews remotely.

Then STOP. Tell the user in five lines what each variant is (one line per variant, the tech mix in words), give the board path or artifact link, and ask which one wins, or which slots to keep and re-roll. This is the human gate; do not port, polish, or iterate past it on your own.

## Step 5 (web): after the pick

- Re-roll with the kept slots locked: `roll.py --design DESIGN.md --lock hero=...`. The roller treats locked slots as fixed and randomises the rest.
- Record the choice: `roll.py --approve <out> v3`. This writes the winning recipe into `history.json` so the same mix is not rolled again as "new", and stores it under the brief for taste tracking. Add a line to the `DESIGN.md` Decisions Log naming the winning hero and why.
- Port the winner when asked: `/design-html` for a Pretext-native production page, `/frontend-build` for a React port (its Stage 1 is already done: `DESIGN.md` exists). The recipe's `ui_base` slot decides shadcn on Base UI vs Astryx. ThreeUI (community, MIT) and Canvas UI (registry, MIT + Commons Clause) become real dependencies at this stage, not before.
- Then run the full `/design-review` on the served result (it needs a URL, a clean git tree, and the gstack browse binary) and fix what it finds. The in-skill gate in Step 4 is the pre-board version of the same rules, not a replacement.

## Video mode

Read `references/video.md` first. Then:

1. Lock taste exactly as in Step 1 (a video without a `DESIGN.md` gets the consultation first). Roll with `--mode video --design DESIGN.md`. The video roll uses the slots `hero`, `material`, `type`, `palette`, `runtime` (GSAP timeline / Three.js hf-seek / HTML-in-canvas post-fx / Paper Shaders background / Spark splat flythrough); `type` and `palette` come from the file.
2. Route through `/hyperframes` (the mandatory video entry point). Run its intent layer with `flow: automation`, `storyboard: no` and hand the recipe in as constraints: `references/video.md` says which HyperFrames adapter each rolled option maps to and how it stays deterministic under `hf-seek`.
3. MVP = 2-3 scenes (hook, product moment, close), 8-15 seconds, one composition. `npx hyperframes preview`, open the browser. Take one snapshot sheet at scene midpoints and LOOK at it.
4. STOP. Show the preview, the recipe in words, and ask "render, re-roll a slot, or change the story?". Never render before that answer.

## Rules that outrank the roll

- The user's words and `DESIGN.md` beat the dice. A locked slot is locked. Dice choose technology, never taste: no round is rolled without `--design` unless the user asked for brand-free exploration in their own words.
- Nothing reaches the board without passing the Step 4 review gate. A variant that fails a hard rejection is fixed, not captioned.
- Never ship the AI-slop set: Inter, purple-to-cyan gradient hero, glass cards with neon glow, three feature cards with icons, bounce hover, emoji headings, everything centred, `rounded-lg` on everything. The roller cannot pick these; do not sneak them in as "defaults".
- Real content only. A mockup with placeholder copy tells the reviewer nothing about hierarchy.
- Free tech only; if a rolled option's package is gated, the catalog is wrong, fix the catalog, do not enter a key.
- Perf is a design constraint: a hero that loads 2 MB of JS is a variant that loses. Splats stay under ~15 MB (`.spz`), Three.js scenes cap `pixelRatio`, heavy shaders run at half resolution on mobile.
- Randomness is logged, never silent. Every variant names its recipe, every round names its seed.

## Files

| File | When to read |
|---|---|
| `references/design-standards.md` | once per session: the four house skills folded in (consultation, direction, review gate, pipeline order) |
| `assets/builder-brief.md` | Step 3, fill once per variant and paste into the sub-agent prompt |
| `references/catalog.md` | after every roll, for the rolled options only |
| `references/anti-slop.md` | once per session before building |
| `references/video.md` | video mode |
| `references/sources.md` | when the user asks "why this tech" or to refresh the catalog |
| `scripts/roll.py` | the roller, board writer, approve/history |
| `scripts/screenshot.py` | eyes-on QA |
| `assets/variant-template.html` | the skeleton every variant starts from |
| `catalog.json` | machine catalog the roller reads; edit here to add an option |
