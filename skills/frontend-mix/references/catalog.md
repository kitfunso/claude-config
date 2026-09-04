# Catalog: the rolled options, how to use each in a single-file HTML

Read only the entries you rolled. Every CDN URL below returned 200 on 2026-09-04 and sits on the Artifact CSP allowlist (cdnjs, cdn.jsdelivr.net/npm, fonts.googleapis.com). Versions are pinned in `catalog.json`; the roller pastes the importmap and script tags into `manifest.json` for you. All free / open source.

## hero

### three-procedural (ThreeUI-style scene)
What: a procedural Three.js scene (wireframe terrain, morphing icosahedron, metaballs via marching cubes, torus knots in fog). ThreeUI (MengTo, 5.1K stars, MIT community tier) is React-only, so treat it as the reference look and port later; in a single file you write plain three.
```html
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.182.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.182.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from "three";
const canvas=document.getElementById("hero-gpu");
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});
renderer.setPixelRatio(window.__pixelRatio);
const scene=new THREE.Scene(), camera=new THREE.PerspectiveCamera(40,1,0.1,100); camera.position.z=6;
const mesh=new THREE.Mesh(new THREE.IcosahedronGeometry(2,3),new THREE.MeshNormalMaterial({wireframe:true})); scene.add(mesh);
function size(){const {clientWidth:w,clientHeight:h}=canvas.parentElement; renderer.setSize(w,h,false); camera.aspect=w/h; camera.updateProjectionMatrix();}
addEventListener("resize",size); size();
let t=0; (function loop(){ mesh.rotation.y=t+=0.004; renderer.render(scene,camera); if(!window.__reducedMotion) requestAnimationFrame(loop); })();
</script>
```
Caveat: WebGPURenderer is r182's default in docs but `three.webgpu.js` is a separate build; stick to WebGLRenderer in mockups (works everywhere, no async init). Use `MeshPhysicalMaterial` with `transmission` for glassy objects only with one light; it is expensive.

### splat (Gaussian splat via Spark)
What: a real 3D capture in the hero. Spark 2.1.0 (World Labs), peer `three>=0.180.0`. Public samples for MVPs: `https://sparkjs.dev/assets/splats/butterfly.spz`, `cat.spz`, `fly.spz` (each a few MB). For a product, capture with Luma/Polycam/Scaniverse and export `.spz` under ~15 MB.
```html
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.182.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.182.0/examples/jsm/","@sparkjsdev/spark":"https://cdn.jsdelivr.net/npm/@sparkjsdev/spark@2.1.0/dist/spark.module.js"}}</script>
<!-- the three/addons/ entry is mandatory: spark.module.js imports three/addons/postprocessing/Pass.js and fails to resolve without it (found in the first live round, 2026-09-04) -->
<script type="module">
import * as THREE from "three";
import { SplatMesh, SparkRenderer } from "@sparkjsdev/spark";
const renderer=new THREE.WebGLRenderer({canvas:document.getElementById("hero-gpu"),antialias:false,alpha:true});
renderer.setPixelRatio(Math.min(window.__pixelRatio,1.25));
const scene=new THREE.Scene(); scene.add(new SparkRenderer({renderer}));
const camera=new THREE.PerspectiveCamera(50,1,0.05,100); camera.position.set(0,0,2.2);
const splat=new SplatMesh({url:"https://sparkjs.dev/assets/splats/butterfly.spz"}); splat.quaternion.set(1,0,0,0); scene.add(splat);
function loop(t){ splat.rotation.y=t*0.0003; renderer.render(scene,camera); if(!window.__reducedMotion) requestAnimationFrame(loop);} loop(0);
</script>
```
Caveat: heavy. Never stack with `canvas-fx-over-dom` (roller blocks it). Splat files load async; show the layout at rest underneath and fade the canvas in on first render.

### paper-shader (Paper Shaders full-bleed)
What: Paper Design's 30 GPU shaders (mesh gradient, neuro noise, god rays, dot orbit, water, dithering, grain, liquid metal), zero deps, 0.0.80. Vanilla API verified in `dist/shader-mount.d.ts`:
`new ShaderMount(parentElement, fragmentShader, uniforms, webGlContextAttributes?, speed?, frame?, minPixelRatio?, maxPixelCount?, mipmaps?)` with `setSpeed(s)`, `setUniforms(u)`, `dispose()`, and `getShaderColorFromString("#hex")` for colour uniforms.
```html
<script type="importmap">{"imports":{"@paper-design/shaders":"https://cdn.jsdelivr.net/npm/@paper-design/shaders@0.0.80/dist/index.js"}}</script>
<script type="module">
import { ShaderMount, meshGradientFragmentShader, getShaderColorFromString } from "@paper-design/shaders";
const el=document.getElementById("hero"); // ShaderMount creates its own canvas inside the parent
const mount=new ShaderMount(el, meshGradientFragmentShader, {
  u_colors:[ "#0A0C0A","#7CFF6B","#1F3A22","#D6F5C9" ].map(getShaderColorFromString), u_colorsCount:4,
  u_distortion:0.8, u_swirl:0.1, u_grainMixer:0, u_grainOverlay:0, u_scale:1, u_rotation:0, u_offsetX:0, u_offsetY:0, u_fit:0
}, undefined, window.__reducedMotion?0:0.6);
</script>
```
Caveat: uniform names differ per shader; when unsure, `import * as S from "@paper-design/shaders"` and read `S.meshGradientFragmentShader` in the console for the `uniform` declarations, or open the React wrapper's defaults in the repo. Mount into a `position:relative` element; the shader canvas is `position:absolute; inset:0`, so keep the content in a `z-index:1` sibling.

