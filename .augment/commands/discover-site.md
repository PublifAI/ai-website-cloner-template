---
description: "Discover a website's full structure via sitemap/navigation crawling, extract its design system, and pull content from re"
argument-hint: "<url>"
---
<!-- AUTO-GENERATED from .claude/skills/discover-site/SKILL.md — do not edit directly.
     Run `node scripts/sync-skills.mjs` to regenerate. -->


# Discover Site

You are about to discover and document the full structure of a website.

This skill produces FOUR outputs that feed into the site-building process:
1. **Site map** — every page categorized as unique or template instance
2. **Design system** — colors, fonts, spacing, component patterns
3. **Site audit report** — client-facing summary of findings and recommendations
4. **Content extraction** — text, images, and structure from representative pages

## Pre-Flight

1. **Browser automation is required.** Check for available browser MCP tools (Chrome MCP, Playwright MCP, Browserbase MCP, Puppeteer MCP, etc.). Use whichever is available — if multiple exist, prefer Chrome MCP. If none are detected, ask the user which browser tool they have and how to connect it.
2. **Parse arguments from `$ARGUMENTS`:**
   - Extract the base URL (first non-flag argument). Normalize it (add `https://` if missing, strip trailing paths to get the domain root).
   - Check for `--client <name>` flag. If present, all output goes into a client-specific folder. If absent, fall back to repo-root paths for backward compatibility.
   - Check for `--phases <list>` flag. If present, parse the comma-separated list of phase numbers (e.g., `--phases 1,2` or `--phases 3,4`). Only run the listed phases. If absent, run all 4 phases.
     - Valid phase numbers: `1` (Site Map), `2` (Design System), `3` (Site Audit Report), `4` (Content Extraction).
     - **Phase dependencies:** Phase 3 (audit report) reads outputs from Phases 1 and 2. If running Phase 3 without 1 or 2, check that the required files (`site-map.json`, `design-system.json`) already exist from a previous run. If missing, warn the user and skip Phase 3.
     - Phase 4 (content extraction) reads the site map from Phase 1. If running Phase 4 without 1, check that `site-map.json` exists. If missing, warn the user and skip Phase 4.
   - Check for `--force` flag. If present, re-run phases even if client.json shows them as completed.
3. **Resolve the clients directory:**
   - Read `.env` file in the repo root for `CLIENTS_DIR`. Default: `../clients` (parent-level, shared across all Publifai tools).
   - Resolve the path relative to the repo root to get an absolute path. Store as `$CLIENTS_DIR`.
   - Example: if repo is at `/Users/me/repos/publifai/ai-website-cloner-template` and `CLIENTS_DIR=../clients`, then `$CLIENTS_DIR` = `/Users/me/repos/publifai/clients`.
4. **Read client.json** (if `--client` was provided):
   - Check if `$CLIENTS_DIR/<name>/client.json` exists.
   - **If it exists**, read it and use:
     - `existing_site.url` as the target URL if no URL was provided as an argument
     - `business.name` as the business name for the audit report (instead of guessing from the site)
     - `case` to understand the client scenario (1, 2a, 2b, 2c)
     - `phases.B_capture.discover` to check which sub-phases are already completed — skip completed sub-phases unless `--force` is passed
     - `design` fields if already populated (e.g., client has already approved colors)
   - **If it doesn't exist**, create it with defaults:
     ```json
     {
       "name": "<title-cased domain>",
       "slug": "<domain without TLD>",
       "owner": { "name": null, "phone": null, "email": null },
       "business": { "type": null, "description": null, "location": null, "services": [], "hours": null, "socials": {} },
       "case": "2b",
       "status": "capturing",
       "phases": {
         "A_onboard": { "started": "<today>", "completed": "<today>" },
         "B_capture": {
           "started": "<today>",
           "completed": null,
           "discover": {
             "site_map": { "status": "pending", "completed": null },
             "design_system": { "status": "pending", "completed": null },
             "audit_report": { "status": "pending", "completed": null, "report_shared": null, "report_deployed_url": null },
             "content_extraction": { "status": "pending", "completed": null }
           },
           "mirror": { "status": "pending", "deployed_url": null }
         },
         "C_define": { "started": null, "structure_approved": null, "design_approved": null },
         "D_build": { "started": null, "completed": null },
         "E_preview": { "started": null, "iterations": 0 },
         "F_launch": { "launched": null }
       },
       "domains": { "subdomain": "<slug>.publif.ai", "custom": "<domain>", "custom_active": false },
       "existing_site": { "url": "https://<domain>", "scraped": false, "pages_discovered": null, "pages_scraped": null },
       "design": { "colors": {}, "fonts": {}, "vibe": null },
       "structure": { "pages": [] },
       "notes": [],
       "created": "<today>",
       "updated": "<today>"
     }
     ```
   - Verify the site is accessible (using the URL from client.json or the argument).
5. **Set output paths** based on whether `--client` was provided:

   | Output | With `--client <name>` | Without `--client` (legacy) |
   |--------|------------------------|-----------------------------|
   | Site map | `$CLIENTS_DIR/<name>/research/site-map.json` | `docs/research/site-map.json` |
   | Design system | `$CLIENTS_DIR/<name>/research/design-system.json` | `docs/research/design-system.json` |
   | Content files | `$CLIENTS_DIR/<name>/research/content/` | `docs/research/content/` |
   | Screenshots | `$CLIENTS_DIR/<name>/research/screenshots/` | `docs/design-references/` |
   | Images | `$CLIENTS_DIR/<name>/assets/images/` | `public/images/` |
   | SEO assets | `$CLIENTS_DIR/<name>/assets/seo/` | `public/images/seo/` |
   | Download script | `$CLIENTS_DIR/<name>/scripts/download-assets.mjs` | `scripts/download-assets.mjs` |
   | Audit report (HTML) | `$CLIENTS_DIR/<name>/report/site-audit.html` | `docs/research/site-audit.html` |

   Use these paths consistently throughout all phases. From here on, this document uses `$RESEARCH`, `$SCREENSHOTS`, `$IMAGES`, `$SEO`, `$SCRIPTS`, and `$REPORT` as placeholders for the resolved paths.

6. Create all output directories.

### Updating client.json at Phase Boundaries

**When `--client` is provided**, update `$CLIENTS_DIR/<name>/client.json` at each phase boundary. Use a read-modify-write pattern — never overwrite fields that aren't being updated.

**When a phase starts:** Set its status to `"running"`.

