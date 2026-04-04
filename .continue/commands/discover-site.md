---
name: discover-site
description: "Discover a website's full structure via sitemap/navigation crawling, extract its design system, and pull content from re"
invokable: true
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
   - Extract the base URL (first non-flag argument). Normalize it (add `https://` if missing, strip trailing paths to get the domain root). Verify the site is accessible.
   - Check for `--client <name>` flag. If present, all output goes into a client-specific folder. If absent, fall back to repo-root paths for backward compatibility.
   - Check for `--phases <list>` flag. If present, parse the comma-separated list of phase numbers (e.g., `--phases 1,2` or `--phases 3,4`). Only run the listed phases. If absent, run all 4 phases.
     - Valid phase numbers: `1` (Site Map), `2` (Design System), `3` (Site Audit Report), `4` (Content Extraction).
     - **Phase dependencies:** Phase 3 (audit report) reads outputs from Phases 1 and 2. If running Phase 3 without 1 or 2, check that the required files (`site-map.json`, `design-system.json`) already exist from a previous run. If missing, warn the user and skip Phase 3.
     - Phase 4 (content extraction) reads the site map from Phase 1. If running Phase 4 without 1, check that `site-map.json` exists. If missing, warn the user and skip Phase 4.
3. **Resolve the clients directory:**
   - Read `.env` file in the repo root for `CLIENTS_DIR`. Default: `../clients` (parent-level, shared across all Publifai tools).
   - Resolve the path relative to the repo root to get an absolute path. Store as `$CLIENTS_DIR`.
   - Example: if repo is at `/Users/me/repos/publifai/ai-website-cloner-template` and `CLIENTS_DIR=../clients`, then `$CLIENTS_DIR` = `/Users/me/repos/publifai/clients`.
4. **Set output paths** based on whether `--client` was provided:

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
   | Audit report (PDF) | `$CLIENTS_DIR/<name>/report/site-audit.pdf` | `docs/research/site-audit.pdf` |

   Use these paths consistently throughout all phases. From here on, this document uses `$RESEARCH`, `$SCREENSHOTS`, `$IMAGES`, `$SEO`, `$SCRIPTS`, and `$REPORT` as placeholders for the resolved paths.

5. Create all output directories.

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
2. Download favicon, apple-touch-icon, OG images to `$SEO/`
3. Note any external fonts (Google Fonts URLs, self-hosted font files)

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

Goal: Generate a polished, client-facing audit report as a styled HTML file (primary deliverable) and a PDF (for sharing via WhatsApp/email). Written for a non-technical small business owner — no jargon, friendly professional tone.

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

These assets are produced by Phase 2 and MUST be embedded in the report:

1. **Client logo** — Find the logo image file. Check in order:
   - `$IMAGES/logo.png` (most common)
   - `$IMAGES/logo.jpg`, `$IMAGES/logo.svg`
   - `$SEO/logo.png`
   - The `assets.logo` path from `design-system.json`
   If found, read the file and base64-encode it for embedding in the report header.

2. **Homepage screenshot** — Find at least one homepage screenshot from Phase 2:
   - `$SCREENSHOTS/homepage-desktop.png` (preferred)
   - `$SCREENSHOTS/comparison.png`
   - Any file in `$SCREENSHOTS/` matching `*homepage*` or `*home*`
   If found, read the file and base64-encode it for embedding in the "At a Glance" or homepage deep-dive section.

3. **Client domain** — Extract from `base_url` in `site-map.json` (e.g., `www.galleryoneindia.com`). Display prominently in the report header alongside the business name.

#### Select Audit Pages

Pick **2-3 pages** to audit in depth. These pages get individual PageSpeed scores, screenshots, and SEO checks:

1. **Homepage** (always) — the front door
2. **One interior content page** — pick the most important non-homepage page (e.g., About, Services, or a key product/listing page). Prefer a page with distinct layout from the homepage.
3. **One template instance** (optional, if the site has template groups) — pick the `example_url` from the most important template group (e.g., a product page, artist profile, or blog post)

Store the selected page URLs as `$AUDIT_PAGES` (list of 2-3 full URLs). Use these consistently for PageSpeed, screenshots, and SEO checks below.

#### Google PageSpeed Insights

Fetch real performance data from the Google PageSpeed Insights API (free, no API key required) **for each page in `$AUDIT_PAGES`**:

```
https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=<PAGE_URL>&strategy=<mobile|desktop>&category=performance&category=accessibility&category=seo
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

#### Browser-Based SEO Checks

For **each page in `$AUDIT_PAGES`**, check via browser MCP (or WebFetch):
- **`<title>` tag** — present? Unique across pages? Reasonable length (under 60 chars)?
- **Meta description** — present? Unique? Reasonable length (under 160 chars)?
- **OG tags** — og:title, og:description, og:image present?
- **Image alt text** — count total images and how many are missing alt text
- **JSON-LD structured data** — any present? What `@type`?
- **H1 tag** — exactly one per page?
- **Canonical URL** — present?

Also check site-wide (once):
- **sitemap.xml** — present and accessible?
- **robots.txt** — present? Does it reference the sitemap?
- **Broken pages** — note any pages from the site map returning errors (500, 404, etc.)

Compile per-page SEO results into a comparison table for the report (page name × check → pass/fail).

### Write the Report (HTML)

Save to `$REPORT/site-audit.html`. This is a **self-contained HTML file** with embedded CSS — no external dependencies. It should look professional enough to share directly with a client.

The HTML should include:

1. **Inline CSS** — all styles embedded in a `<style>` tag. Use a clean, modern design:
   - Sans-serif body font (system font stack or Inter/Open Sans via Google Fonts `<link>`)
   - Generous whitespace, max-width ~800px centered container
   - Subtle section dividers
   - Print-friendly `@media print` styles (hide non-essential decorations, ensure black text)
   - A4-friendly proportions

2. **Color swatches** — render each color in the palette as a small colored circle/square (`<span>` with inline `background-color`) next to its name and hex code. This is the key advantage over markdown.

3. **Screenshots** — embed screenshots from `$SCREENSHOTS/` as `<img>` tags with **base64-encoded data URIs** so the HTML file is fully self-contained. Read each screenshot file, base64-encode it, and embed as `src="data:image/png;base64,..."`. If screenshots are large, resize to max 800px width before encoding. Include screenshots for **each audited page** (desktop + mobile).

4. **PageSpeed score gauges** — render the performance, accessibility, and SEO scores as visual gauge elements (colored circles or semi-circular gauges using CSS):
   - 0-49: Red (`#ff4e42`)
   - 50-89: Orange (`#ffa400`)
   - 90-100: Green (`#0cce6b`)
   - Show the numeric score prominently inside each gauge
   - Display both mobile and desktop scores side by side

5. **Core Web Vitals table** — a clean table showing LCP, CLS, TBT, Speed Index with values and pass/fail indicators

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

  <section id="recommendation">
    <h2>Our Recommendation</h2>
    <!-- Approach suggestion based on findings -->
    <!-- Three options: Fresh start / Faithful rebuild / Same structure new look -->
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

  <footer>
    <!-- "This report was generated from an automated scan..." -->
    <!-- Publifai contact info -->
  </footer>
</body>
</html>
```

### Report Guidelines

- **Length:** The HTML should render to roughly 2-4 printed pages. Be concise but include the data.
- **Tone:** Friendly consultant, not a technical scanner. Write as if you're explaining findings to the business owner over coffee.
- **Framing:** "Here's what we can improve" not "here's what's wrong." Lead each section with positives.
- **No jargon:** Don't use terms like "render-blocking," "DOM," "viewport," "CDN," "LCP." Translate everything into plain language. For example, say "time until your page looks ready" instead of "Largest Contentful Paint."
- **PageSpeed scores:** Present the numbers but always explain what they mean in human terms. "34/100 on mobile means most visitors on phones will leave before your site finishes loading."
- **Color palette:** Use friendly names with hex codes and rendered swatches (e.g., a colored circle + "Dark Charcoal #313131").
- **Screenshots:** Embed desktop + mobile screenshots for each audited page directly in the HTML as base64 data URIs.
- **Client logo:** Embed the client's logo (base64-encoded from `$IMAGES/logo.png`) in the report header. Style it at max 160px wide, centered above the business name.
- **Client domain:** Show the domain (e.g., `www.galleryoneindia.com`) prominently in the header below the business name.
- **Homepage screenshot:** Embed at least one homepage screenshot (base64-encoded from `$SCREENSHOTS/`) in the "At a Glance" section or the homepage deep-dive. Show it at max 100% width with a subtle border/shadow.
- **Self-contained:** The HTML file must work when opened directly in a browser with no internet connection (except Google Fonts, which degrade gracefully to system fonts).

### Generate PDF

After saving the HTML report, generate a PDF version at `$REPORT/site-audit.pdf`.

**Method:** Use a headless browser or HTML-to-PDF tool to convert the HTML file to PDF. Try these approaches in order:

1. **Puppeteer/Playwright** (if available): `page.goto('file:///$REPORT/site-audit.html'); page.pdf({path: '$REPORT/site-audit.pdf', format: 'A4'})`
2. **wkhtmltopdf** (if installed): `wkhtmltopdf $REPORT/site-audit.html $REPORT/site-audit.pdf`
3. **Python weasyprint** (if available): `weasyprint $REPORT/site-audit.html $REPORT/site-audit.pdf`
4. **Fallback:** Write a small Node.js script using puppeteer (`npx puppeteer` if needed) to load the HTML and print to PDF

The PDF should faithfully reproduce the HTML report including color swatches, screenshots, and score gauges.

Both files (`site-audit.html` and `site-audit.pdf`) should exist when Phase 3 is complete.

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
  Saved → $REPORT/site-audit.html
  Saved → $REPORT/site-audit.pdf

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
