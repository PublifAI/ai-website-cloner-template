<!-- AUTO-GENERATED from .claude/skills/clone-website/SKILL.md — do not edit directly.
     Run `node scripts/sync-skills.mjs` to regenerate. -->


# Clone Website

You are about to reverse-engineer and rebuild a website as pixel-perfect clones using **plain HTML + Tailwind CSS** (no frameworks).

When multiple URLs are provided, process them independently and in parallel where possible.

This is not a two-phase process (inspect then build). You are a **foreman walking the job site** — as you inspect each section of the page, you write a detailed specification to a file, then hand that file to a specialist builder agent with everything they need. Extraction and construction happen in parallel, but extraction is meticulous and produces auditable artifacts.

## Output Format: Plain HTML + Tailwind CSS

**This is NOT a Next.js/React project.** The output is standalone static HTML files.

When `--client <name>` is provided, everything goes into a client-specific folder outside the repo (configured via `CLIENTS_DIR` in `.env`). When omitted, falls back to repo-root paths for backward compatibility.

```
$CLIENTS_DIR/<name>/              # With --client (recommended)
├── research/                     # Discovery + extraction artifacts
│   ├── site-map.json
│   ├── design-system.json
│   ├── screenshots/              # Page screenshots from recon
│   ├── content/                  # One JSON per scraped page
│   └── components/               # Section spec files
├── assets/                       # Downloaded from source site
│   ├── images/
│   ├── videos/
│   └── seo/                      # Favicon, OG images
├── scripts/                      # Download scripts for this client
│   └── download-assets.mjs
└── output/                       # Generated HTML+Tailwind site
    ├── index.html
    ├── about.html
    ├── [page-name].html
    ├── [template-name].html
    ├── css/
    │   ├── input.css
    │   └── output.css
    ├── js/
    │   └── main.js
    ├── images/                   # Copied from assets, optimized
    │   └── seo/
    ├── tailwind.config.js
    └── build.sh
```

**Rules for HTML output:**
- Every page is a **fully self-contained, valid HTML5** file
- Use **semantic HTML5** elements: `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>`
- All styling via **Tailwind CSS utility classes** — no inline styles except where Tailwind can't express it
- **No JavaScript frameworks** — vanilla JS only, and only where actually needed (mobile menu toggle, carousel, form validation)
- Header and footer are **duplicated in every HTML file** (intentional — no build-time includes)
- Images use **relative paths**: `./images/filename.ext`
- Include proper `<meta>` tags per page (title, description, viewport, OG tags)
- **Responsive** using Tailwind breakpoints: `sm:`, `md:`, `lg:`, `xl:`
- Target **Lighthouse 95+** performance score
- For template pages: output one HTML file with `<!-- VARIABLE: field_name -->` comments marking where per-instance content goes

## Scope Defaults

The target is whatever page `the target URL provided by the user` resolves to. Clone exactly what's visible at that URL. Unless the user specifies otherwise, use these defaults:

- **Fidelity level:** Pixel-perfect — exact match in colors, spacing, typography, animations
- **Page limit:** Build **5–8 pages maximum** unless the user explicitly requests more. This includes unique pages + one per template group. Homepage is always first.
- **In scope:** Visual layout and styling, component structure and interactions, responsive design, mock data for demo purposes
- **Out of scope:** Real backend / database, authentication, real-time features
- **Customization:** None — pure emulation

If the user provides additional instructions (specific fidelity level, customizations, extra context), honor those over the defaults.

## Pre-Flight

1. **Browser automation is required.** Check for available browser MCP tools (Chrome MCP, Playwright MCP, Browserbase MCP, Puppeteer MCP, etc.). Use whichever is available — if multiple exist, prefer Chrome MCP. If none are detected, ask the user which browser tool they have and how to connect it. This skill cannot work without browser automation.
2. **Parse arguments from `the target URL provided by the user`:**
   - Extract URL(s) (non-flag arguments). Normalize and validate each URL.
   - Check for `--client <name>` flag. If present, all output goes into a client-specific folder. If absent, fall back to repo-root paths for backward compatibility.
