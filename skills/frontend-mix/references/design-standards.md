# Design standards (the house pipeline, folded in)

Distilled 2026-09-04 from four skills installed on this box. Re-read the originals when refreshing this file; they are the source, this is the working copy.

| Source skill | What it owns | Where frontend-mix uses it |
|---|---|---|
| `/design-consultation` (gstack) | Proposes one coherent design system, writes `DESIGN.md` | Step 1, lock taste |
| `/frontend-design` (Anthropic) | Commit to one bold direction before code; typography carries the page | Step 3, every builder brief |
| `/design-review` (gstack) | Designer's-eye QA: hard rules, litmus checks, slop blacklist, 80-item checklist, fix loop | Step 4 review gate (in-skill), and the full skill after the port |
| `/frontend-build` | Chains the three in order: lock taste, implement, QA | The spine of this skill's web mode |

The one-line rule that came out of the first live round: **dice choose technology, never taste.** A roll that also picks palette and type produces five costumes on the same page. Lock taste first, then roll.

## 1. Lock taste (from /design-consultation)

Order of truth: the user's words, then an existing `DESIGN.md`, then a proposal you make and the user approves. Never build on a palette or type pair that nobody chose.

If `DESIGN.md` exists at the project root, read it and go. If not, run the consultation in short form:

1. **Product context, one question.** What it is, who it is for, what space, what project type (web app / dashboard / marketing / editorial / internal tool). Pre-fill from the repo and confirm.
2. **The memorable thing.** "What is the one thing someone should remember after seeing this for the first time?" One sentence. Every later decision serves it.
3. **The complete proposal, one package, with SAFE / RISK.** Propose, do not present menus. Every line has a "because".

```
AESTHETIC: <direction> — <why>
DECORATION: minimal | intentional | expressive — <why it pairs with the aesthetic>
LAYOUT: grid-disciplined | creative-editorial | hybrid — <why for this product type>
COLOR: restrained | balanced | expressive + palette hex — <why>
TYPOGRAPHY: display / body / data faces — <why these>
SPACING: base unit + density — <why>
MOTION: minimal-functional | intentional | expressive — <why>
Coherent because <how the choices reinforce each other>.
SAFE CHOICES: 2-3 category conventions you keep, and why.
RISKS: 2-3 deliberate departures; for each: what, why it works, what you gain, what it costs.
```

4. **Wait for the user.** Options: ship it, adjust a section, wilder risks, start over. Accept the final choice; nudge on coherence, never block.
5. **Write `DESIGN.md`** at the project root in this shape, then add the "Design System" pointer to the project `CLAUDE.md`:

```markdown
# Design System — <Project>
## Product Context
- **What this is:** … · **Who it's for:** … · **Space/industry:** … · **Project type:** …
## Aesthetic Direction
- **Direction:** … · **Decoration level:** … · **Mood:** … · **Memorable thing:** …
## Typography
- **Display/Hero:** <font> — <why> · **Body:** <font> — <why> · **Data/Tables:** <font, tabular-nums> · **Code:** <font>
- **Loading:** Google Fonts css2 URL · **Scale:** modular scale with px/rem per level
## Color
- **Approach:** … · **Primary:** #hex — <usage> · **Secondary:** #hex — <usage>
- **Neutrals:** #lightest … #darkest (warm or cool, never mixed) · **Semantic:** success/warning/error/info
- **Dark mode:** redesign surfaces, desaturate the accent 10-20%
## Spacing
- **Base unit:** 4px | 8px · **Density:** compact | comfortable | spacious · **Scale:** 2xs(2) xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48) 3xl(64)
## Layout
- **Approach:** … · **Grid:** … · **Max content width:** … · **Border radius:** hierarchical scale, not one radius everywhere
## Motion
- **Approach:** … · **Easing:** enter ease-out, exit ease-in, move ease-in-out · **Duration:** micro 50-100, short 150-250, medium 250-400, long 400-700 ms
## Decisions Log
| Date | Decision | Rationale |
```

`roll.py --design DESIGN.md` reads the Typography and Color blocks and locks `palette` and `type` from them. Keep the bold labels exactly as above so the parser finds them.

Font rules from the consultation: never Inter, Roboto, Arial, Helvetica, Open Sans, Lato, Montserrat, Poppins, or Space Grotesk as primary unless the user asks by name. Never Papyrus, Comic Sans, Lobster, Impact, Raleway, Clash Display, Courier New for body. Good display faces: Fraunces, Instrument Serif, General Sans, Satoshi, Cabinet Grotesk, Clash Grotesk. Good body: Instrument Sans, DM Sans, Source Sans 3, Geist, Plus Jakarta Sans. Data: Geist, DM Sans, JetBrains Mono, IBM Plex Mono with `tabular-nums`. Google Fonts is the only font host the Artifact CSP allows; if a chosen face is not on Google Fonts, pick the nearest one that is and say so in the Decisions Log.

Anti-convergence across projects: never propose the same system twice without saying why. Vary light/dark, faces, and direction between projects. Within one project, the system is fixed and the variants differ in technology, layout, and motion only.

## 2. Direction before code (from /frontend-design)

Every builder brief opens with four answers, written by you, not left to the builder:

- **Purpose.** What problem the page solves, for whom.
- **Tone.** One extreme, named in a phrase the builder can hold in their head: "tactile brutalist trading terminal", "cinematic dark product film", "warm editorial field guide". Bold maximalism and refined minimalism both work; intentionality beats intensity.
- **Constraints.** Stack, performance, accessibility, the Artifact CSP allowlist.
- **Differentiation.** The one thing someone will remember. This is the memorable thing from `DESIGN.md`, restated for this variant's hero.

Then the aesthetics rules the builder must apply:

- Typography carries the page. The display face and the body face from `DESIGN.md`, paired on purpose, a scale you stay on, weights that make hierarchy, `text-wrap: balance` on headings, ~65ch measure for running text.
- Colour commits. Dominant ground plus a sharp accent beats an even spread. Tokens in CSS variables, both themes resolve unless the palette is single-world.
- Motion is spent on one orchestrated moment (a page-load sequence with staggered reveals, or one scroll-linked move), not scattered hovers. CSS first; the rolled motion library for the choreography.
- Composition is unexpected: asymmetry, overlap, grid-breaking, generous negative space or controlled density. Never everything centred.
- Backgrounds have atmosphere: the rolled hero and material supply it. No flat single-colour hero.
- Match complexity to the vision: maximal directions need elaborate code, minimal ones need precision in spacing and type.

## 3. Review gate (from /design-review)

The full `/design-review` needs a served URL, a clean git tree, and the gstack browse binary. It runs after the port, on the real app. Before the board, every variant passes this in-skill gate instead. Run it on the rendered screenshots, not the source, and write the verdict into `<out>/qa/review.md`, one block per variant.

**Classify first.** MARKETING/LANDING (hero-driven, conversion-focused) uses the landing rules. APP UI (workspace, data-dense, task-focused) uses the app rules. HYBRID splits by section.

**Hard rejections. Any one of these fails the variant; fix before the board, never present with a caveat.**

1. Generic SaaS card grid as the first impression.
2. Beautiful image or effect with a weak brand.
3. Strong headline with no clear action.
4. Busy imagery or effect behind text (the first live round failed this twice: wireframe grid under the paragraph, ghost headline over the headline).
5. Sections repeating the same mood statement.
6. Carousel with no narrative purpose.
7. App UI made of stacked cards instead of layout.
8. Anything on the slop blacklist below.

**Litmus, answer YES/NO for each. Six of seven must be YES.**

1. Brand or product unmistakable in the first screen?
2. One strong visual anchor present?
3. Page understandable by scanning headlines only?
4. Each section has one job?
5. Are the cards actually necessary?
6. Does the motion improve hierarchy or atmosphere?
7. Would it still feel premium with every decorative shadow removed?

**Landing rules.** First viewport reads as one composition, a poster not a document. Hierarchy: brand > headline > body > CTA. Hero budget: brand, one headline, one supporting sentence, one CTA group, one image or live effect. No cards in the hero. One job per section: one purpose, one headline, one short sentence. Two typefaces max. Motion: two or three intentional motions (entrance, scroll-linked, hover or reveal). Copy is product language, not design commentary; if deleting 30% improves it, keep deleting.

**App UI rules.** Calm surface hierarchy, strong type, few colours, dense but readable, minimal chrome. Primary workspace, navigation, secondary context, one accent. No dashboard-card mosaics, thick borders, decorative gradients, ornamental icons. Headings say what the area is or what the user can do.

**Universal.** CSS variables for the colour system. No default font stacks. Body text 16px or larger and 4.5:1 contrast. Cards earn their existence. Visited links differ from unvisited. Headings sit closer to what they introduce than to what came before.

**Slop blacklist (instant fail).** Purple/violet/indigo gradients or blue-to-purple schemes. The three-column feature grid with icons in coloured circles. Icons in coloured circles as decoration. Everything centred. Uniform bubbly radius on every element. Decorative blobs, floating circles, wavy dividers. Emoji as design elements. Coloured left border on cards. Generic hero copy ("Welcome to", "Unlock the power of", "Your all-in-one"). Cookie-cutter section rhythm with every section the same height. `system-ui` or `-apple-system` as the primary face.

**Checklist items a single-file page can be scored on** (impact high / medium / polish; screenshots are the evidence):

- Hierarchy: one focal point, one primary CTA per view, purpose readable in 3 seconds, squint test passes, white space intentional.
- Typography: at most 3 faces, scale on a ratio (1.25 or 1.333), body line-height 1.5 and headings 1.15-1.25, 45-75 character measure, no skipped heading levels, at least 2 weights, `tabular-nums` on number columns, no letterspacing on lowercase, curly quotes and a real ellipsis.
- Colour: at most 12 non-grey colours, WCAG AA, neutrals consistently warm or cool, dark mode with elevation not inversion, off-white text on dark, `color-scheme` set.
- Spacing: one scale (4 or 8 base), consistent alignment, radius hierarchy, no horizontal scroll on mobile, max content width set.
- Interaction: hover on every interactive element, `focus-visible` never removed without a replacement, `cursor: pointer`, touch targets 44px.
- Responsive: the mobile layout makes design sense, not just stacked desktop columns; 16px body on mobile; no `user-scalable=no`.
- Motion: ease-out in, ease-in out; 50-700 ms; only `transform` and `opacity`; no `transition: all`; `prefers-reduced-motion` respected.
- Content: no lorem, no happy talk ("Welcome to…"), no visible instructions longer than a sentence, active voice, specific button labels.
- Performance as design: fonts `display=swap` with preconnect, images with dimensions and `loading="lazy"`, no layout shift while the GPU layer loads.

**Critique format** for the notes you write: "I notice… / I wonder… / What if… / I think… because…". Specific and actionable, "change X to Y because Z", never "the spacing feels off". Quick wins first: the 3-5 highest-impact fixes under 30 minutes each.

## 4. Pipeline order (from /frontend-build)

Trivial edit: no pipeline, just do it. New page or section: lock taste, build, gate, board. New project or redesign: all stages plus `/plan-design-review` when the build is more than three steps. After the human pick: `/design-html` for a Pretext-native production page, `/frontend-build` for a React port, then the full `/design-review` on the served result, then lighthouse. Component sources at port time: shadcn on Base UI with tweakcn tokens, originui, kokonutui; never a paid kit.