**When a phase completes,** update the following fields (merge, don't replace):

**Note:** All discovery sub-phases live under `phases.B_capture.discover.*` in the new schema. This skill executes Phase B1 (Discover) of Phase B (Capture) in the site-building process.

| Phase completes | Fields to set |
|-----------------|---------------|
| Phase 1 (Site Map) | `phases.B_capture.discover.site_map.status` = `"completed"`, `.completed` = today, `existing_site.pages_discovered` = total count, `existing_site.pages_scraped` = pages_to_scrape, `existing_site.scraped` = `true`, `status` = `"capturing"` (if not already set), `phases.B_capture.started` = today (if not already set) |
| Phase 2 (Design System) | `phases.B_capture.discover.design_system.status` = `"completed"`, `.completed` = today, `design.colors` = `{primary, secondary, accent}` from design-system.json, `design.fonts` = `{heading, body}` from design-system.json |
| Phase 3 (Audit Report) | `phases.B_capture.discover.audit_report.status` = `"completed"`, `.completed` = today. After deploy step (see below), also set `.report_deployed_url` = `https://<slug>.pages.dev/audit/` |
| Phase 4 (Content Extraction) | `phases.B_capture.discover.content_extraction.status` = `"completed"`, `.completed` = today |

**When ALL requested phases are done:**
- Set `updated` = today
- Discover is complete only when all 4 sub-phases are `"completed"`. Phase B itself (`phases.B_capture.completed`) is set by `/clone-website` + mirror deploy, not here.

**When a phase is skipped** (via `--phases` flag): leave its status as-is.

**Always** set `updated` = today on any write.

## Phase 1: Site Map Discovery (Output 1)

**Skip this phase if `--phases` was provided and `1` is not in the list.**

Goal: Discover ALL pages on the site and categorize them.

### Step 1: Try Sitemap

1. Fetch `<base-url>/sitemap.xml` via WebFetch
2. If not found, try `<base-url>/sitemap_index.xml`
3. If a sitemap index is found, fetch each child sitemap listed in it
4. Parse all `<loc>` URLs from the sitemap(s)
5. If no sitemap exists, fall back to Step 2

### Step 2: Navigation Crawling (fallback or supplement)

If no sitemap, or if the sitemap seems incomplete:

1. Navigate to the homepage with browser MCP
2. Extract ALL internal links from:
   - Header navigation (including dropdowns and mega menus)
   - Footer links
   - Sidebar menus
   - Body content links
3. For each discovered page, visit it and extract any NEW internal links not yet seen
4. **Depth limit: 2 levels** from homepage (homepage → linked page → linked from that page)
5. **Page limit: never discover more than 200 URLs** — stop crawling when you hit this
6. Deduplicate URLs (strip query params, anchors, trailing slashes for comparison)

### Step 3: Categorize Pages

For each discovered URL, determine if it's a **unique page** or a **template instance**:

**Signals that pages share a template:**
- URL path pattern: `/artists/john-doe`, `/artists/jane-smith` → same template
- Similar URL structure: `/blog/post-slug-1`, `/blog/post-slug-2` → same template
- Shared parent path segment with many siblings
- WooCommerce/WordPress patterns: `/product/*`, `/product-category/*`
- Pagination: `?page=2`, `/page/2/` — skip these entirely

**Signals of a unique page:**
- Top-level path: `/about`, `/contact`, `/services`
- Present in main navigation as a direct link
- No URL siblings with the same pattern

**Categorization algorithm:**
1. Group URLs by their path pattern (replace the last path segment with `*`)
2. If a group has 3+ URLs → it's a template group
3. If a group has 1-2 URLs → they're unique pages
4. Name each template group based on its path pattern and page content

### Step 4: Output Site Map

Save to `$RESEARCH/site-map.json`:

```json
{
  "base_url": "https://example.com",
  "discovered_at": "2026-04-04T12:00:00Z",
  "discovery_method": "sitemap" | "navigation_crawl" | "both",
  "unique_pages": [
    {
      "url": "/",
      "label": "Home",
      "found_in": "navigation"
    },
    {
      "url": "/about-us/",
      "label": "About Us",
      "found_in": "navigation"
    }
  ],
  "template_groups": [
    {
      "template_name": "Product Page",
      "url_pattern": "/product/*",
      "example_url": "/product/jagannath-paul/",
      "total_count": 47,
      "sample_urls": [
        "/product/jagannath-paul/",
        "/product/somenath-maity-2/",
        "/product/biswajit-mondal-3/"
      ]
    }
  ],
  "skipped_urls": [
    {
      "url": "/my-account/",
      "reason": "authentication_required"
    }
  ],
  "summary": {
    "total_pages_discovered": 64,
    "unique_pages": 6,
    "template_groups": 2,
    "pages_to_scrape": 8
  }
}
```

**Print a summary table** to the user after saving, showing unique pages and template groups with counts. Ask the user to confirm before proceeding to Phase 2. They may want to adjust categorization or skip certain pages.

## Phase 2: Design System Extraction (Output 2)

**Skip this phase if `--phases` was provided and `2` is not in the list.**

Goal: Extract the visual design language from 2-3 key pages.

### Pages to Inspect

- The homepage (always)
- 1-2 other pages with distinct layouts (e.g., a content page and a listing/gallery page)
- Do NOT inspect every page — the design system should be derivable from a few pages

### What to Extract

Use browser MCP to navigate to each page and run JavaScript extraction.

**Colors** — Use a **multi-layered approach** to get the real brand palette, not CMS defaults:

1. **Fetch and parse the theme stylesheet.** Find the site's theme/custom CSS file URL (look for `<link rel="stylesheet">` pointing to the theme directory — e.g., `/wp-content/themes/*/style.css`, or the main CSS bundle for non-WordPress sites). Fetch it via WebFetch and extract all color values (hex, rgb, rgba, hsl). This gives you the *intentionally chosen* colors, not framework defaults.

2. **Run frequency-based color sampling via JavaScript.** Execute a script that iterates over all visible elements on the page, calls `getComputedStyle()` for `color`, `backgroundColor`, `borderColor`, and tallies each unique color value with a usage count. Rank by frequency. The top 10-15 most-used colors are the real palette. Ignore colors used fewer than 3 times (likely one-off overrides).

3. **Filter out known CMS/framework defaults.** Discard colors that are standard WordPress, WooCommerce, Bootstrap, or browser defaults:
   - WordPress admin colors: `#007cba`, `#006ba1`, `#005a87` (these are `--wp-admin-theme-color` variants)
   - WordPress block editor palette: `#7a00df`, `#cf2e2e`, `#ff6900`, `#fcb900`, `#7bdcb5`, `#00d084`, `#8ed1fc`, `#0693e3`, `#abb8c3`, `#313131` (only if it appears ONLY in `.has-*-color` classes and not in the theme CSS)
   - WordPress block gradients (vivid-cyan-blue, luminous-vivid-orange, etc.)
   - Default browser colors: `rgb(0, 0, 0)`, `rgb(255, 255, 255)` (keep these only if theme CSS explicitly sets them)
   - Bootstrap defaults: `#0d6efd`, `#6c757d`, `#198754`, `#dc3545`, `#ffc107`, `#0dcaf0`

4. **Sample specific semantic elements.** After the frequency scan, also specifically extract colors from:
   - The `<header>` / `<nav>` background and text
   - The `<footer>` background and text
   - Primary CTA buttons (the first prominent `<a>` or `<button>` with a background color)
   - Link colors (find an `<a>` in body text and get its computed color)
   - Hero/banner section background
   - Card or product listing backgrounds and borders

5. **Cross-reference.** Compare the theme CSS colors with the frequency-sampled colors. Colors that appear in BOTH the theme CSS AND the rendered page with high frequency are the true brand colors. Colors only in CMS defaults should be excluded.

6. **Classify.** From the validated colors, determine:
   - **Primary** — the dominant brand color (most prominent in header, buttons, accents)
   - **Secondary** — supporting brand color
   - **Accent** — highlight/CTA color
   - **Background/foreground/muted/border** — structural colors

   Store both the classified palette AND the raw frequency data so the cloner has full context.

**Typography** — Extract from computed styles:
- Font families (heading font, body font, any special fonts)
- Font sizes for h1, h2, h3, h4, h5, h6, body, small, caption
- Font weights used
- Line heights
- Letter spacing values
- Text transforms (uppercase headings, etc.)

**Spacing** — Identify the spacing scale:
- Section padding (top/bottom)
- Container max-width and padding
- Card padding
- Gap between grid items
- Margin patterns

**Layout** — Extract structural patterns:
- Page max-width
- Grid column counts at different breakpoints
- Sidebar widths (if any)
- Header height
- Footer structure

**Components** — Document the patterns for:
- Buttons (primary, secondary, outline — padding, border-radius, font)
- Cards (shadow, border, radius, padding)
- Navigation (desktop + mobile patterns)
- Footer (columns, background, text style)
- Forms (input styling, labels)
- Links (color, decoration, hover state)

**Decorative** — Note:
- Border radius values used
- Box shadow patterns
- Gradient usage
- Opacity patterns
- Transition/animation patterns

### Take Screenshots

- Homepage at 1440px, 768px, 390px
- 1-2 other pages at 1440px
- Save to `$SCREENSHOTS/`

### Download Global Assets

1. Find and download all images referenced on scraped pages to `$IMAGES/`
2. **Download the site's real logo to `$IMAGES/logo.<ext>`** — locate the logo by inspecting the header: look for an `<img>` inside a `.logo`, `#logo`, `header .navbar-brand`, `.site-logo`, or similar container, or the first `<img>` inside `<header>` whose `src`/`alt` contains "logo". Download the actual file from the live site (preserving its original extension: `.png`, `.svg`, `.jpg`, or `.webp`) and save it as `$IMAGES/logo.<ext>`. Also set `assets.logo` in `design-system.json` to this relative path. **Never generate, draw, or synthesize a logo** — if no logo image can be found on the site, leave `assets.logo` as `null` and do not create a placeholder file.
3. Download favicon, apple-touch-icon, OG images to `$SEO/`
4. Note any external fonts (Google Fonts URLs, self-hosted font files)

Write and run a `$SCRIPTS/download-assets.mjs` script for batch downloading (4 concurrent).

### Output Design System

Save to `$RESEARCH/design-system.json`:

```json
{
  "colors": {
    "primary": "#313131",
    "secondary": "#eeeeee",
    "accent": "#007cba",
    "background": "#ffffff",
    "foreground": "#333333",
    "muted": "#666666",
    "border": "#dddddd",
    "footer_bg": "#313131",
    "footer_text": "#999999",
    "link": "#007cba",
    "link_hover": "#005a8c",
    "button_bg": "#313131",
    "button_text": "#ffffff",
    "button_hover_bg": "#007cba"
  },
  "typography": {
    "heading_font": "Playfair Display, serif",
    "body_font": "Open Sans, sans-serif",
    "google_fonts_url": "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Open+Sans:wght@300;400;600;700&display=swap",
    "sizes": {
      "h1": { "size": "42px", "weight": "700", "line_height": "1.2" },
      "h2": { "size": "32px", "weight": "700", "line_height": "1.3" },
      "h3": { "size": "24px", "weight": "700", "line_height": "1.4" },
      "h4": { "size": "20px", "weight": "600", "line_height": "1.4" },
      "body": { "size": "14px", "weight": "400", "line_height": "24px" },
      "small": { "size": "13px", "weight": "400", "line_height": "20px" },
      "nav": { "size": "14px", "weight": "600", "line_height": "1", "transform": "uppercase", "letter_spacing": "1px" }
    }
  },
  "spacing": {
    "section_padding_y": "50px",
    "container_max_width": "1200px",
    "container_padding_x": "20px",
    "card_padding": "10px",
    "grid_gap": "20px",
    "heading_margin_bottom": "20px"
  },
  "layout": {
    "max_width": "1200px",
    "header_height": "90px",
    "footer_columns": 4,
    "grid_columns_desktop": 4,
    "grid_columns_tablet": 2,
    "grid_columns_mobile": 1
  },
  "components": {
    "button": {
      "padding": "8px 18px",
      "border_radius": "0",
      "font_size": "13px",
      "font_weight": "600",
      "text_transform": "uppercase",
      "letter_spacing": "0.5px"
    },
    "card": {
      "border": "1px solid #eeeeee",
      "border_radius": "0",
      "box_shadow": "none",
      "padding": "10px"
    },
    "input": {
      "border": "1px solid #dddddd",
      "border_radius": "4px",
      "padding": "10px 16px",
      "font_size": "14px"
    }
  },
  "decorative": {
    "border_radius": {
      "none": "0",
      "small": "4px",
      "full": "9999px"
    },
    "shadows": {
      "dropdown": "0 5px 15px rgba(0,0,0,0.1)"
    },
    "transitions": {
      "default": "0.3s ease"
    }
  },
  "assets": {
    "logo": "public/images/logo.png",
    "favicon": "public/images/seo/favicon.ico",
    "images_downloaded": 16
  }
}
```

## Phase 3: Site Audit Report (Output 3)

**Skip this phase if `--phases` was provided and `3` is not in the list.**
**Requires:** `$RESEARCH/site-map.json` (Phase 1) and `$RESEARCH/design-system.json` (Phase 2). If either file is missing, warn the user and skip this phase.

Goal: Generate a polished, client-facing audit report as a self-contained, styled HTML file. Written for a non-technical small business owner — no jargon, friendly professional tone.

### Determine the Business Name

Look for the business name in this order:
1. The site's `<title>` tag or OG title (strip suffixes like "| Home", "— Official Site")
2. The logo alt text
3. The domain name, title-cased (e.g., "galleryoneindia.com" → "Gallery One India")

Use this business name throughout the report.

### Gather Data

Read the outputs from Phase 1 and Phase 2:
- `$RESEARCH/site-map.json` — page counts, unique pages, template groups
- `$RESEARCH/design-system.json` — colors, fonts, layout, components
- Screenshots from `$SCREENSHOTS/` — embed them in the report

#### Locate Client Logo and Homepage Screenshot

1. **Client logo** — Find an **existing** logo file that was downloaded during Phase 2. Check in order:
   - `$IMAGES/logo.png`
   - `$IMAGES/logo.jpg`, `$IMAGES/logo.svg`, `$IMAGES/logo.webp`
   - `$SEO/logo.png`
   - The `assets.logo` path from `design-system.json`

   If found, read the file and base64-encode it for embedding in the report header.

   **DO NOT create, generate, synthesize, or draw a logo under any circumstances.** Never write a logo file, never use an SVG placeholder, never fabricate one from the business name. If no logo file exists in the locations above, omit the logo from the report entirely — the header should just show the business name and domain. Setting the logo is Phase 2's job (via `Explore`/asset download), not Phase 3's.

2. **Homepage screenshot** — You MUST embed an actual screenshot of the client's live homepage. Look for it in `$SCREENSHOTS/` in this order:
   - `$SCREENSHOTS/homepage-desktop.png`
   - `$SCREENSHOTS/homepage-mobile.png`
   - Any file in `$SCREENSHOTS/` matching `*homepage*` or `*home*`

   If no homepage screenshot exists in `$SCREENSHOTS/`, **capture one now** using browser MCP against the live site (1440px desktop viewport, full-page) and save it to `$SCREENSHOTS/homepage-desktop.png` before embedding. **Never fall back to a repo asset, README image, placeholder, or any file outside `$SCREENSHOTS/`.** The embedded image must be a real rendering of the client's actual homepage.

3. **Client domain** — Extract from `base_url` in `site-map.json` (e.g., `www.galleryoneindia.com`). Display prominently in the report header alongside the business name.

#### Select Audit Pages

Pick **2-3 pages** to audit in depth. These pages get individual PageSpeed scores, screenshots, and SEO checks:

1. **Homepage** (always) — the front door
2. **One interior content page** — pick the most important non-homepage page (e.g., About, Services, or a key product/listing page). Prefer a page with distinct layout from the homepage.
3. **One template instance** (optional, if the site has template groups) — pick the `example_url` from the most important template group (e.g., a product page, artist profile, or blog post)

Store the selected page URLs as `$AUDIT_PAGES` (list of 2-3 full URLs). Use these consistently for PageSpeed, screenshots, and SEO checks below.

#### Google PageSpeed Insights

Fetch real performance data from the Google PageSpeed Insights API **for each page in `$AUDIT_PAGES`**.

Read `PSI_API_KEY` from the repo's `.env` file (required — the unauthenticated endpoint's shared quota is almost always exhausted). If `PSI_API_KEY` is missing, stop and tell the user to set it in `.env` (see `.env.example`).

