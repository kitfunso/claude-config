# UI Overlay

Project-type specific gates for UI projects (React, Next, Vue, Svelte, Solid, Astro, Nuxt, Remix).

## Detection signals
- Frontend frameworks: `react`, `next`, `vue`, `svelte`, `solid`, `astro`, `nuxt`, `remix`
- File patterns: `*.tsx`, `*.jsx`, `*.svelte`, `*.vue`
- Configs: `next.config.*`, `vite.config.*`, `tailwind.config.*`, `index.html`

## Required additions per phase

### DISCOVER
- Reference 2-4 UI comps or visual references before sketching (per `workflow_design_md_pipeline` memory: lock taste first)
- `/design-shotgun` if no taste anchor exists: generates multiple variants for comparison
- Read `MEMORY.md` voice samples if any prose copy will be involved

### SCAFFOLD
- **`/design-consultation` REQUIRED**: produces `DESIGN.md` covering aesthetic, typography, color, layout, spacing, motion
- `DESIGN.md` is a required artifact alongside PRD/ARCH/CLAUDE/PLAN
- For existing sites: `/plan-design-review` instead to infer the system

### PLAN
- **`/plan-design-review` REQUIRED** alongside `/plan-eng-review`
- Component-level plan, not just page-level
- Reference comps mapped explicitly to components
- Loading/empty/error states planned for every async surface

### EXECUTE
- `/frontend-design` for distinctive, production-grade UI generation
- `/design-html` for finalization (Pretext-native HTML/CSS)
- **`/frontend-build` REQUIRED for production builds and bundling**
- Build section-by-section or component-by-component against the locked DESIGN.md reference
- Component sources: shadcn + tweakcn (primitives), magicui + aceternity + 21st.dev (effects)
- Pattern research: mobbin, pageflows
- No em dashes in UI text (per `feedback_no_em_dashes`: use hyphens/colons/commas)

### VERIFY
- **`/qa` REQUIRED**: browser QA + auto-fix loop
- **`/smoke-test` REQUIRED**: Playwright smoke tests
- Test on actual browser, not just headless
- Responsive check at 3 breakpoints (mobile/tablet/desktop)
- `/devex-review` if dev-facing
- `/browse` for targeted assertions

### REVIEW
- **`/design-review` REQUIRED**: visual QA, AI slop check, hierarchy, spacing, motion
- Pattern check against locked DESIGN.md
- Component diff vs DESIGN.md tokens (colors, spacing, typography)

### SHIP
- `/frontend-build` clean (no warnings beyond known)
- Bundle size check (no regression beyond threshold)
- Type check clean (`tsc --noEmit`)

### DEPLOY
- **Lighthouse REQUIRED post-deploy** (per project memory: "run lighthouse after deploys")
- Lighthouse score >= 90 mobile per project memory
- `/canary` for console errors, perf regressions, page failures
- `/smoke-test` against production URL

### LEARN
- Component patterns captured for reuse
- Variant patterns added to DESIGN.md if new

## Tools: UI build pipeline

- `/frontend-build`: production builds, bundle analysis
- `/frontend-design`: generative component design
- `/design-html`: Pretext-native HTML/CSS finalization
- `/design-consultation`: DESIGN.md authoring
- `/design-shotgun`: variant exploration
- `/design-review`: visual QA + iterative fixes
- `/plan-design-review`: pre-implementation design plan critique
- `/qa`: browser QA loop
- `/qa-only`: browser QA report only
- `/smoke-test`: Playwright tests
- `/browse`: headless browser commands (~100ms each)
- `/setup-browser-cookies`: auth-required testing

### Component sources

Component sources: see frontend-build Stage 4.

### Performance
- Lighthouse CI in pipeline
- Core Web Vitals tracking
- Bundle size budget

## Anti-patterns to catch at REVIEW

- Em dashes in UI text (use hyphens/colons/commas)
- AI slop: overly busy gradients, generic illustrations, decorative noise
- Inconsistent spacing tokens (off-grid)
- Hierarchy violations (multiple h1, unclear primary action)
- Loading states absent
- Empty states absent
- Error states generic
- Form validation only on submit (no inline)
- Color contrast under WCAG AA
- Focus rings removed without alternative
- Click targets under 44x44 on mobile

## Per-project notes

If working in `shiny`, `phzse`, `mure`, `resona`, `luminus`, `turntables`, `boring-maths`: these are existing UI projects, read their existing design tokens / DESIGN.md before scaffolding new pages.
