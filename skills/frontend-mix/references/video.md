# Video mode: rolled tech into HyperFrames

HyperFrames renders video from an HTML composition whose timing is declared with `data-*` attributes and whose animation runtime is seekable. `/hyperframes` is the mandatory entry point and owns routing; this file only says how a frontend-mix roll maps onto its adapters and how each option stays deterministic under `hf-seek`. Read `/hyperframes-core` (`references/minimal-composition.md`, `determinism-rules.md`) and `/hyperframes-animation` (`adapters/three.md`, `adapters/html-in-canvas-patterns.md`) before writing composition HTML.

## The MVP contract

- One composition, 2-3 scenes: hook (0-3 s), product moment (3-10 s), close (10-13 s). 8-15 s total, 1920x1080 unless the destination says otherwise.
- `npx hyperframes preview` opens it in the browser. Take a snapshot sheet at scene midpoints and LOOK at it.
- No render until the user answers "render, re-roll a slot, or change the story?". This is the human gate; HyperFrames also keeps rendering user-gated in both modes.

Route: `/hyperframes` → intent layer with `flow: automation`, `storyboard: no` (so it does not re-ask what the roll already decided) → `/product-launch-video` when a product is being launched or demoed, `/motion-graphics` for a short title or reveal. Hand the recipe in as constraints on `frame.md` (design system) and `STORYBOARD.md` (per-scene visual notes). Rendering, captions, audio (`/media-use`) stay with those skills.

## Slot to adapter map

| Rolled option | HyperFrames adapter | Determinism rule |
|---|---|---|
| `runtime: gsap-timeline` | default: one paused GSAP timeline on `window.__timelines["main"]` | Already seekable. Compose 2-4 atomic rules from `hyperframes-animation/rules-index.md`. |
| `runtime: three-hf-seek`, `hero: three-procedural / instanced-particles / ascii-dither-object` | `adapters/three.md` | Render from `hf-seek` time, never from `requestAnimationFrame`. Set `data-duration` on the root (three has no duration inference). Preload every asset before the first seek. |
| `runtime: splat-flythrough`, `hero: splat` | three adapter + Spark `SplatMesh` | Load the `.spz` with `await` before registering; drive camera position from time (`camera.position.lerpVectors(a, b, t)`); `renderer.render` in the `hf-seek` handler. Keep the splat under ~15 MB; `sparkjs.dev/assets/splats/*.spz` are public samples for MVPs. |
| `runtime: paper-shader-bg`, `hero: paper-shader` | none native; mount with `new ShaderMount(el, fragment, uniforms, undefined, 0 /* speed */, frame)` | Verified on 2026-09-04 in `shader-mount.d.ts`: the constructor takes `speed` (0 = stopped) and `frame` (offsets `u_time` for deterministic results); `setSpeed`, `setUniforms`, `dispose` exist. No frame setter was seen. For a seekable background either re-mount with the new `frame` on each `hf-seek` (cheap: one quad), or keep speed 0 and animate the shader's own uniforms (colours, distortion, scale) through GSAP `onUpdate` → `setUniforms`. Verify with `npx hyperframes check`. |
| `runtime: html-in-canvas-postfx`, `hero: canvas-fx-over-dom` | `adapters/html-in-canvas-patterns.md` | Chrome 148-150 origin trial (`layoutsubtree` + `drawElementImage`); the adapter's boilerplate includes feature detection and a GPU-overlay fallback. Use for one or two hero beats, not every beat. |
| `material: liquid-glass / gooey` | CSS + SVG filters, animated via GSAP on the filter primitives (`feDisplacementMap` scale, `feTurbulence` seed/baseFrequency) | Filters are stateless per frame, so any seek is exact. Expensive: one surface, not ten. |
| `material: liquid-metal` | Paper Shaders `liquidMetalFragmentShader` on the logo mark | Same rule as `paper-shader-bg`. |
| `material: border-beam` | CSS conic-gradient mask, angle driven by GSAP | Exact under seek. |
| `type: variable-kinetic` | CSS `font-variation-settings` tweened by GSAP | Exact under seek. Keep the resting frame at readable axes. |
| `palette: *` | tokens in `frame.md` | Single-world palettes (terminal-core, cinematic-dark, neon-brutalist) paint explicitly; the others pick one theme for the video. |

## Scene recipe by hero

- **three-procedural**: hook = camera pushes through the scene onto the product name; product moment = DOM UI card floats in front of the scene (z-index, not in-canvas); close = scene dims to the accent.
- **splat**: hook = flythrough of the captured object/space; product moment = freeze, headline lands with `type` slot treatment; close = splat dissolves via `SplatMesh` opacity.
- **paper-shader**: hook = mesh gradient / neuro noise at full bleed with a single word; product moment = shader retreats to a panel behind the UI; close = liquid-metal logo.
- **canvas-fx-over-dom**: hook = the actual UI shatters or liquefies into place; product moment = clean UI, one glass surface; close = VHS or decrypt-reveal on the URL.
- **kinetic-type-only**: hook = one word at viewport scale, axes animating; product moment = UI screenshot with kinetic labels; close = wordmark settles.
- **instanced-particles**: hook = particles assemble the wordmark; product moment = they scatter into a bento of UI tiles; close = collapse to the accent dot.
- **ascii-dither-object**: hook = product object as ASCII, resolves to shaded; product moment = UI beside it; close = back to ASCII.

## What not to do

- No `requestAnimationFrame` loops as the source of truth; HyperFrames seeks, it does not play.
- No lazy asset fetches inside a seek handler.
- No render before the human gate.
- No more than two GPU-heavy layers in a scene (the roller already enforces this per recipe; scenes inherit it).