```
https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=<PAGE_URL>&strategy=<mobile|desktop>&category=performance&category=accessibility&category=seo&key=$PSI_API_KEY
```

For each page, call the API **twice** (mobile + desktop). That's 4-6 API calls total. Run them in parallel where possible (use concurrent WebFetch calls).

Extract from each response:
- **Performance score** (0-100): `lighthouseResult.categories.performance.score * 100`
- **Accessibility score** (0-100): `lighthouseResult.categories.accessibility.score * 100`
- **SEO score** (0-100): `lighthouseResult.categories.seo.score * 100`
- **Core Web Vitals:**
  - LCP (Largest Contentful Paint): `lighthouseResult.audits['largest-contentful-paint'].displayValue`
  - CLS (Cumulative Layout Shift): `lighthouseResult.audits['cumulative-layout-shift'].displayValue`
  - TBT (Total Blocking Time): `lighthouseResult.audits['total-blocking-time'].displayValue`
  - Speed Index: `lighthouseResult.audits['speed-index'].displayValue`
- **Key opportunities** (top 3 by estimated savings): `lighthouseResult.audits` — look for audits with `details.overallSavingsMs > 0`, sorted by savings descending. Extract the audit title and savings value.

If an API call fails (timeout, site unreachable, 500 error), note "PageSpeed data unavailable for [page]" and fall back to qualitative observations for that page.