### canvas-fx-over-dom (Canvas UI style)
What: the live UI is captured and pushed through a GLSL effect (liquid, shatter, VHS, decrypt, particle reveal). Canvas UI (DavidHDev, 4.5K stars, MIT + Commons Clause, 35+ effects) does this with the HTML-in-canvas API, which is a Chrome 148-150 origin trial only. In a single file, do the portable version: render the effect in a WebGL quad over the DOM with `pointer-events:none`, sampling a snapshot texture you build yourself (draw the hero's text into an offscreen 2D canvas with the same fonts, then use it as a texture) or use `mix-blend-mode` + the effect as a distortion field only.
Minimal pattern: one fullscreen quad, fragment shader with `u_time`, `u_mouse`, `u_tex`; feature-detect `HTMLCanvasElement.prototype.layoutsubtree` for the real API; fall back to the snapshot path. Keep it to the hero; it is heavy.

### ascii-dither-object
What: a Three.js object drawn as ASCII (`three/addons/effects/AsciiEffect.js`, still shipped in 0.182.0 examples) or ordered-dither postprocess. Terminal-core and cult-indie palettes love it.
```js
import { AsciiEffect } from "three/addons/effects/AsciiEffect.js";
const effect=new AsciiEffect(renderer," .:-=+*#%@",{invert:true,resolution:0.2});
effect.setSize(w,h); effect.domElement.style.cssText="position:absolute;inset:0;color:var(--ink);background:transparent;pointer-events:none";
canvas.replaceWith(effect.domElement); // then effect.render(scene,camera) in the loop
```

### kinetic-type-only (no GPU)
What: the hero is one line of viewport-scaled type with animated variable axes or split-letter choreography. Requires a `type` slot with a variable or display face. Keep the resting frame legible; `prefers-reduced-motion` stops the axes. Native CSS for the axis loop, GSAP SplitText is club-only, so split letters with a 5-line JS helper.

### instanced-particles
What: 10k-100k points or `InstancedMesh` forming the wordmark or logo from sampled canvas text, then scattering on scroll/mouse. Sample positions by drawing the word into a 2D canvas and reading `getImageData` alpha. `THREE.Points` with a `PointsMaterial({size:0.02})` is enough; a custom `ShaderMaterial` for the morph if the motion slot is gsap-lenis.

## material

- **liquid-glass**: `backdrop-filter: blur(18px) saturate(1.4)` + `filter:url(#liquid-glass)` on ONE surface, 1px inner highlight (`box-shadow: inset 0 1px 0 rgba(255,255,255,.35)`), a subtle specular gradient. Template ships the `#liquid-glass` filter. Roller blocks it with neon-brutalist and anti-grid.
- **gooey**: parent `filter:url(#gooey)` (template ships it); children are blobs/nav pills that fuse when close. Works for menus, cursors, tag clouds. libraries.dev `liquid-gooey` is the React reference.
- **liquid-metal**: Paper Shaders `liquidMetalFragmentShader` mounted on the logo mark only (small element, cheap). Same mount pattern as paper-shader; uniforms include `u_colorBack`, `u_colorTint`, `u_repetition`, `u_softness`, `u_shiftRed`, `u_shiftBlue`, `u_distortion`, `u_contour`, `u_shape`, `u_angle` (check the fragment source if a name errors).
- **border-beam**: pseudo-element with `background: conic-gradient(from var(--a), transparent 70%, var(--accent))`, masked to a 1px ring via `mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)` + `mask-composite: exclude`, `@property --a` animated. libraries.dev `border-beam` is the React reference.
- **tactile-brutalist**: 1px solid `var(--ink)` borders, no radius, `box-shadow: 4px 4px 0 var(--ink)`, paper grain via an SVG `feTurbulence` overlay at 4% opacity, buttons that translate 2px on press. Blocked with glass-soft-futurism.
- **flat-editorial**: no cards at all. Hairline rules (`border-top:1px solid var(--rule)`), generous measure, type scale does the hierarchy.

## motion

- **gsap-lenis**: `<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.15.0/gsap.min.js">`, `.../ScrollTrigger.min.js`, `<script src="https://cdn.jsdelivr.net/npm/lenis@1.3.26/dist/lenis.min.js">`. Wire: `const lenis=new Lenis(); lenis.on("scroll",ScrollTrigger.update); gsap.ticker.add(t=>lenis.raf(t*1000)); gsap.ticker.lagSmoothing(0);`. One pinned section with a scrubbed timeline beats ten fade-ups.
- **native-scroll-driven**: `animation-timeline: view()` / `scroll()` with `animation-range: entry 0% cover 40%`, zero JS. Progressive: wrap in `@supports (animation-timeline: view())`. Pair with `scroll-snap` for horizontal-scroll layouts.
- **view-transitions-motion**: `<script src="https://cdn.jsdelivr.net/npm/motion@13.2.0/dist/motion.js">` exposes `Motion.animate`, `Motion.inView`, `Motion.scroll`, `Motion.spring`. Use `document.startViewTransition` for tab/state swaps with `view-transition-name` on the moving element, and Motion springs for the rest. React `<ViewTransition>` is still Canary; this is the vanilla path.
- **anime-v4**: `<script src="https://cdnjs.cloudflare.com/ajax/libs/animejs/4.5.0/anime.iife.min.js">` exposes `anime.animate`, `anime.createTimeline`, `anime.stagger`, `anime.createDraggable`. Draggable cards and staggered grids are its strength.
- **css-micro-only**: hover/focus/press transitions on real controls, one page-load sequence via `@keyframes` with `animation-delay`. Nothing moves on scroll. Precision beats motion here.

## type (Google Fonts, query strings in catalog.json)

- **condensed-grotesque**: Barlow Condensed 500/700 display, IBM Plex Sans body. Tight leading, uppercase eyebrows.
- **editorial-serif**: Fraunces (opsz axis; use 144 for display, 9 for small) display, Schibsted Grotesk body.
- **mono-terminal**: JetBrains Mono everywhere; use weight, size, and colour, not a second face. `tabular-nums` by default.
- **variable-kinetic**: Anybody (wdth 50-150) or Roboto Flex (wdth/opsz/wght). Animate `font-variation-settings` only; never `font-size` for the kinetic effect.
- **wide-grotesque**: Bricolage Grotesque display at wdth 75-100 / opsz 96, Source Serif 4 body. The width contrast is the personality.

## layout

- **bento**: CSS grid, `grid-auto-flow: dense`, cells spanning 1x1 / 2x1 / 2x2; one cell live (a canvas, a ticking number, a mini chart). Equal cells = template.
- **anti-grid-brutalist**: absolute/negative-margin offsets, blocks overlapping by 12-40px, rotated labels, text that runs into the edge. Grid exists underneath; the design breaks it on purpose.
- **editorial-columns**: `columns: 2` or a 12-col grid with hairline rules between, drop cap on the first paragraph, pull quotes across columns.
- **data-dense**: tables with `tabular-nums`, 28px rows, sparklines (inline SVG or canvas), sticky headers, chips for state. The desk-page default.
- **single-column-manifesto**: 65ch column, display type at `clamp(2.5rem, 8vw, 7rem)`, sections separated by whitespace not rules, one image or canvas per screen.
- **horizontal-scroll**: `scroll-snap-type: x mandatory` sections or a GSAP pinned horizontal tween; a progress rail; mobile falls back to vertical.

## palette (tokens in catalog.json)

Nine families from rohitg00/awesome-claude-design, each with `bg / ink / accent / muted` starting tokens in `catalog.json`. Adjust toward the subject; the tokens are a starting key, not a spec. `single_world: true` families (terminal-core, cinematic-dark, neon-brutalist) skip the light/dark media blocks and paint explicitly.

## ui_base (port target only, not used in the mockup)

- **shadcn-base-ui**: `npx shadcn@latest init` (Base UI is the default since July 2026).
- **astryx**: Meta's system, `npx astryx@latest init`, MCP server for agent-readable components, 10 themes (`brutalist`, `gothic`, `y2k` map well onto the louder palettes).
- **handrolled**: keep the single-file CSS, extract components by hand.

## Port-stage libraries (React; not for the single file)

ThreeUI (`@designcodeio/threeui`), Canvas UI (`npx shadcn@latest add @canvas-ui/<effect>-react`), libraries.dev (`border-beam`, `thinking-orbs`, `liquid-gooey`, `metal-fx`, `img-fx`), Emil Kowalski's picks (NumberFlow, input-otp, Liveline, Leva, cmdk, Virtuoso, dnd kit, Sonner, torph, Cobe, Satori, shiki), R3F v9 + drei for three in React, vgpu for WebGPU in React. Bring them in when porting the winner, per `ui_base`.