3. **Resolve the clients directory:**
   - Read `.env` file in the repo root for `CLIENTS_DIR`. Default: `../clients` (parent-level, shared across all Publifai tools).
   - Resolve the path relative to the repo root to get an absolute path. Store as `$CLIENTS_DIR`.
4. **Read client.json** (if `--client` was provided):
   - Check if `$CLIENTS_DIR/<name>/client.json` exists.
   - **If it exists**, read it and use:
     - `existing_site.url` as the target URL if no URL was provided as an argument
     - `case` to understand what kind of build this is (2a = fresh from scratch, 2b = migration with improvements, 2c = same structure new design)
     - `design` fields if populated (client-approved colors/fonts override what was extracted)
     - `structure.pages` if populated (client-approved page list)
   - **If it doesn't exist and `--client` was provided**, create it with defaults (same schema as `/discover-site` — see that skill for the template).
   - **Determine which phase of the Publifai flow this run is:**
     - If `phases.B_capture.discover` has any completed sub-phases and `phases.B_capture.mirror.status` is `"pending"` → this is **Phase B2 (Mirror)** of Phase B (Capture). Set `status` = `"capturing"`, `phases.B_capture.mirror.status` = `"running"`.
     - Otherwise → this is **Phase D (Build)**. Set `status` = `"building"`, `phases.D_build.started` = today (if not already set).
   - Set `updated` = today.
   - When the clone **completes**:
     - Phase B2: set `phases.B_capture.mirror.status` = `"completed"`. The `deployed_url` field is set by the separate mirror-deploy wrapper (not this skill).
     - Phase D: set `phases.D_build.completed` = today.
5. **Set output paths** based on whether `--client` was provided:

   | Output | With `--client <name>` | Without `--client` (legacy) |
   |--------|------------------------|-----------------------------|
   | Research/specs | `$CLIENTS_DIR/<name>/research/` | `docs/research/` |
   | Screenshots | `$CLIENTS_DIR/<name>/research/screenshots/` | `docs/design-references/` |
   | Component specs | `$CLIENTS_DIR/<name>/research/components/` | `docs/research/components/` |
   | Assets (images) | `$CLIENTS_DIR/<name>/assets/images/` | `public/images/` |
   | SEO assets | `$CLIENTS_DIR/<name>/assets/seo/` | `public/images/seo/` |
   | HTML output | `$CLIENTS_DIR/<name>/output/` | `output/` |
   | Download scripts | `$CLIENTS_DIR/<name>/scripts/` | `scripts/` |
   | Audit report | `$CLIENTS_DIR/<name>/report/` | `docs/research/` |

   Use these paths consistently throughout all phases. From here on, this document uses `$RESEARCH`, `$SCREENSHOTS`, `$COMPONENTS`, `$IMAGES`, `$SEO`, `$OUTPUT`, `$SCRIPTS`, and `$REPORT` as placeholders for the resolved paths.

6. **Check for discovery output.** If `$RESEARCH/site-map.json` exists (from running `/discover-site`), read it and use it to determine which pages to clone. If `$RESEARCH/design-system.json` exists, use it for design tokens. If `$RESEARCH/content/` has files, use them for page content. This avoids re-scraping what was already discovered.
7. Create all output directories.
8. When working with multiple pages, optionally confirm whether to run them in parallel (recommended) or sequentially.

## Guiding Principles

These are the truths that separate a successful clone from a "close enough" mess. Internalize them — they should inform every decision you make.

### 1. Completeness Beats Speed

Every builder agent must receive **everything** it needs to do its job perfectly: screenshot, exact CSS values, downloaded assets with local paths, real text content, component structure. If a builder has to guess anything — a color, a font size, a padding value — you have failed at extraction. Take the extra minute to extract one more property rather than shipping an incomplete brief.

### 2. Small Tasks, Perfect Results