Save the raw PageSpeed responses to `$RESEARCH/pagespeed/` — one file per page+strategy:
- `pagespeed-homepage-desktop.json`, `pagespeed-homepage-mobile.json`
- `pagespeed-[slug]-desktop.json`, `pagespeed-[slug]-mobile.json`

#### Screenshots

Take screenshots of **each page in `$AUDIT_PAGES`** using browser MCP. For each page:

- **Desktop** at 1440px viewport width (full-page screenshot if possible, otherwise above-the-fold)
- **Mobile** at 390px viewport width

Save to `$SCREENSHOTS/` with descriptive names:
- `homepage-desktop.png`, `homepage-mobile.png`
- `[slug]-desktop.png`, `[slug]-mobile.png`

These screenshots will be base64-embedded in the HTML report, so each audited page gets its own visual in the report.

#### Numeric Findings Extraction (from Lighthouse)

**Every finding in this report must be numeric, not adjectival.** For each page in `$AUDIT_PAGES`, open the saved PageSpeed JSON and extract the concrete numbers below. Store them in memory as you go — they drive the Hero Stat Strip and all "Findings" bullets.

From `lighthouseResult.audits` pull (mobile response preferred, fall back to desktop):
- **`total-byte-weight`** — `numericValue` in bytes → convert to MB. This is today's page payload.
- **`uses-optimized-images`** — `details.overallSavingsBytes` → MB saved if images were compressed properly.
- **`uses-responsive-images`** — `details.overallSavingsBytes` → additional MB saved by right-sizing.
- **`modern-image-formats`** — `details.overallSavingsBytes` → MB saved by WebP/AVIF.
- **`offscreen-images`** — `details.overallSavingsBytes` → MB saved by lazy-loading.
- **`unused-css-rules`** — `details.overallSavingsBytes` → KB saved.
- **`unused-javascript`** — `details.overallSavingsBytes` → KB saved.
- **`render-blocking-resources`** — `details.overallSavingsMs` → ms saved.
- **`tap-targets`** — `score` (1 = pass, <1 = fail) + failing element count from `details.items.length`.
- **`image-alt`** — `score` and failing element count.
- **`meta-description`** / **`document-title`** — pass/fail.
- **`is-crawlable`** / **`robots-txt`** — pass/fail.

Compute derived metrics:
- **Homepage payload today (MB)** = `total-byte-weight.numericValue / 1024 / 1024`.
- **Target payload (MB)** = today − sum of image savings (optimized + responsive + modern formats + offscreen).
- **Estimated time saved on mobile (seconds)** = sum of `overallSavingsMs` across top 3 opportunities / 1000.
- **Implied CLS conversion drag (%)** = `max(0, (CLS − 0.1) / 0.1) × 7`. (Rule of thumb: every 0.1 of CLS above 0.1 correlates with roughly a 7% drop in conversions — Google Web.dev research.)

#### Page-Level SEO Checks

For **each page in `$AUDIT_PAGES`**, fetch the HTML directly (WebFetch with a browser User-Agent, or browser MCP) and extract:
- **`<title>`** — exact text and length. Under 60 chars?
- **`<meta name="description">`** — exact text and length. Empty string = fail. Under 160 chars?
- **OG tags** — og:title, og:description, og:image — capture exact values. Missing og:image is a specific flag because it breaks WhatsApp/social previews.
- **Twitter card** — twitter:card present?
- **`<h1>`** — count occurrences on the page.
- **Canonical URL** — present?
- **JSON-LD `@type`** — list every `@type` found in `<script type="application/ld+json">` blocks (flatten `@graph` arrays). Note which `@type`s are present and which important ones are missing.
- **Image alt coverage** — regex count of `<img>` tags vs. `<img>` tags with an `alt` attribute, as a percentage.
- **Visible "last updated" date** — search the rendered HTML for patterns like "Last updated", "Updated on", "Updated:".

#### Site-Wide SEO & Infrastructure Checks

