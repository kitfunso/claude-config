# Anti-slop rules (read once per session)

Distilled from Anthropic's `frontend-design` (installed locally), leonxlnx/taste-skill's three dials, Paul Bakaus's Impeccable, uizze's anti-ui-slop, and the mid-2026 "what held up" reality checks. The point is not "be tasteful". The point is: an AI that picks the statistical average produces the same page as every other AI, and readers now recognise it in under a second.

## The tells (never ship, even as a "default")

- Purple-to-cyan (or blue) gradient behind the hero.
- Glass cards with a faint neon glow. Glass is fine; glow-on-glass-on-gradient is the tell.
- Inter, Space Grotesk, or Roboto as the only face. Every weight of Inter is still Inter.
- Three feature cards in a row: icon, heading, exactly two lines.
- Bounce or scale-on-hover on everything. Motion nobody asked for.
- Emoji as section markers. Numbered 01/02/03 markers on content that is not a sequence.
- Everything centred. `rounded-lg` on every block. One shadow stamped on every card.
- Warm cream (#F4F1EA) + serif + terracotta as the "premium" default. It was original in 2025.
- Near-black + one acid green pop as the "dev tool" default. Same story.
- A Spline scene in the hero "for wow". 800 kB-2 MB of JS; reviewers now dock points for it.
- Kinetic typography that never ships because it fails accessibility and performance. If you roll `kinetic-type-only`, make it honour `prefers-reduced-motion` and stay legible at rest.

## What the good skills do instead

**Commit to a direction before code** (frontend-design). Name the tone in one phrase: "tactile brutalist trading terminal", "cinematic dark product film", "warm editorial field guide". Every choice after that serves the phrase. Intentionality beats intensity; minimal done with precision is as bold as maximal.

**Three dials, set deliberately** (taste-skill): DESIGN_VARIANCE (centred, safe layout at 1; asymmetric, overlapping at 10), MOTION_INTENSITY (hover only at 1; scroll choreography at 10), VISUAL_DENSITY (airy at 1; data-dense at 10). The roller's `layout` and `motion` slots set two of these; you set density from the subject (a trading desk page is dense, a manifesto is airy). State the three numbers in the sub-agent brief.

**Teach by anti-pattern** (Impeccable, anti-ui-slop): the list above exists because "don't make AI slop" does nothing, while "no purple gradient, no three cards" does.

**Spend boldness in one place** (artifact-design): one aesthetic risk per variant, everything around it quiet. If the roll gives you a splat hero AND liquid glass AND neon brutalist palette, the roller already blocked that. If the roll gives you two loud things, pick which one leads and make the other its supporting act.

**Subject vernacular as content, not ornament**: a page for a crude oil desk shows $/bbl and tenor labels; a page for an npm package shows the real install line and a real changelog date. One detail only this subject would have, per variant, minimum.

**Typography carries the page**: pair the rolled display face with the rolled body face on purpose, set a scale and stay on it, ~65ch measure for running text, `tabular-nums` wherever digits align, uppercase labels with a touch of letter-spacing.

**Neutrals are chosen**: tint every grey toward the accent or the ground. Pure #888 reads as unconsidered.

**Show the page at rest**: first frame is readable with the GPU layer off. Motion adds on top.

## Rules from the 2026 reality check (Studio Meyer, six months in)

Held up: bento grids (make cells unequal and one cell live, otherwise it is a template), dark mode as a first-class theme, design systems as a prerequisite, anti-grid brutalism as the counter-move to bento.

Faded or restrained: glassmorphism 2.0 (keep `backdrop-filter` to one or two surfaces; it is expensive), organic blobs (landing pages only), 3D everywhere (budget it: one GPU hero, capped pixel ratio, half-res on mobile, flat fallback).

New and load-bearing: the page must be readable by agents too. Semantic HTML, real headings, `aria-label` on the decorative canvas, a `<title>` that names the product.