When an agent gets "build the entire features section," it glosses over details — it approximates spacing, guesses font sizes, and produces something "close enough" but clearly wrong. When it gets a single focused section with exact CSS values, it nails it every time.

Look at each section and judge its complexity. A simple banner with a heading and a button? One agent. A complex section with 3 different card variants, each with unique hover states and internal layouts? One agent per card variant plus one for the section wrapper. When in doubt, make it smaller.

**Complexity budget rule:** If a builder prompt exceeds ~150 lines of spec content, the section is too complex for one agent. Break it into smaller pieces.

### 3. Real Content, Real Assets

Extract the actual text, images, videos, and SVGs from the live site. This is a clone, not a mockup. Use `element.textContent`, download every `<img>` and `<video>`, extract inline `<svg>` elements. The only time you generate content is when something is clearly server-generated and unique per session.

**Layered assets matter.** A section that looks like one image is often multiple layers — a background watercolor/gradient, a foreground UI mockup PNG, an overlay icon. Inspect each container's full DOM tree and enumerate ALL `<img>` elements and background images within it, including absolutely-positioned overlays.

### 4. Foundation First

Nothing can be built until the foundation exists: `tailwind.config.js` with the target site's design tokens (colors, fonts, spacing), `css/input.css` with global styles, and downloaded global assets (fonts, favicons). This is sequential and non-negotiable. Everything after this can be parallel.

### 5. Extract How It Looks AND How It Behaves

A website is not a screenshot — it's a living thing. Elements move, change, appear, and disappear in response to scrolling, hovering, clicking, resizing, and time. If you only extract the static CSS of each element, your clone will look right in a screenshot but feel dead when someone actually uses it.

For every element, extract its **appearance** (exact computed CSS via `getComputedStyle()`) AND its **behavior** (what changes, what triggers the change, and how the transition happens).

Examples of behaviors to watch for:
- A navbar that shrinks, changes background, or gains a shadow after scrolling past a threshold
- Elements that animate into view when they enter the viewport
- Hover states that animate (the transition duration and easing matter)
- Dropdowns, modals, accordions with enter/exit animations
- Auto-playing carousels or cycling content
- **Tabbed/pill content that cycles** — buttons that switch visible content
- **Smooth scroll libraries** (Lenis, Locomotive Scroll)

### 6. Identify the Interaction Model Before Building

Before writing any builder prompt for an interactive section, determine: **Is this section driven by clicks, scrolls, hovers, time, or some combination?**

1. **Don't click first.** Scroll through the section slowly and observe if things change on their own.
2. If they do, it's scroll-driven. Extract the mechanism.
3. If nothing changes on scroll, THEN click/hover to test.
4. Document the interaction model explicitly in the component spec.

### 7. Extract Every State, Not Just the Default

Many components have multiple visual states. You must extract ALL states, not just whatever is visible on page load.

### 8. Spec Files Are the Source of Truth

Every section gets a specification file in `$COMPONENTS/` BEFORE any builder is dispatched. This file is the contract between your extraction work and the builder agent.

### 9. Output Must Be Valid HTML

Every builder agent must verify its output is valid HTML. After merging, open each page in a browser and verify visually. No broken builds.

## Phase 1: Reconnaissance

Navigate to the target URL with browser MCP.

### Check for Discovery Data (preferred path)

If `/discover-site` was run first, its outputs are your primary data source — **do not re-scrape what was already discovered.**

1. **Read `$RESEARCH/site-map.json`** — this is your page list. Use `unique_pages` + one `example_url` per `template_groups` entry. Apply the 5–8 page cap:
   - Homepage is always included and always built first
   - All unique pages from the site map (typically 4–6)
   - One representative per template group (typically 1–2)
   - If the total exceeds 8, prioritize pages present in the main navigation; ask the user which to drop
   - If `client.json` has `structure.pages` populated (client-approved list), use that instead

2. **Read `$RESEARCH/design-system.json`** — use directly for `tailwind.config.js` generation (colors, fonts, spacing, components). Do not re-extract design tokens from the browser.