Run these once per audit:
- **`/sitemap.xml` / `/sitemap_index.xml` / `/wp-sitemap.xml`** — which one resolves? HTTP status?
- **`/robots.txt`** — fetch raw text. Does it reference the sitemap?
- **`/favicon.ico` and any `<link rel="icon">`** — does the site have a real favicon, or is it the default browser globe?
- **Broken pages** — scan `site-map.json` for any URLs that returned errors during crawl (if Phase 1 captured them).
- **Site-wide alt coverage** — walk every content file in `$RESEARCH/content/` and count total `image` nodes vs. those with non-empty `alt`. This gives a broader number than the per-page spot check.
- **Server-rendered vs JS-injected content** — compare the raw HTML fetched via `curl`/WebFetch against what browser MCP renders. If the rendered DOM has significantly more text than the raw HTML, content is JS-injected (bad for AI crawlers that don't run JS).
- **"Time to first artwork/product"** — count clicks from the homepage to reach the first buyable product/artwork page. Use the homepage's scraped links: is there a direct link, or does the user have to drill through Gallery → Category → Product?

#### AI Search Visibility (GEO) Checks

This is the newest and most important section. SMB owners all want to know: "Can ChatGPT/Perplexity/Gemini cite my site?" Run these checks:

1. **AI crawler robots.txt rules.** Parse `/robots.txt` and check the `User-agent:` directives for each of these bots. For each, record: `allowed` (no Disallow for their UA), `partially_blocked` (some paths blocked), or `fully_blocked` (Disallow: /):
   - `GPTBot` (OpenAI — trains ChatGPT)
   - `OAI-SearchBot` (OpenAI — powers ChatGPT search)
   - `ChatGPT-User` (on-demand fetches)
   - `PerplexityBot` (Perplexity)
   - `Perplexity-User` (on-demand)
   - `ClaudeBot` (Anthropic)
   - `Claude-Web` (Anthropic)
   - `Google-Extended` (Google AI / Gemini training)
   - `Applebot-Extended` (Apple Intelligence)
   - `CCBot` (Common Crawl — feeds many LLMs)
   - `Bytespider` (ByteDance)
   - `Amazonbot` (Amazon/Alexa)

2. **`/llms.txt` and `/llms-full.txt`** — probe both. HTTP 200 = present. Most sites won't have these; it's a quick-win for the client.

3. **Structured data inventory.** From the JSON-LD types captured above (across all audited pages), specifically check for presence of these high-value `@type`s. Each one missing is a quick win:
   - `Organization` (on homepage or `/about`)
   - `LocalBusiness` (critical for local SEO + AI "best X in Y" queries)
   - `WebSite` with `SearchAction`
   - `BreadcrumbList`
   - `Product` (for each artwork/product — only sample one)
   - `Person` (for each artist profile — only sample one)
   - `Event` (for exhibitions, if applicable)
   - `FAQPage` (anywhere)
   - `ImageObject` with `creator`

4. **Entity signals for authority.** Check whether the homepage or about page includes:
   - Founding date / founded year
   - Physical address (text form, not just map iframe)
   - Opening hours
   - `sameAs` links to social profiles inside JSON-LD
   - Named founder/owner mentioned by name

5. **Content extractability (SSR vs CSR).** Compare raw HTML character count vs. rendered DOM text length. Ratio < 0.5 = content is mostly JS-injected (bad for AI). Note the ratio.

6. **Heading hierarchy quality.** From the scraped content, check each audited page has exactly one `<h1>`, heading levels don't skip (no h1 → h3), and headings are descriptive (not "Click here", "Learn more").

7. **Descriptive link text.** Scan scraped content for generic anchors — count occurrences of "click here", "read more", "learn more", "here". These hurt both SEO and AI extraction.

8. **Live AI citation test (optional).** If the user has configured a Perplexity or OpenAI API key in `.env` (`PERPLEXITY_API_KEY` / `OPENAI_API_KEY`), run two test queries against Perplexity's Chat Completions API:
   - `"best {business.type} in {business.location}"` (e.g., "best art galleries in Gurgaon")
   - `"{business.name} {business.location}"` (e.g., "Gallery One India Gurgaon")
   Check whether the response text includes the client's domain or a citation pointing to it. Record `cited: true|false` plus the competing domains that WERE cited.
   **Gracefully skip this check if no API key is present** — just note "Live AI citation test skipped (no API key configured)" in the report.

9. **Build the AI-ready quick wins checklist.** From all the above, synthesize 6–8 concrete, cheap-to-fix items. Examples: "Add `Organization` + `LocalBusiness` JSON-LD to homepage (30 min)", "Publish `/llms.txt` pointing at About + Services + Contact (15 min)", "Add og:image to all product pages (templated — 1 hour)", "Unblock GPTBot and PerplexityBot in robots.txt (2 min)".

### Write the Report (HTML)

### Write the Report (HTML)

Save to `$REPORT/site-audit.html`. This is a **self-contained HTML file** with embedded CSS — no external dependencies. It must look professional enough to share directly with a client AND function as marketing collateral (screenshot-worthy, forwardable, referenceable).

The HTML must include, in order:

1. **Inline CSS** — all styles embedded. Clean, modern design; max-width ~820px; Inter or system font; print-friendly `@media print` styles.

2. **Hero Stat Strip** (right below the header, above "At a Glance") — a single horizontal row with 3 big numbers and short labels:
   - `{N} pages audited` (count from site-map.json total_pages_discovered)
   - `{M} quick wins identified` (total count of specific numeric recommendations surfaced in this report)
   - `~{X}s faster on mobile` (estimated time saved derived from Lighthouse opportunities)

3. **Color swatches** — colored circles + names + hex (already in current template).

4. **Screenshots** — base64-embedded, desktop + mobile for each audited page.

5. **PageSpeed gauges** — circular gauges, colour-coded (0–49 red `#ff4e42`, 50–89 orange `#ffa400`, 90–100 green `#0cce6b`). Mobile + desktop side-by-side. **Always accompanied by a one-liner explaining why mobile and desktop scores may diverge** — e.g., desktop may score lower than mobile if CLS is the dominant issue, because the larger viewport amplifies layout shifts.

6. **Core Web Vitals table** — LCP, CLS, TBT, Speed Index with pass/warn/fail pills.

7. **Numeric findings** — every bullet must carry a real number (MB saved, count of missing alt tags, number of clicks to first product, etc.). No adjectival findings.

8. **CLS → Conversion Impact callout** — under the CLS finding, include: "Google's Web.dev research shows every 0.1 of CLS above 0.1 correlates with a ~7% drop in conversions. Your current CLS of {X} implies roughly {Y}% conversion drag." Compute `Y` using the formula from Numeric Findings Extraction above.

9. **WhatsApp / Social Share Preview** (NEW section, high marketing value) — an HTML/CSS mockup of a WhatsApp chat bubble showing how a product/artwork URL previews today (likely a broken/empty card due to missing og:image or og:description) side-by-side with the post-rebuild version. Render as two `.chat-bubble` divs with a WhatsApp-style card inside. Use the scraped actual title/description/image of one product page. This is the single highest-impact visual for SMB owners — they instantly "get it."

10. **Google SERP Preview** (NEW section) — render the client's actual scraped `<title>` and `<meta name="description">` as they'd appear in a Google search result card (blue link, green URL, grey snippet), alongside an improved version with a better title and a hand-crafted meta description. Use classes `.serp-card` and `.serp-card.improved`.

11. **Per-page deep dives** — Homepage + 1-2 others, each with screenshots, gauges, Core Web Vitals, and numeric findings.

12. **AI Search Visibility (GEO)** — NEW section, sits after the per-page deep dives and before the recommendation. Structure:
    - **Opening line (plain English, no jargon):** "When someone asks ChatGPT or Perplexity 'best {business.type} in {business.location}', can your site be cited? Here's what AI crawlers see today."
    - **AI crawler access table** — rows: GPTBot, PerplexityBot, ClaudeBot, Google-Extended, Applebot-Extended, CCBot, Bytespider. Columns: Status (allowed / blocked / not mentioned), What it means (plain English).
    - **`llms.txt` status** — "Not yet published. This is a new standard that's becoming the AI-era equivalent of `robots.txt`. Most sites haven't added it — adding yours is a 15-minute win."
    - **Structured data scorecard** — for each of the high-value `@type`s (Organization, LocalBusiness, Product, Person, BreadcrumbList, FAQPage), show ✓ present or → missing with a one-line "why it matters".
    - **Entity signals** — found / not found for founding date, address, hours, `sameAs` links, named founder.
    - **Content extractability** — SSR vs CSR ratio, plain-English interpretation.
    - **Heading / link quality** — count of `<h1>`s, heading hierarchy gaps, count of generic "click here"/"read more" links.
    - **Live AI citation test** — if run: "We asked Perplexity 'best {category} in {city}' — you {were / weren't} cited. The sites it did cite: {list}." If skipped: small note "Live AI citation test skipped — no API key configured."
    - **AI-ready quick wins checklist** — 6-8 items with estimated time (e.g., "✓ 2 min — Unblock GPTBot and PerplexityBot in robots.txt").
    - **Framing throughout:** "This is a new opportunity, not a deficiency. Most {category} sites aren't ready for AI search yet — getting ahead of it is a 1-week project." This is also the marketing hook.

13. **SEO Overview** — site-wide summary with comparison table (page × check).

14. **Our Recommendation** — **two options only** (drop the third, or reframe Option C as "Phase 2"):
    - **Option A — Faithful Rebuild (recommended)** — same structure, same content, modern foundation.
    - **Option B — Same Bones, New Look** — keep sitemap, apply fresh design.
    - Under the recommended option, include a one-sentence **"What we'd ship in week one"** preview (e.g., "Homepage, About, Gallery listing, and Contact — mobile-first, with CLS fixed and og:image on every product so WhatsApp previews work.").

15. **Favicon / Tap Targets / Google Business Profile** — small section under SEO Overview covering:
    - Favicon: detected/default/missing
    - Mobile tap target failures (from Lighthouse `tap-targets` audit, numeric)
    - Google Business Profile: is the business listed? Is it linked from the site? (Best-effort check — search for the business name and look for GBP-style results; if no API, just note "Not linked from your site. If you have a GBP listing, we'll connect it during the rebuild.")

16. **What Happens Next** — numbered steps (unchanged).

17. **Marketing Snippets** (NEW, at the very bottom, in a small collapsed/footer block titled "For the Publifai team — copy-paste snippets") — three pre-written snippets generated from the actual audit data:
    - **Tweet-length stat:** e.g., `"We audited all {N} pages of {business.name}. Found {M} things we'd fix in week one. The biggest one: {top finding}."`
    - **WhatsApp opener:** e.g., `"Hi {owner.name}, we took a fresh look at {domain}. The good news: your catalogue is solid. The one thing that jumped out: {top finding in one sentence}. Want to see the full review?"`
    - **Cold email subject + first line:** subject like `"A 2-minute fix worth ~{X}s on your homepage"` and a first line referencing the specific metric.

Follow this content structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Business Name] — Website Review</title>
  <style>
    /* Modern, clean report styles — embed all CSS here */
    /* Include @media print styles */
  </style>
