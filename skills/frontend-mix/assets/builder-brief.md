# Builder brief for {{VARIANT_ID}} (fill every field; paste into the sub-agent prompt verbatim)

You are building one single-file HTML variant for a design round. Write exactly one file: `{{OUT_PATH}}`. Do not touch any other file. Start from the skeleton at `{{TEMPLATE_PATH}}`.

## Direction (decided, not yours to change)

- **Purpose:** {{PURPOSE}}
- **Tone, one phrase:** {{DIRECTION_PHRASE}}
- **The memorable thing:** {{MEMORABLE_THING}}
- **Dials:** DESIGN_VARIANCE {{VARIANCE}}/10 · MOTION_INTENSITY {{MOTION}}/10 · VISUAL_DENSITY {{DENSITY}}/10
- **Page class:** {{PAGE_CLASS}} (landing | app | hybrid). Apply that rule set from the review gate below.

## Taste (locked from DESIGN.md, use verbatim)

- Display face: {{DISPLAY_FONT}} · Body face: {{BODY_FONT}} · Data face: {{DATA_FONT}}
- Tokens: bg {{BG}} · ink {{INK}} · accent {{ACCENT}} · muted {{MUTED}}
- Spacing base {{SPACE_BASE}}px, density {{DENSITY_WORD}}, radius scale {{RADIUS_SCALE}}
- Motion approach: {{MOTION_APPROACH}}; easing enter ease-out / exit ease-in / move ease-in-out
- Google Fonts link: {{FONTS_LINK}}

## Technology (rolled, use it for real)

Recipe:

```json
{{RECIPE_JSON}}
```

Importmap and scripts, paste verbatim from the manifest, never retype:

```json
{{IMPORTMAP_JSON}}
```

Catalog snippets for the rolled options:

{{CATALOG_SNIPPETS}}

Use the rolled hero, material, and motion for real. A `splat` hero loads a real `.spz` through Spark. `liquid-glass` has the SVG `feDisplacementMap` refraction. `gsap-lenis` has a pinned section. The technology is the reason this variant exists; the taste is the reason it will be picked.

## Content (real, no placeholders)

{{CONTENT}}

## Rules that fail the variant if broken

- First viewport is one composition, a poster not a document. Hero budget: brand, one headline, one supporting sentence, one CTA group, one live effect. No cards in the hero.
- Nothing busy behind text. If the hero effect crosses running text, it drops to a level where the text wins, or moves.
- Two typefaces on the page, three at most with the data face. Body 16px or larger, 4.5:1 contrast. Headings `text-wrap: balance`. Running text 45-75 characters wide. `tabular-nums` on numbers.
- One job per section. If deleting 30% of the copy improves it, delete it. No "Welcome to", no "Unlock", no "all-in-one".
- Never centre everything. Never one radius on everything. No three-column icon-card grid. No purple gradient. No blobs, no wavy dividers, no emoji as decoration. No `system-ui` as the primary face.
- Motion: one orchestrated moment (load sequence or one scroll-linked move) plus hover states. `prefers-reduced-motion` respected. Only `transform` and `opacity` animate. No `transition: all`.
- Visible at rest: the first frame shows the page with the GPU layer off. WebGL failure falls back to the flat version of the same layout. `pixelRatio` capped at 1.5, half resolution on mobile for heavy shaders.
- Single self-contained HTML. Scripts only from `cdnjs.cloudflare.com` or `cdn.jsdelivr.net/npm/`, fonts only from Google Fonts. Both themes resolve unless the palette is single-world.
- When a texture or particle field samples text, position it from the live element's `getBoundingClientRect` / `Range.getClientRects`.
- Keep the `.recipe-chip` in the corner listing the mix.
- Mobile is a design, not stacked desktop columns. Check 390px wide.

Finish by listing, in three lines, the one bold move you made, the one thing you cut, and anything in the recipe you could not make work and why.