3. **Read `$RESEARCH/content/*.json`** — use for page text content, headings, meta tags, image references, and template field mappings. Only visit pages in the browser for visual extraction (computed styles, interaction sweep) — text content comes from these files.

4. **Read `$REPORT/site-audit.md`** (or `.html`) if it exists — note any issues flagged (mobile problems, missing meta tags, broken links) as a QA checklist for Phase 5.

5. **Use existing assets** — images already downloaded to `$IMAGES/` and `$SEO/` during discovery. Do not re-download them (see Phase 2 step 4).

6. Proceed to Phase 2 with discovery data. You still need the browser for visual inspection (computed styles, interaction sweep, screenshots) but you already have the site structure, design tokens, content, and assets.

If no discovery data exists, proceed with single-page extraction below. The browser becomes your only data source — extract everything from scratch, but still respect the 5–8 page limit.

### Screenshots
- Take **full-page screenshots** at desktop (1440px) and mobile (390px) viewports
- Save to `$SCREENSHOTS/` with descriptive names

### Global Extraction
Extract from the page:

**Fonts** — Inspect `<link>` tags for Google Fonts or self-hosted fonts. Check computed `font-family` on key elements. Document every family, weight, and style actually used.

**Colors** — Extract the site's color palette from computed styles across the page.

**Favicons & Meta** — Download favicons, apple-touch-icons, OG images to `$OUTPUT/images/seo/`.

**Global UI patterns** — Identify any site-wide CSS or JS: custom scrollbar hiding, scroll-snap, global keyframe animations, smooth scroll libraries.

### Mandatory Interaction Sweep

**Scroll sweep:** Scroll the page slowly from top to bottom. At each section, pause and observe.

**Click sweep:** Click every element that looks interactive.

**Hover sweep:** Hover over every element that might have hover states.

**Responsive sweep:** Test at 1440px, 768px, 390px.

Save all findings to `$RESEARCH/BEHAVIORS.md`.

### Page Topology
Map out every distinct section of the page from top to bottom. Save as `$RESEARCH/PAGE_TOPOLOGY.md`.

## Phase 2: Foundation Build

This is sequential. Do it yourself (not delegated to an agent):

### 1. Create tailwind.config.js

Generate `$OUTPUT/tailwind.config.js` with design tokens from the target site:

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./**/*.html'],
  theme: {
    extend: {
      colors: {
        // Extracted from target site
        primary: '#313131',
        accent: '#007cba',
        // ... all colors from design-system.json or extraction
      },
      fontFamily: {
        heading: ['"Playfair Display"', 'serif'],
        body: ['"Open Sans"', 'sans-serif'],
      },
      maxWidth: {
        container: '1200px',
      },
      // spacing, shadows, etc.
    },
  },
  plugins: [],
}
```

If `$RESEARCH/design-system.json` exists, use its values directly.

### 2. Create css/input.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Google Fonts import */
@import url('https://fonts.googleapis.com/css2?family=...');

/* Global styles that can't be expressed as Tailwind utilities */
@layer base {
  html { font-family: 'Open Sans', sans-serif; }
  /* ... */
}

@layer components {
  /* Reusable component patterns */
  .btn-primary { @apply bg-primary text-white px-5 py-2 text-sm font-semibold uppercase tracking-wide transition-colors hover:bg-accent; }
  /* ... */
}

/* Keyframe animations */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
```

### 3. Create build.sh

```bash
#!/bin/bash
npx tailwindcss -i css/input.css -o css/output.css --minify
echo "Build complete: css/output.css"
```

### 4. Populate output assets

**If discovery data exists** (preferred): Copy assets from `$IMAGES/` → `$OUTPUT/images/` and `$SEO/` → `$OUTPUT/images/seo/`. These were already downloaded during `/discover-site`. Only download net-new assets found during visual inspection that weren't captured in discovery.

**If no discovery data exists**: Write and run `$SCRIPTS/download-assets.mjs` to download all images, videos, fonts, and favicons to `$OUTPUT/images/`.