</head>
<body>
  <header>
    <!-- Client logo (base64-encoded from $IMAGES/logo.png), business name, domain -->
    <img src="data:image/png;base64,..." alt="[Business Name] logo" class="client-logo" />
    <h1>[Business Name] — Website Review</h1>
    <p class="domain">[domain, e.g. www.galleryoneindia.com]</p>
    <p class="subtitle">Prepared by Publifai | [Date]</p>
  </header>

  <section id="hero-stats">
    <!-- Single horizontal row with 3 big numbers -->
    <div class="stat-strip">
      <div class="stat"><div class="big">{N}</div><div class="label">pages audited</div></div>
      <div class="stat"><div class="big">{M}</div><div class="label">quick wins identified</div></div>
      <div class="stat"><div class="big">~{X}s</div><div class="label">faster on mobile (est.)</div></div>
    </div>
  </section>

  <section id="at-a-glance">
    <!-- 2-3 sentences: page count, site overview, overall impression -->
    <!-- Lead with what's working well -->
    <!-- Include a homepage screenshot (base64-encoded from $SCREENSHOTS/) -->
    <figure class="hero-screenshot">
      <img src="data:image/png;base64,..." alt="Current homepage" />
      <figcaption>Your current homepage</figcaption>
    </figure>
  </section>

  <section id="pages">
    <h2>Pages & Structure</h2>
    <!-- List unique pages with descriptions -->
    <!-- Template groups in plain language -->
    <!-- Flag broken/error pages if any -->
  </section>

  <section id="design">
    <h2>Design & Branding</h2>
    <!-- Color palette with rendered swatches -->
    <!-- Font information -->
    <!-- Overall style description -->
    <!-- What's working well / what could be improved -->
  </section>

  <!-- ===== PER-PAGE DEEP DIVES ===== -->
  <!-- Repeat this block for each page in $AUDIT_PAGES (2-3 pages) -->

  <section id="page-homepage" class="page-audit">
    <h2>Homepage — Deep Dive</h2>

    <div class="page-screenshots">
      <!-- Desktop + mobile screenshots side by side, base64-encoded -->
      <figure>
        <img src="data:image/png;base64,..." alt="Homepage on desktop" />
        <figcaption>Desktop (1440px)</figcaption>
      </figure>
      <figure>
        <img src="data:image/png;base64,..." alt="Homepage on mobile" />
        <figcaption>Mobile (390px)</figcaption>
      </figure>
    </div>

    <div class="page-scores">
      <h3>Speed & Performance</h3>
      <!-- PageSpeed score gauges for THIS page: Performance, Accessibility, SEO -->
      <!-- Show mobile and desktop side by side -->
      <!-- Core Web Vitals table for THIS page -->
      <!-- Plain-language: "Your homepage scores 34/100 on phones..." -->
      <!-- Top 3 opportunities with estimated savings -->
    </div>

    <div class="page-seo">
      <h3>Search Visibility</h3>
      <!-- SEO checks for THIS page: title, description, OG, alt text, H1, structured data -->
      <!-- Pass/fail indicators for each check -->
    </div>
  </section>

  <section id="page-[slug]" class="page-audit">
    <h2>[Page Name] — Deep Dive</h2>
    <!-- Same structure: screenshots, scores, SEO checks -->
    <!-- Repeat for each additional audited page -->
  </section>

  <!-- ===== END PER-PAGE DEEP DIVES ===== -->

  <section id="seo-summary">
    <h2>SEO Overview</h2>
    <!-- Site-wide SEO summary: sitemap, robots.txt, overall alt text coverage -->
    <!-- Comparison table: page × check → pass/fail across all audited pages -->
    <!-- Frame gaps as easy wins -->
  </section>

  <!-- ===== NEW: WhatsApp / Social Share Preview ===== -->
  <section id="share-preview">
    <h2>How Your Links Look on WhatsApp &amp; Social</h2>
    <p>When someone pastes one of your artwork links into a WhatsApp chat, this is what shows up today — and what it could look like instead:</p>
    <div class="share-compare">
      <div class="chat-bubble now">
        <div class="chat-label">Today</div>
        <!-- broken/empty preview card using actual scraped title/desc -->
      </div>
      <div class="chat-bubble after">
        <div class="chat-label">After rebuild</div>
        <!-- rich preview card with image, title, description -->
      </div>
    </div>
  </section>

  <!-- ===== NEW: Google SERP Preview ===== -->
  <section id="serp-preview">
    <h2>How You Appear in Google Search</h2>
    <p>Your site's search result snippet today vs. after the rebuild:</p>
    <div class="serp-card"><!-- current scraped title + description --></div>
    <div class="serp-card improved"><!-- improved title + hand-crafted meta description --></div>
  </section>

  <!-- ===== NEW: AI Search Visibility (GEO) ===== -->
  <section id="ai-visibility">
    <h2>AI Search Visibility</h2>
    <p class="lead">When someone asks ChatGPT or Perplexity "best [business type] in [city]", can your site be cited? Here's what AI crawlers see today.</p>
    <!-- AI crawler access table -->
    <!-- llms.txt status -->
    <!-- Structured data scorecard (Organization, LocalBusiness, Product, Person, BreadcrumbList, FAQPage) -->
    <!-- Entity signals: founding date, address, hours, sameAs, founder name -->
    <!-- Content extractability (SSR vs CSR ratio) -->
    <!-- Heading + link quality counts -->
    <!-- Live AI citation test result (or "skipped — no API key") -->
    <!-- AI-ready quick wins checklist (6-8 items with time estimates) -->
    <p class="opportunity-frame"><strong>Most [category] sites aren't ready for this yet — getting ahead of AI search is a 1-week project, not a 6-month project.</strong></p>
  </section>

  <section id="recommendation">
    <h2>Our Recommendation</h2>
    <!-- TWO options only (drop Option C or reframe as "Phase 2") -->
    <!-- Option A: Faithful Rebuild (RECOMMENDED) + "What we'd ship in week one" one-liner -->
    <!-- Option B: Same Bones, New Look -->
    <!-- "Which direction feels right to you?" -->
  </section>

  <section id="next-steps">
    <h2>What Happens Next</h2>
    <ol>
      <li>We'll agree on the page structure together</li>
      <li>Then lock in the design direction — colors, style, feel</li>
      <li>I'll build your site and send you a preview link</li>
      <li>You tell me what to change — as many rounds as you need</li>
      <li>When you're happy, we go live</li>
    </ol>
  </section>

  <!-- ===== NEW: Marketing Snippets (for Publifai team) ===== -->
  <section id="marketing-snippets" class="snippets">
    <h2>For the Publifai team — copy-paste snippets</h2>
    <p class="snippets-note">These are generated from this audit's actual findings. Use them in outreach.</p>
    <div class="snippet">
      <div class="snippet-label">Tweet-length stat</div>
      <div class="snippet-body"><!-- "We audited all {N} pages of {name}. Found {M} things we'd fix in week one. The biggest one: {top finding}." --></div>
    </div>
    <div class="snippet">
      <div class="snippet-label">WhatsApp opener</div>
      <div class="snippet-body"><!-- "Hi {owner}, we took a fresh look at {domain}. The good news: {one positive}. The one thing that jumped out: {top finding}. Want to see the full review?" --></div>
    </div>
    <div class="snippet">
      <div class="snippet-label">Cold email</div>
      <div class="snippet-body">
        <div><strong>Subject:</strong> <!-- "A 2-minute fix worth ~{X}s on {domain}" --></div>
        <div><strong>First line:</strong> <!-- references specific metric --></div>
      </div>
    </div>
  </section>

  <footer>
    <!-- "This report was generated from an automated scan..." -->
    <!-- Publifai contact info -->
  </footer>
