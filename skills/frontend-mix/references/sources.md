# Sources and provenance (2026-09-04)

Three inputs went into the catalog. Every claim below was read on 2026-09-04 unless marked.

## Input 1: Fable research (this session)

- skills.sh leaderboard, 8-week installs: frontend-design 852.2K (anthropics/skills), anti-ui-slop 658.5K (uizze.com), web-design-guidelines 605.9K (vercel-labs/agent-skills), design-taste-frontend 441.3K + high-end-visual-design 326.8K + minimalist-ui 299.9K + industrial-brutalist-ui 279.6K (leonxlnx/taste-skill, 84.2K stars), ui-ux-pro-max 343.6K (nextlevelbuilder). https://skills.sh/
- Impeccable, Paul Bakaus, 64.7K stars (pasqualepillitteri.it roundup).
- Three.js r182 (Dec 2025) WebGPURenderer default, ~2.7M weekly; WebGPU Baseline Jan 2026, ~95%; TSL; R3F v9 + drei. https://www.youngju.dev/blog/culture/2026-05-14-3d-development-for-web-three-js-react-three-fiber-webgpu-gaussian-splatting-deep-dive-2026.en
- Spark 2.0 (World Labs) LoD streaming; "most influential 2025" per swyvl roundup. https://www.worldlabs.ai/blog/spark-2.0
- Paper Shaders: 30+ shaders, v0.0.80, zero deps. https://github.com/paper-design/shaders
- Motion 3.6M weekly / 30.7K stars; GSAP 1.47M / 23.6K, free; Anime.js v4 66K stars / 319K weekly; Lenis <4 kB. LogRocket, spell.sh, Alignify roundups.
- Scroll-driven animations + View Transitions cross-browser; claimed to replace 70-80% of decorative library motion. mintec.co, frontendhorizon.com.
- shadcn: Base UI default July 2026, 2:1 over Radix; Base UI 6M+ weekly at 1.6.0. https://ui.shadcn.com/docs/changelog/2026-07-base-ui-default
- 21st.dev Magic MCP, 12,000+ components. https://github.com/21st-dev/magic-mcp
- DESIGN.md: Google Labs spec open-sourced 21 Apr 2026; VoltAgent/awesome-design-md. https://ossinsight.io/blog/design-md-protocol-2026
- Claude Design launched 17 Apr 2026. Peter Yang on X: "design system integration feels best in class for AI... burns through usage quickly" (via rohitg00/awesome-claude-design "X signal").
- Trends reality check (held / faded): https://dev.to/studiomeyer_io/web-design-trends-2026-what-actually-held-up-after-six-months-23p8
- AI-slop tells: https://www.925studios.co/blog/ai-slop-web-design-guide

## Input 2: Grok list (user-supplied), verified items

- ThreeUI (Meng To): github.com/MengTo/threeui, 5.1K stars, MIT (community), 50 community parent components, 141 free variants, npm `@designcodeio/threeui` 1.2.0; Pro via CLI OAuth, not on npm. UNVERIFIED: Grok's claim that each component ships a skill file for Claude/Cursor (threeui.com fetch showed no such section). React-only; a port target, not a single-file dependency.
- Canvas UI (David Haz): github.com/DavidHDev/canvas-ui, 4.5K stars, MIT + Commons Clause, 35+ effects, shadcn-registry install (`npx shadcn@latest add @canvas-ui/<effect>-react`), React/Vue/Svelte/Solid/Preact/vanilla TS, WebGL2 default or WebGPU via vgpu. Relies on HTML-in-canvas (Chrome 148-150 origin trial, stable est. late 2026, Chrome-only) with GPU-overlay fallback.
- Astryx (Meta): github.com/facebook/astryx, public beta 28 Jun 2026, MIT, 150+ components, 10 themes (default, neutral, daily, butter, chocolate, matcha, stone, gothic, brutalist, y2k), CLI + MCP server, built on StyleX but ships pre-built CSS.
- StyleX "all the rage on X" after the Cursor migration from Tailwind (This Week In React #295). vgpu = Vercel WebGPU library "designed for agents", CLI verification without a GPU.
- libraries.dev (Jakub Antalik): Beam (`border-beam`), Orb (`thinking-orbs`), Gooey (`liquid-gooey`), Metal (`metal-fx`), Image (`img-fx`), MIT, free on npm; Pro adds agent skills. React; port stage.
- Emil Kowalski: favourite libraries post (NumberFlow, input-otp, Liveline, Leva, cmdk, Virtuoso, dnd kit, Sonner) and his `pick-ui-library` skill (github.com/emilkowalski/skills) which also maps torph, Cobe, Satori, shiki, recharts, zustand, clsx, cva, next-themes. Port stage.
- React `<ViewTransition>` still Canary as of 19.2.7 (Jun 2026); expected stable in 19.3. Do not claim it shipped.
- Skiper UI (24 free / 54 premium, shadcn), FeralUI (physics demos, Sarthak Navalekar), Rare UI, BeUI: inspiration only; premium tiers excluded.
- Liquid glass ports, HeroUI v3 (React Aria, Tailwind v4), Kibo UI, Fragments UI (MCP-native), motionsites.ai / kinetics.colorion.co / originkit.dev catalogs: named by Grok, not individually verified this session.

## Input 3: Opus artifact

`https://claude.ai/code/artifact/d2981e62-00c8-455d-b09a-74697bf07906` could not be read (served as public reader, not enabled). NOT folded in yet. When the user pastes it, diff against this file and add new options to `catalog.json`.

## CDN verification (curl, 2026-09-04)

cdnjs: three.js 0.185.1, gsap 3.15.0, animejs 4.5.0 (lenis absent). jsdelivr 200: lenis 1.3.26, @paper-design/shaders 0.0.80, @sparkjsdev/spark 2.1.0 (peer three>=0.180.0, `dist/spark.module.js`), motion 13.2.0, three 0.182.0 module + webgpu builds, vgpu 0.4.0. Paper Shaders `ShaderMount(parentElement, fragmentShader, uniforms, webGlContextAttributes?, speed?, frame?, minPixelRatio?, maxPixelCount?, mipmaps?)` from `dist/shader-mount.d.ts`. Spark public samples: `https://sparkjs.dev/assets/splats/{butterfly,cat,fly}.spz`.