### 5. Create js/main.js

Scaffold the vanilla JS file with only the interactivity needed:

```javascript
// Mobile menu toggle
document.addEventListener('DOMContentLoaded', () => {
  const menuButton = document.getElementById('mobile-menu-button');
  const mobileMenu = document.getElementById('mobile-menu');
  if (menuButton && mobileMenu) {
    menuButton.addEventListener('click', () => {
      mobileMenu.classList.toggle('hidden');
    });
  }

  // Carousel (if needed)
  // Form validation (if needed)
});
```

## Phase 3: Section Specification & Dispatch

### Build Order

**Homepage is always built first.** It establishes the master header, footer, and global patterns that all other pages reuse. Once the homepage is complete and visually verified, build remaining pages in parallel — they copy the homepage's header/footer and only need their unique body sections built.

For multi-page clones:
1. **Homepage** — full extraction + build of every section (header, hero, all body sections, footer)
2. **Other unique pages** — copy header/footer from homepage, extract + build only the body sections unique to each page. Can run in parallel.
3. **Template pages** — one representative per template group. Copy header/footer, build the template body with `<!-- VARIABLE -->` markers.

This is the core loop. For each section in your page topology, you do THREE things: **extract**, **write the spec file**, then **dispatch builders**.

### Step 1: Extract

Same extraction process as before — use browser MCP to extract computed styles, content, assets, and behavior for each section. Use the `getComputedStyle()` extraction script.

### Step 2: Write the Section Spec File

Create spec files in `$COMPONENTS/` with the same template as before, but change the target file path and implementation notes:

```markdown
# <SectionName> Specification

## Overview
- **Target output:** Section HTML for `$OUTPUT/index.html` (or whichever page)
- **Screenshot:** `$SCREENSHOTS/<screenshot-name>.png`
- **Interaction model:** <static | click-driven | scroll-driven | time-driven>

## DOM Structure
<Describe the HTML element hierarchy>

## Computed Styles (exact values — map to Tailwind classes)
### Container
- display: flex → `flex`
- padding: 50px 0 → `py-[50px]`
- maxWidth: 1200px → `max-w-container`
- (map every property to its Tailwind equivalent)

## Implementation Notes
- Use semantic HTML5 elements
- All styling via Tailwind utility classes
- For interactions: add vanilla JS in js/main.js
- Images use relative paths: ./images/filename.ext
```

### Step 3: Dispatch Builders