</body>
</html>
```

### Report Guidelines

- **Length:** Roughly 4-6 printed pages. Dense with data, but readable.
- **Tone:** Friendly consultant, not a technical scanner. Explain findings like you're talking to the owner over coffee.
- **Framing:** "Here's what we can improve" not "here's what's wrong." Lead each section with positives. Frame GEO as opportunity, not deficiency: "Most sites aren't ready for this yet — getting ahead is a 1-week project."
- **No jargon:** No "render-blocking," "DOM," "viewport," "CDN," "LCP," "CLS." Translate everything. Say "time until the main image appears" instead of "LCP." When you *must* use a term (e.g., CLS in the vitals table), always pair it with the plain-English meaning.
- **Every finding is numeric.** No adjectives like "images could be optimized" — say "your homepage is 4.8 MB today; compressing and right-sizing images cuts it to ~1.2 MB (saves 3.6 MB)." Same for alt text ("63 of 218 images on your site are missing alt text"), links ("4 clicks from homepage to the first buyable artwork"), etc.
- **PageSpeed scores:** Always explain in human terms. And **always include a one-liner on why mobile and desktop may diverge** — if desktop scores worse, it's usually CLS-driven (larger viewport amplifies layout shift). Don't let the reader be confused by "Mobile 60 / Desktop 42" without context.
- **CLS → conversion impact:** Under every CLS finding, include the computed "~Y% conversion drag" number derived from the 7%-per-0.1-above-0.1 rule of thumb.
- **WhatsApp / SERP mockups:** These are the single highest-value visuals for SMB owners. Use actual scraped title/description/image data — not placeholders. Render the "today" version showing what's broken (e.g., empty meta description → Google shows a generic fallback).
- **AI Search Visibility (GEO) section:** Must include all 8 checks. Frame as opportunity. End with the quick-wins checklist.
- **Recommendation:** Two options only, not three. Under the recommended option, include the "What we'd ship in week one" one-liner.
- **Marketing snippets block:** Always include at the bottom. Auto-generate from real audit data — do not use templated fillers.
- **Color palette:** Friendly names + hex + rendered swatches.
- **Screenshots:** Desktop + mobile base64-embedded for each audited page.
- **Client logo:** Only if it actually exists in `$IMAGES/` or `$SEO/`. Never generate or fabricate.
- **Client domain:** Prominent in header.
- **Self-contained:** Must render standalone with no external deps (Google Fonts degrades gracefully).
- **Deploys cleanly:** The report must deploy to `<slug>.pages.dev/audit/` without broken images or missing assets.

### Deploy the Audit to `<slug>.pages.dev/audit/`

After the HTML is generated, publish the audit to the client's Cloudflare Pages project so it's shareable via a live URL. This assumes `scripts/provision-site.sh` has already been run.

The deploy source of truth is `clients/<client-folder>/public/`. Every Publifai skill that wants something live on `<slug>.pages.dev` writes into that folder and then calls the shared deploy script — no per-skill staging.

**Steps:**

1. **Read slug** from `client.json`: `domains.subdomain` (strip `.pages.dev`).
2. **Populate `public/audit/`** in the client folder (outside this repo, in `$CLIENTS_DIR/<name>/public/audit/`):
   - Copy `$REPORT/site-audit.html` → `$CLIENTS_DIR/<name>/public/audit/index.html`
3. If `$CLIENTS_DIR/<name>/public/index.html` does not yet exist, create a minimal placeholder linking to `/audit/` (so visitors hitting the root see something). Use `[Business Name]` from `client.json`:
   ```html
   <!DOCTYPE html>
   <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>[Business Name] — Coming soon on Publifai</title><style>body{font-family:system-ui,-apple-system,sans-serif;max-width:560px;margin:10vh auto;padding:0 24px;color:#1a1a1a}h1{font-size:28px;margin-bottom:8px}p{line-height:1.6;color:#555}a{display:inline-block;margin-top:16px;padding:10px 18px;background:#111;color:#fff;text-decoration:none;border-radius:6px}a:hover{background:#333}</style></head><body><h1>[Business Name]</h1><p>Your new website is being built on Publifai. In the meantime, here is the review we prepared of your current site.</p><a href="/audit/">View the site review →</a></body></html>
   ```
4. **Call the publifai-level deploy script** from the publifai repo root (the repo that contains `clients/`). Pass only the **client folder name** — the script reads the Pages project slug from `client.json`:
   ```bash
   cd <publifai-repo-root>
   ./scripts/deploy-client.sh <client-folder>
   ```
   The script stages the folder (ignoring `client.json` and dotfiles), deploys via `wrangler pages deploy` to the project's production branch, and appends a deploy note to `client.json`.
5. **Update client.json** (in addition to the note the script adds):
   - `phases.B_capture.discover.audit_report.report_deployed_url` = `https://<slug>.pages.dev/audit/`

The audit is now live at `https://<slug>.pages.dev/audit/`. Because `public/` is the single deploy source, future skills that add new live content (mirror, draft build, production) just drop their files into the same `public/` folder and re-run `./scripts/deploy-client.sh` — the audit keeps working automatically.

## Phase 4: Content Extraction (Output 4)

**Skip this phase if `--phases` was provided and `4` is not in the list.**
**Requires:** `$RESEARCH/site-map.json` (Phase 1). If missing, warn the user and skip this phase.

Goal: Extract content from representative pages ONLY.

### Which Pages to Scrape

- **Every unique page** from the site map
- **ONE representative page per template group** (the `example_url`)
- **NEVER scrape more than ~10 pages total** regardless of site size
- **Skip pages behind authentication** (login, admin, my-account)

### What to Extract Per Page

For each page, navigate with browser MCP and extract:

1. **Meta information:**
   - `<title>` tag content
   - Meta description
   - Open Graph tags (og:title, og:description, og:image)
   - Canonical URL
   - Any JSON-LD structured data

2. **Heading hierarchy:**
   - Every H1, H2, H3, H4 with their exact text
   - Nesting structure (which H3s are under which H2, etc.)

3. **Body content:**
   - All paragraph text, verbatim
   - Lists (ordered and unordered) with items
   - Blockquotes
   - Tables with data

4. **Images:**
   - All `<img>` src URLs, alt text, and context (hero, inline, gallery, background)
   - Download each to `$IMAGES/`

5. **Links:**
   - Internal navigation links
   - External links
   - Social media links
   - CTA buttons with their text and target

6. **Forms:**
   - Form fields (name, type, placeholder, required)
   - Form action URL
   - Submit button text

7. **Embedded content:**
   - Google Maps iframes (extract coordinates/address)
   - YouTube/Vimeo embeds (extract video IDs)
   - Social media embeds

8. **For template pages specifically:**
   - Mark each field as `"variable"` (changes per instance — e.g., artist name, bio, artwork image) or `"fixed"` (same on every instance — e.g., sidebar layout, related sections)

### Output Content Files

Save one file per scraped page in `$RESEARCH/content/`:

```json
{
  "url": "/about-us/",
  "label": "About Us",
  "type": "unique_page",
  "scraped_at": "2026-04-04T12:00:00Z",
  "meta": {
    "title": "About Us - Gallery One India",
    "description": "Learn about Gallery One India...",
    "og_image": "/images/seo/og-about.jpg",
    "canonical": "https://www.galleryoneindia.com/about-us/"
  },
  "headings": [
    { "level": 1, "text": "About Us" },
    { "level": 2, "text": "Our Story" },
    { "level": 2, "text": "Our Team" }
  ],
  "content": [
    {
      "type": "paragraph",
      "text": "1999. Gurgaon City, bordering New Delhi..."
    },
    {
      "type": "image",
      "src": "/images/about-gallery.jpg",
      "alt": "Gallery One India interior",
      "context": "inline"
    }
  ],
  "links": {
    "internal": ["/contact/", "/gallery/"],
    "external": [],
    "social": ["https://facebook.com/galleryoneindia"]
  },
  "forms": [],
  "embedded": []
}
```

For template pages, add a `template_fields` section:

```json
{
  "url": "/product/jagannath-paul/",
  "type": "template_instance",
  "template_name": "Product Page",
  "template_fields": {
    "variable": {
      "product_name": "Jagannath Paul",
      "product_image": "/images/products/jagannath-paul.jpg",
      "artist_name": "Jagannath Paul",
      "size": "48 x 48 Inches",
      "price": 400000,
      "description": "..."
    },
    "fixed": {
      "sidebar_sections": ["Related Artworks", "Artist Info"],
      "page_layout": "two-column with sidebar"
    }
  }
}
```

## Smart Scraping Rules

These are hard limits — never violate them:

- **Never scrape more than 10 pages** regardless of site size
- All unique pages get scraped (usually 4-6)
- One representative per template group (usually 1-3)
- If site has 500+ pages, it's almost certainly 5-6 unique pages + a few template types with hundreds of instances
- Download ALL images from scraped pages (client will need them)
- **Skip pages behind authentication** (admin panels, member areas, login pages)
- **Skip pagination** (`?page=2`, `/page/2/`)
- **Skip search results** (`?s=`, `?q=`)
- **Skip feed URLs** (`/feed/`, `/rss/`)
- **Respect robots.txt** — check it before crawling

## Completion

When all requested phases are done, print a summary. Only include sections for phases that were actually run. If `--phases` was used, also note which phases were skipped.

```
Site Discovery Complete: example.com
═══════════════════════════════════════
Phases run: 1, 2, 3, 4  (or "1, 2" if --phases was used)

Site Map:                              ← only if Phase 1 ran
  • 6 unique pages discovered
  • 2 template groups (47 products, 12 blog posts)
  • 64 total pages on site
  Saved → $RESEARCH/site-map.json

Design System:                         ← only if Phase 2 ran
  • Primary: #313131, Accent: #007cba
  • Fonts: Playfair Display (headings), Open Sans (body)
  • 16 assets downloaded to $IMAGES/
  Saved → $RESEARCH/design-system.json

Site Audit Report:                     ← only if Phase 3 ran
  • Client-facing website review with PageSpeed scores
  • Desktop: Performance XX/100, Accessibility XX/100, SEO XX/100
  • Mobile:  Performance XX/100, Accessibility XX/100, SEO XX/100
  Saved  → $REPORT/site-audit.html
  Live   → https://<slug>.pages.dev/audit/

Content Extracted:                     ← only if Phase 4 ran
  • 8 pages scraped (6 unique + 2 templates)
  • 24 images downloaded
  Saved → $RESEARCH/content/

Next step: Share the audit report with the client, then run /clone-website with the same --client flag to build the site.
```

If phases were skipped, suggest the next command to run remaining phases:
```
To run remaining phases: /discover-site <url> --client <name> --phases 3,4
```