Dispatch builder agent(s) in worktree(s). Each builder produces an **HTML fragment** (the section's HTML with Tailwind classes) that will be assembled into the final page.

**What every builder agent receives:**
- The full spec file contents inline
- Path to the section screenshot
- The output file path (e.g., a temporary file in the worktree)
- Instruction to use **only** Tailwind CSS classes and semantic HTML
- No React, no JSX, no components — plain HTML
- For interactivity: write vanilla JS functions that the main js/main.js will call
- The `tailwind.config.js` design token names to use (e.g., `text-primary`, `bg-accent`)

**Builder output format:** Each builder writes its section as a standalone HTML fragment:

```html
<!-- Section: HeroSlider -->
<section class="relative w-full overflow-hidden" id="hero-slider">
  <div class="relative w-full">
    <!-- slides -->
  </div>
</section>
<!-- End: HeroSlider -->
```

### Step 4: Merge

As builder agents complete:
- Copy their HTML fragments from worktrees
- After all sections for a page are done, assemble them (Phase 4)

## Phase 4: Page Assembly

After all sections are built, assemble each page:

### For each page (index.html, about.html, etc.):

1. Create the HTML boilerplate:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page Title - Site Name</title>
  <meta name="description" content="...">
  <!-- OG tags -->
  <meta property="og:title" content="...">
  <meta property="og:description" content="...">
  <meta property="og:image" content="./images/seo/og-image.jpg">
  <!-- Favicon -->
  <link rel="icon" href="./images/seo/favicon.ico">
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=..." rel="stylesheet">
  <!-- Tailwind output -->
  <link rel="stylesheet" href="./css/output.css">
</head>
<body class="min-h-screen font-body text-foreground bg-background">
```

2. Insert all section HTML fragments in order (header, hero, content sections, footer)

3. Close with JS and closing tags:

```html
  <!-- Vanilla JS -->
  <script src="./js/main.js"></script>
</body>
</html>
```

4. **Duplicate header and footer** into every page file. This is intentional — each HTML file must be fully self-contained.

### For template pages:

Add comments marking variable content:

```html
<!-- TEMPLATE: Artist Profile -->
<!-- VARIABLE: artist_name --><h1 class="text-3xl font-heading font-bold">Jagannath Paul</h1><!-- /VARIABLE -->
<!-- VARIABLE: artist_image --><img src="./images/products/jagannath-paul.jpg" alt="Jagannath Paul"><!-- /VARIABLE -->
<!-- FIXED: sidebar layout (same on all artist pages) -->
```

## Phase 5: Visual QA Diff

After assembly:

1. Build the CSS: `cd $OUTPUT && bash build.sh`
2. **Check the audit report** — if `$REPORT/site-audit.md` (or `.html`) exists from `/discover-site`, review its findings. Use flagged issues (missing meta tags, mobile layout problems, broken links, slow-loading assets) as a QA checklist. The clone should fix these where possible, not replicate them.
3. Open each HTML file in the browser via browser MCP
4. Compare section by section with the original at desktop (1440px) and mobile (390px)
5. Fix any discrepancies directly in the HTML files
6. Test all interactive behaviors
7. Verify Lighthouse score target (95+)

## Pre-Dispatch Checklist

Before dispatching ANY builder agent:

- [ ] Spec file written to `$COMPONENTS/<name>.spec.md` with ALL sections filled
- [ ] Every CSS value mapped to a Tailwind class (or documented as a custom value)
- [ ] Interaction model is identified (static / click / scroll / time)
- [ ] For stateful components: every state's content and styles are captured
- [ ] All images in the section are identified and downloaded
- [ ] Responsive behavior is documented for desktop and mobile
- [ ] Text content is verbatim from the site
- [ ] The builder prompt is under ~150 lines; if over, split

## What NOT to Do

- **Don't use React, Next.js, JSX, or any framework** — plain HTML + Tailwind only
- **Don't use npm/Node.js in the output** — Tailwind standalone CLI only for CSS compilation
- **Don't create a shared layout/template system** — duplicate header/footer in every page (intentional for our pipeline)
- **Don't add JavaScript unless actually needed** — most sections are pure HTML+CSS
- **Don't use `@apply` excessively** — prefer inline utility classes, use `@apply` only for truly reusable patterns (buttons, badges)
- **Don't approximate CSS values** — extract exact values and map to Tailwind
- **Don't skip asset extraction** — without real images, the clone looks fake
- **Don't bundle unrelated sections** — one agent per section
- **Don't skip responsive extraction** — test at 1440, 768, and 390

## Completion

### Update client.json

If `--client` was provided, update `$CLIENTS_DIR/<name>/client.json` (read-modify-write, merge don't replace):

**On success:**
- Set `steps.build.completed` = today
- Set `structure.pages` = list of page names built (e.g., `["Home", "About", "Contact", "Artist Profile", "Product Page"]`)
- Set `updated` = today

**On failure** (build breaks, critical pages can't be cloned, unrecoverable errors):
- Set `status` = `"build_failed"`
- Set `steps.build.failed` = today
- Set `steps.build.error` = brief description of what went wrong
- Set `updated` = today
- Do NOT set `steps.build.completed`

### Report

When done, report:
- Total pages built (HTML files)
- Total sections built
- Total spec files written
- Total assets downloaded
- Build status (`bash build.sh` result)
- Visual QA results
- Any known gaps or limitations
- File listing of the `$OUTPUT/` directory
