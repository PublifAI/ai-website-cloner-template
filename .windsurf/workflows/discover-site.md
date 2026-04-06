<!-- AUTO-GENERATED from .claude/skills/discover-site/SKILL.md — do not edit directly.
     Run `node scripts/sync-skills.mjs` to regenerate. -->


# Discover Site

You are about to discover, perceive, and report on a website. This is the required prerequisite for `/clone-website` — the cloner reads discovery outputs and does not re-fetch.

This skill has THREE phases:

1. **Extract** — scripts + WebFetch + (browser only for link enumeration on SPA sites). Pulls every deterministic signal: sitemap, page list, robots.txt, per-page signals, Lighthouse/PSI, entity data, social/GBP links, raw HTML. No screenshots, no design, no narrative. Output: `audit-data.json` + `site-map.json` + `audit-pages.json` + `raw/*` + `pagespeed/*` + updates to `client.json[branding, business, assets]`.

2. **Perceive** — browser + vision. Captures screenshots of every audit page (+ optional competitor homepages) and derives the design system *from the pixels*, not from scraped CSS. Cross-references the font families actually loaded (from raw HTML `<link>` tags) as a sanity check. Output: `screenshots/*.png` + updates to `client.json[design]` (the full token tree).

3. **Report** — pure synthesis. Reads Phase 1 + Phase 2 outputs, writes `report/index.html`, deploys to the **root** of `<slug>.pages.dev/` so leads can be sent a clean URL. (When `/clone-website` later runs, it will move this audit to `/audit/` so the cloned site takes over the root.) No fetches, no browser, no re-computation.

**Design principles:**
1. **Compute once, read from disk.** Every artifact has exactly one producer phase; later phases read the file.
2. **Scripts own numbers, the LLM owns narrative.** Deterministic work lives in `scripts/audit/*`; the SKILL prompt only selects, reads, and explains.
3. **`client.json` is the cross-phase handshake.** Anything the cloner or future phases need (logo path, business name, design tokens, socials) lives in `client.json`, not scattered across `research/`.
4. **Fail loud, not silent.** Phase 1 is the data gate. If Phase 1 can't fetch a thing, Phase 2 and Phase 3 don't get a second chance — the run halts. No retries, no fallbacks, no "capture one now" escape hatches. One exception: bot-protected sites where WebFetch 403s but a real browser works — in that case Phase 1 may capture the HTML via Phase 2's browser session at Phase 2 start time, once. That's it.
5. **Content scraping for the rebuild lives in `/clone-website`, not here.** This skill produces signals, not builder inputs. Headings, paragraph text, template field mapping belong to clone-website's Phase 1.5.

## Pre-Flight

1. **Browser automation is required.** Check for available browser MCP tools (Chrome MCP, Playwright MCP, Browserbase MCP, Puppeteer MCP, etc.). Use whichever is available — if multiple exist, prefer Chrome MCP. If none are detected, ask the user which browser tool they have and how to connect it.
2. **Parse arguments from `the target URL provided by the user`:**
   - Extract the base URL (first non-flag argument). Normalize it (add `https://` if missing, strip trailing paths to get the domain root).
   - Check for `--client <name>` flag. If present, all output goes into a client-specific folder. If absent, fall back to repo-root paths for backward compatibility.
   - Check for `--phases <list>` flag. If present, parse the comma-separated list of phase numbers (e.g., `--phases 1,2` or `--phases 3`). Only run the listed phases. If absent, run all 3 phases.
     - Valid phase numbers: `1` (Extract), `2` (Perceive), `3` (Report).
     - **Phase dependencies:** Phase 2 reads `audit-pages.json`, `pagespeed/*.json`, `raw/homepage.raw.html`, and `audit-data.json` from Phase 1. Phase 3 reads Phase 1's `audit-data.json` + Phase 2's `client.json[design]` + `screenshots/`. Running a later phase without its prerequisites **fails the run** — no silent fallbacks. If the user runs `--phases 3` on a client that hasn't had Phase 1+2 yet, tell them to run Phase 1+2 first and stop.
   - Check for `--competitors <url1>,<url2>,...` flag (optional). Up to 4 competitor URLs. If absent, Phase 1 Step 4.5 auto-picks from a curated category map (see below); if no map hit, the Category benchmark subsection in the Phase 3 report is skipped.
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
             "extract":  { "status": "pending", "completed": null },
             "perceive": { "status": "pending", "completed": null },
             "report":   { "status": "pending", "completed": null, "report_shared": null, "report_deployed_url": null }
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
   | Audit report (HTML) | `$CLIENTS_DIR/<name>/report/index.html` | `docs/research/index.html` |

   Use these paths consistently throughout all phases. From here on, this document uses `$RESEARCH`, `$SCREENSHOTS`, `$IMAGES`, `$SEO`, `$SCRIPTS`, and `$REPORT` as placeholders for the resolved paths.

6. Create all output directories.

### Updating client.json at Phase Boundaries

**When `--client` is provided**, update `$CLIENTS_DIR/<name>/client.json` at each phase boundary. Use a read-modify-write pattern — never overwrite fields that aren't being updated.

**When a phase starts:** Set its status to `"running"`.

**When a phase completes,** update the following fields (merge, don't replace):

**Note:** All discovery sub-phases live under `phases.B_capture.discover.*` in the new schema. This skill executes Phase B1 (Discover) of Phase B (Capture) in the site-building process. The old `content_extraction` sub-phase is **removed** — content scraping for the rebuild lives in `/clone-website`.

| Phase completes | Fields to set |
|-----------------|---------------|
| Phase 1 (Extract) | `phases.B_capture.discover.extract.status` = `"completed"`, `.completed` = today. `existing_site.pages_discovered` = total count, `existing_site.scraped` = `true`, `status` = `"capturing"` (if not already set), `phases.B_capture.started` = today (if not already set). Set `branding.business_name` (from homepage `<title>`) + `branding.business_name_source`. Copy `audit-data.social.found_via_links` into `business.socials` (merge). Set `assets.favicon_path` if downloaded. |
| Phase 2 (Perceive) | `phases.B_capture.discover.perceive.status` = `"completed"`, `.completed` = today. **`design` = full extracted token tree derived from screenshots** — merge into `client.json[design]` (read-modify-write, preserve human edits like `design.vibe` set during Phase C). Set `branding.logo_path` (if logo was downloaded in Phase 1), `branding.logo_source = "scraped"`. Upgrade `branding.business_name` via logo alt if current source is `domain_fallback`. |
| Phase 3 (Report) | `phases.B_capture.discover.report.status` = `"completed"`, `.completed` = today. After deploy step (below), also set `.report_deployed_url` = `https://<slug>.pages.dev/` (root — clone will later move it to `/audit/`). |

**When ALL requested phases are done:**
- Set `updated` = today
- Discover is complete only when all 3 sub-phases are `"completed"`. Phase B itself (`phases.B_capture.completed`) is set by `/clone-website` + mirror deploy, not here.

**When a phase is skipped** (via `--phases` flag): leave its status as-is.

**Always** set `updated` = today on any write.

## Phase 1: Extract

**Skip this phase if `--phases` was provided and `1` is not in the list.**

Goal: capture every deterministic signal about the site. Scripts do the heavy lifting; this phase is deliberately headless-first. Browser is only used for link enumeration on SPA/CSR sites where WebFetch returns an empty shell — **never for screenshots** (those belong to Phase 2). Phase 1 ends with `audit-data.json`, `site-map.json`, `audit-pages.json`, raw HTML cached per audit page, PSI JSON per audit page, and `client.json` updated with branding + socials.

**Phase 1 is the data gate.** If a required fetch fails here, Phase 2 and Phase 3 do not paper over it — the run halts.

### Step 1: Try Sitemap

1. Fetch `<base-url>/sitemap.xml` via WebFetch
2. If not found, try `<base-url>/sitemap_index.xml`
3. If a sitemap index is found, fetch each child sitemap listed in it
4. Parse all `<loc>` URLs from the sitemap(s)
5. **Also save raw sitemap XML** to `$RESEARCH/raw/sitemap.xml` (so Phase 3's `gather-audit-data.mjs` can reuse it without refetching).
6. **Fetch `<base-url>/robots.txt`** via WebFetch and save the raw body to `$RESEARCH/raw/robots.txt`. This is the single source of truth for robots.txt across all phases — `gather-audit-data.mjs` short-circuits its own fetch if this file exists.
7. If no sitemap exists, fall back to Step 2

### Step 2: Navigation Crawling (fallback or supplement)

If no sitemap, or if the sitemap seems incomplete:

1. Navigate to the homepage with browser MCP
2. Extract ALL internal links from:
   - Header navigation (including dropdowns and mega menus)
   - Footer links
   - Sidebar menus
   - Body content links
3. For each discovered page, visit it and extract any NEW internal links not yet seen
4. **While the page is loaded, also dump rendered HTML to `$RESEARCH/raw/<slug>.html`** (slug = URL path normalized with `/` replaced by `-`, empty path = `homepage`). This is best-effort: crawl is primary, raw dump is a side effect.
5. **Also do a second un-rendered WebFetch with a desktop browser UA** and save the response body to `$RESEARCH/raw/<slug>.raw.html`. This is what `extract-page-signals.mjs` uses for SSR vs CSR ratio — it must be the server response, not the hydrated DOM.
6. **Depth limit: 2 levels** from homepage (homepage → linked page → linked from that page)
7. **Page limit: never discover more than 200 URLs** — stop crawling when you hit this
8. Deduplicate URLs (strip query params, anchors, trailing slashes for comparison)

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

### Step 4.5: Pick Competitors

Competitor homepages power the Design → Category benchmark subsection in the Phase 3 report. Decision tree:

1. **If `--competitors <url1>,<url2>,...` was passed** → use those URLs (up to 4). Source = `"flag"`.
2. **Else auto-pick from a curated category map:**
   - Read `business.type` from `client.json` if set. Otherwise infer by keyword-matching the homepage `<title>` + any JSON-LD `@type` on the homepage against the map's keys (case-insensitive): "gallery" → `art_gallery`, "restaurant" / "cafe" → `restaurant_india`, "boutique" / "fashion" → `boutique_fashion`, "clinic" / "hospital" → `clinic_india`, "salon" / "spa" → `salon_india`, "hotel" / "resort" → `hotel_india`, "school" / "academy" → `school_india`, "law" / "legal" / "advocate" → `law_firm_india`.
   - Look up the curated exemplars (2 picks) from this map:
     ```yaml
     art_gallery:      [https://gagosian.com, https://www.davidzwirner.com]
     restaurant_india: [https://thebombaycanteen.com, https://indianaccent.com]
     boutique_fashion: [https://www.nicobar.com, https://www.goodearth.in]
     clinic_india:     [https://www.apollohospitals.com, https://www.fortishealthcare.com]
     salon_india:      [https://www.lakmesalon.in, https://www.enrichsalon.com]
     hotel_india:      [https://www.tajhotels.com, https://www.theleela.com]
     school_india:     [https://www.dpsrkpuram.com, https://www.modernschool.net]
     law_firm_india:   [https://www.azbpartners.com, https://www.trilegal.com]
     ```
   - Source = `"auto"`.
3. **No map hit** → skip competitors entirely. Source = `"none"`, `urls = []`. Phase 3's Category benchmark subsection will not render.

Write the result to `$RESEARCH/competitors.json`:

```json
{ "source": "flag | auto | none", "urls": ["https://...", "https://..."] }
```

Also write it to `client.json[phases.B_capture.discover.competitors] = { source, urls }`.

### Step 5: Compute and Persist the Canonical Audit Page List

Right after writing `site-map.json`, compute the **canonical list of pages that every downstream phase will use** for screenshots, PSI, signal extraction, and content scraping. Write it to `$RESEARCH/audit-pages.json`:

Selection rule (runs here, once):
- **Homepage** (always, `role: "homepage"`)
- **One interior content page** — most important non-homepage unique page. Priority: About > Services > first entry in main navigation. Role: `"interior"`.
- **One template instance** — `example_url` from the largest template group (by `total_count`), if any template groups exist. Role: `"template_example"`.

```json
{
  "pages": [
    { "slug": "homepage",        "url": "https://example.com/",            "role": "homepage" },
    { "slug": "about",           "url": "https://example.com/about/",      "role": "interior" },
    { "slug": "product-example", "url": "https://example.com/product/foo", "role": "template_example", "template_group": "Product Page" }
  ]
}
```

All subsequent work — Phase 2 screenshots, PSI calls, `gather-audit-data.mjs`, and downstream `/clone-website` content scraping — **reads from this file**. No phase recomputes the list.

### Step 6: Derive Business Name Into `client.json`

Read the homepage `<title>` tag from `$RESEARCH/raw/homepage.raw.html`. Strip common suffixes like "| Home", "— Official Site", "- Gallery". Set `client.json[branding][business_name]` and `branding.business_name_source = "title_tag"`. If the title is empty or unparseable, fall back to the title-cased domain and set `business_name_source = "domain_fallback"`.

### Step 7: Count Site-Wide Alt Coverage During Crawl

While the navigation crawl is still in flight (or as a second pass over `$RESEARCH/raw/<slug>.html` files), count every `<img>` tag and every `<img>` with a non-empty `alt` attribute. Aggregate into a single `site_wide_alt_coverage = { total_images, images_with_alt, coverage_pct }` object and **write it into `$RESEARCH/site-map.json` as a top-level field** — `gather-audit-data.mjs` reads it from there. (This replaces the old Phase-4 content-dir scan that `gather-audit-data.mjs` used to do.)

### Step 8: Download Site Assets (Logo + Favicon + OG)

Download the minimum set of assets the audit report needs:
- **Logo** — locate via `<img>` inside `.logo`, `#logo`, `header .navbar-brand`, `.site-logo`, or the first `<img>` inside `<header>` whose `src`/`alt` contains "logo". Download to `$IMAGES/logo.<ext>` (preserve original extension: `.png`, `.svg`, `.jpg`, `.webp`). Capture its `alt` attribute. **Never generate, draw, or synthesize a logo.** If no logo is found, leave it unset.
- **Favicon + apple-touch-icon** — download from `<link rel="icon">` / `<link rel="apple-touch-icon">` in the homepage HTML. Save to `$SEO/favicon.ico` and `$SEO/apple-touch-icon.png`.
- **OG image** — download the homepage `og:image` to `$SEO/og-image.<ext>` for the share-preview mockup in the report.

Do **not** download every image on every page here — that's a rebuild concern and belongs to `/clone-website`'s content scrape. Phase 1 only grabs the assets the audit report itself needs to render.

Update `client.json[branding][logo_path]`, `branding.logo_source`, and `assets.favicon_path`. If the logo alt text is clearly the business name and `branding.business_name_source` is currently `"domain_fallback"`, upgrade `branding.business_name` to the alt text and set `business_name_source = "logo_alt"`.

### Step 9: Fetch PageSpeed Insights For Every Audit Page

For each page in `$RESEARCH/audit-pages.json`, call the Google PSI API twice (mobile + desktop). Run in parallel where possible.

Read `PSI_API_KEY` from the repo's `.env`. If missing, **stop** and tell the user to set it — the unauthenticated endpoint's shared quota is almost always exhausted. No fallback.

```
https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=<PAGE_URL>&strategy=<mobile|desktop>&category=performance&category=accessibility&category=seo&key=$PSI_API_KEY
```

Save raw responses to `$RESEARCH/pagespeed/<slug>-<strategy>.json`. Do not parse them here — `extract-lighthouse.mjs` does that inside `gather-audit-data.mjs`.

If a PSI call fails (timeout, 500, site unreachable), write a stub JSON with `{ "error": "..." }` so the gatherer knows the page was attempted but failed. This is the **one acceptable partial state** — because a single PSI fail shouldn't kill the run, but it must be visible in downstream output.

### Step 10: Run the Audit-Data Gathering Script

Every deterministic per-page check — SEO signals, AI-crawler robots/llms.txt, Lighthouse score extraction, social/GBP link parsing, entity signals, favicon inspection, derived metrics — runs through a single script. Do **not** re-implement any of this in the SKILL prompt.

```bash
node scripts/audit/gather-audit-data.mjs $CLIENTS_DIR/<name>
```

It reads:
- `$RESEARCH/audit-pages.json` (canonical page list)
- `$RESEARCH/raw/<slug>.raw.html` (preferred) or `<slug>.html` (fallback) for per-page signal extraction
- `$RESEARCH/raw/robots.txt`, `$RESEARCH/raw/sitemap.xml` (cached, not refetched)
- `$RESEARCH/pagespeed/<slug>-<strategy>.json` (written in Step 9)
- `$RESEARCH/raw/homepage.raw.html` for social link extraction (via `extract-social-links.mjs`)
- `$RESEARCH/raw/homepage.raw.html` + about page (if any) for entity signals (via `extract-entity-signals.mjs`) — founding date, address, opening hours, `sameAs`, named founder
- `$SEO/favicon.ico`, `$SEO/apple-touch-icon.png` on disk (pure inspection)

It writes `$RESEARCH/audit-data.json` containing:
- `audited_pages[]` — per-page signals + lighthouse + entity_signals
- `robots` — AI crawler access matrix
- `llms_txt`, `llms_full_txt` — presence checks
- `social` — homepage social/GBP/directory links
- `favicon` — disk inspection result
- `derived` — headline metrics, quick wins, `site_wide_alt_coverage`

Helper scripts (runnable individually for debugging):
- `scripts/audit/extract-page-signals.mjs <html-file> <url>` — per-page SEO signals
- `scripts/audit/extract-entity-signals.mjs <html-file>` — founding date, address, hours, sameAs, founder
- `scripts/audit/extract-social-links.mjs <html-file>` — social/GBP/directory links
- `scripts/audit/analyze-robots.mjs <robots.txt>` — AI crawler matrix
- `scripts/audit/extract-lighthouse.mjs <psi.json>` — scores, CWV, opportunities, derived metrics

**Print a summary table** to the user showing unique pages, template groups, PSI scores, and quick-wins count. Phase 1 is complete — nothing fetched in Phase 2 or Phase 3 will re-do any of this work.

## Phase 2: Perceive

**Skip this phase if `--phases` was provided and `2` is not in the list.**
**Requires Phase 1 outputs:** `audit-pages.json`, `raw/homepage.raw.html`, and a populated `client.json[branding]`. If Phase 1 didn't run, fail — don't try to run Phase 1 inline.

Goal: capture screenshots of every audit page at every viewport, then use a **vision model to derive the design system from the pixels** — not from scraped CSS. Also (optionally) shoot competitor homepages for a visual comparison paragraph in the audit.

This phase **kills the old multi-layered color-scraping pipeline** (theme CSS parse + frequency sampling + WordPress-defaults filter + semantic-element sampling + cross-reference + classification). All of that is replaced by "look at the picture and tell me the palette."

### Step 0: Screenshot Pre-Flight (HARD GATE)

Before anything else in Phase 2, **prove that browser MCP can actually capture a screenshot of the live site.**

1. Navigate to the homepage at 1440px using browser MCP.
2. Attempt a full-page screenshot and save to `$SCREENSHOTS/homepage-desktop.png`.
3. Verify the file exists and is > 10KB.

**If the screenshot fails** (browser MCP not connected, navigation error, blocked by Cloudflare/bot protection, blank image, file < 10KB): **STOP Phase 2 immediately.** Report the failure and ask the user how to proceed. **Never fall back to a screenshot-less design system.**

(This is the only place in the run that uses a browser for visual capture. Phase 1's browser use — if any — was for link enumeration only.)

### Step 1: Capture All Audit-Page Screenshots

For **every page in `$RESEARCH/audit-pages.json`**, capture and save to `$SCREENSHOTS/`:

- `<slug>-desktop.png` at 1440px (full page)
- `<slug>-mobile.png` at 390px (full page)
- Plus one extra pass **only for the homepage**: `homepage-tablet.png` at 768px (for design-system perception).

**Skip-if-exists rule:** If a file already exists and is > 10KB, reuse it. This auto-preserves `homepage-desktop.png` from Step 0.

After each new capture, verify the file exists and is > 10KB. Any failure → stop Phase 2.

Expected total file count: `2 × len(audit-pages) + 1`.

### Step 2: Capture Competitor Homepages

Read `$RESEARCH/competitors.json` (written in Phase 1 Step 4.5). If `urls` is empty (`source: "none"`), skip this step entirely — the Phase 3 report's Category benchmark subsection will not render.

Otherwise, for each competitor URL (max 4):
1. Navigate to the URL at 1440px and capture `$SCREENSHOTS/competitors/<domain>-desktop.png` (full page).
2. Navigate at 390px and capture `$SCREENSHOTS/competitors/<domain>-mobile.png`.
3. Verify each screenshot > 10KB; log a warning and skip the competitor on failure — do not halt Phase 2.

Then run a **single vision LLM pass per competitor** on their desktop screenshot and produce:
- `design_language`: 1-2 sentence description of the visual style (palette, type, layout archetype)
- `does_well`: one-line "what they do well" observation (e.g., "full-bleed hero with a single CTA, no visual noise")

Write the results as `derived.competitor_design[]` into `$RESEARCH/audit-data.json` via read-modify-write:

```json
{
  "derived": {
    "competitor_design": [
      {
        "url": "https://gagosian.com",
        "domain": "gagosian.com",
        "desktop_screenshot": "$SCREENSHOTS/competitors/gagosian.com-desktop.png",
        "mobile_screenshot": "$SCREENSHOTS/competitors/gagosian.com-mobile.png",
        "design_language": "Editorial minimalism — white background, black serif wordmark, full-bleed exhibition photography, zero gradients.",
        "does_well": "Lets the artwork breathe: one image per fold, no competing CTAs."
      }
    ]
  }
}
```

Do **not** crawl competitors. Do **not** run Lighthouse. Do **not** extract their design tokens into `client.json[design]`. These shots exist only for the Phase 3 Category benchmark subsection.

### Step 3: Derive the Design System From Screenshots (Vision LLM)

Using `$SCREENSHOTS/homepage-desktop.png`, `homepage-tablet.png`, and `homepage-mobile.png` as the primary input (plus the interior + template pages as reference for non-homepage patterns), describe the design system. This is a **vision task** — look at the pixels.

Extract, in order:

1. **Color palette** — primary, secondary, accent, background, foreground, muted, border, footer_bg, footer_text, link, link_hover, button_bg, button_text, button_hover_bg. Report exact hex values. Sample from the actual pixels where possible (e.g., header background, CTA button fill).
2. **Typography** — heading font family, body font family, perceived weights, relative size hierarchy. **Cross-reference:** read `$RESEARCH/raw/homepage.raw.html` for `<link rel="stylesheet" href="...fonts.googleapis.com/css2?family=...">` entries — these are the *actually loaded* font families and should match what your eyes see. If vision disagrees with `<link>` tags, trust the `<link>` tags for the family names and your eyes for the pairing/usage.
3. **Spacing rhythm** — perceived section padding, container width, card padding, grid gap.
4. **Layout archetype** — max-width-container vs full-bleed, sidebar vs no sidebar, header height, footer column count, grid columns at desktop/tablet/mobile.
5. **Component patterns** — button shape/radius/padding, card shadow/border/radius, navbar style, input style.
6. **Decorative signatures** — border-radius scale, shadow usage (subtle vs dramatic vs none), gradient usage, transition feel.
7. **Vibe** — a single short phrase. "warm traditional", "modern minimal", "bold colorful", "editorial sophisticated", "playful indie", etc.

**Brand color cross-reference (optional, deterministic):** if a logo file exists at `client.json[branding][logo_path]`, sample the dominant non-white/non-black pixel colors from the logo — these are usually the brand's true primary + secondary. Note any disagreement with the vision-derived palette.

### Step 4: Write the Design Tree Into `client.json[design]`

**Do NOT write `research/design-system.json` — that file is deprecated.** Read `client.json`, merge the derived design tree into `client.json[design]` via read-modify-write. Preserve any fields a human may have edited (e.g., `design.vibe` set during Phase C).

`design.colors.primary/secondary/accent` and `design.typography.fonts.heading/body` must be present at those exact paths so `client-status.sh` and downstream tooling keep working unchanged.

The full `design` subtree shape:

```json
{
  "vibe": "warm traditional",
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
    "fonts": { "heading": "Playfair Display", "body": "Open Sans" },
    "google_fonts_url": "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Open+Sans:wght@300;400;600;700&display=swap",
    "sizes": {
      "h1": { "size": "42px", "weight": "700", "line_height": "1.2" },
      "h2": { "size": "32px", "weight": "700", "line_height": "1.3" },
      "body": { "size": "14px", "weight": "400", "line_height": "24px" }
    }
  },
  "spacing": {
    "section_padding_y": "50px",
    "container_max_width": "1200px",
    "container_padding_x": "20px",
    "card_padding": "10px",
    "grid_gap": "20px"
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
    "button": { "padding": "8px 18px", "border_radius": "0", "font_weight": "600", "text_transform": "uppercase" },
    "card":   { "border": "1px solid #eeeeee", "border_radius": "0", "box_shadow": "none", "padding": "10px" },
    "input":  { "border": "1px solid #dddddd", "border_radius": "4px", "padding": "10px 16px" },
    "navbar": { "height": "90px", "background": "#ffffff" }
  },
  "radius": { "none": "0", "small": "4px", "full": "9999px" },
  "shadows": { "dropdown": "0 5px 15px rgba(0,0,0,0.1)" },
  "transitions": { "default": "0.3s ease" }
}
```

**Why this subtree is powerful:** it's both (a) the source of truth the cloner reads to generate `tailwind.config.js`, and (b) the starting point for the Phase C design conversation with the client — "here's what you have today, here are three directions we could take it." Same data, two consumers.

## Phase 3: Report

**Skip this phase if `--phases` was provided and `3` is not in the list.**
**Requires Phase 1 + Phase 2 outputs.** No fetches, no browser, no re-computation — this phase reads everything and synthesizes the report. If any required input is missing, fail — don't try to generate the missing data here.

Required inputs:
- `$RESEARCH/audit-data.json` (Phase 1)
- `$RESEARCH/site-map.json` (Phase 1)
- `$RESEARCH/audit-pages.json` (Phase 1)
- `$RESEARCH/pagespeed/*.json` (Phase 1, for raw opportunities if needed)
- `$SCREENSHOTS/*.png` (Phase 2)
- `client.json[design, branding, business, assets]` (Phase 1 + Phase 2)

Goal: Generate a polished, client-facing audit report as a self-contained, styled HTML file. Written for a non-technical small business owner — no jargon, friendly professional tone.

### Business Name

Read `client.json[branding][business_name]`. It was set by Phase 1 (and possibly upgraded by Phase 2 via logo alt). If somehow null (shouldn't happen after Phase 1), fall back to the 3-step derivation (title → logo alt → title-cased domain) and write the result back to `client.json`.

### Gather Data

Read the outputs from Phase 1 and Phase 2:
- `$RESEARCH/site-map.json` — page counts, unique pages, template groups
- `$RESEARCH/audit-pages.json` — canonical list of pages to deep-dive on
- `client.json[design]` — full design tree (colors, fonts, layout, components)
- `client.json[branding]` — business name + logo path
- Screenshots from `$SCREENSHOTS/` — embed them in the report (already captured by Phase 2 for every page in `audit-pages.json`)

#### Locate Client Logo and Homepage Screenshot

1. **Client logo** — Read `client.json[branding][logo_path]`. If set, resolve it relative to the client folder and base64-encode the file for embedding in the report header. If `null`, fall back to scanning `$IMAGES/` for `logo.{png,jpg,svg,webp}`. If nothing is found, omit the logo from the report entirely — do not fabricate one.

   **DO NOT create, generate, synthesize, or draw a logo under any circumstances.** Never write a logo file, never use an SVG placeholder, never fabricate one from the business name. Setting the logo is Phase 2's job, not Phase 3's.

2. **Homepage screenshot** — Read `$SCREENSHOTS/homepage-desktop.png`. This file is guaranteed by Phase 1 Step 0's hard gate and confirmed by Phase 2's unified capture. If it's somehow missing, **fail Phase 3** rather than re-capture — its absence means a critical invariant was broken and should be diagnosed, not papered over.

3. **Client domain** — Extract from `base_url` in `site-map.json` (e.g., `www.galleryoneindia.com`). Display prominently in the report header alongside the business name.

#### Audit Pages

Read `$RESEARCH/audit-pages.json` — the canonical list was computed in Phase 1 Step 5. Use it as-is for PageSpeed, signal extraction, and report rendering. Do not recompute the list.

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

Screenshots for every page in `audit-pages.json` at both desktop (1440px) and mobile (390px) viewports already exist in `$SCREENSHOTS/` — they were captured once by Phase 2 using canonical slugs. Phase 3 **reads** these files and base64-embeds them in the report. No re-capture.

#### Run the audit-data gathering script

**Every deterministic check (per-page SEO, Lighthouse numbers, AI crawler robots.txt, llms.txt probe, derived metrics) is handled by a single permanent script — do NOT re-implement these inline.**

```bash
node scripts/audit/gather-audit-data.mjs $CLIENTS_DIR/<name>
```

Optional flag: `--pages=<url1>,<url2>,<url3>` to override which pages are audited. By default the script reads `$RESEARCH/audit-pages.json`. **Before running the gatherer, make sure the PSI files for every page in `audit-pages.json` exist** in `$RESEARCH/pagespeed/` (named `<slug>-mobile.json` / `<slug>-desktop.json`) — call PageSpeed Insights first if not.

The script short-circuits its own fetches when Phase 1 has already cached the data:
- `$RESEARCH/raw/robots.txt` — reused if present (Phase 1 writes this)
- `$RESEARCH/raw/sitemap.xml` — reused if present
- `$RESEARCH/raw/<slug>.raw.html` — reused for signal extraction if present (preferred — it's the unrendered server response, correct for SSR ratio)
- `$RESEARCH/raw/<slug>.html` — fallback if `.raw.html` is missing

This is what preserves the `--phases 3` standalone path: if `raw/` is empty, the gatherer still fetches cleanly on its own.

The gatherer also emits new fields:
- `favicon` — pure disk inspection of `$SEO/favicon.ico` and `$SEO/apple-touch-icon.png`, no network
- `social` — homepage-only extraction of social profile links, GBP/maps links, directory profiles (Yelp, JustDial, IndiaMart, etc.) and JSON-LD `sameAs` entries. See `extract-social-links.mjs`.
- `derived.site_wide_alt_coverage` — computed in Phase 1 during the navigation crawl. If null (crawl didn't collect it), the report must **not fabricate** a number.

The script writes `$RESEARCH/audit-data.json` with this shape:

```json
{
  "base_url": "https://example.com",
  "site_map_summary": { "total_pages_discovered": 218, "unique_pages": 8, "template_groups": 5 },
  "audited_pages": [
    {
      "slug": "homepage",
      "url": "https://example.com/",
      "signals": {
        "title": "...", "title_length": 10, "meta_description": "...",
        "og_title": null, "og_image": null, "canonical": null,
        "h1_count": 0, "h2_count": 4, "jsonld_types": [],
        "img_total": 17, "img_without_alt": 3,
        "ssr_ratio": 0.03, "generic_link_count": 2, "last_updated_visible": false
      },
      "lighthouse": {
        "mobile": { "scores": {...}, "cwv": {...}, "opportunities": {...}, "derived": { "today_mb": 2.21, "target_mb": 2.21, "top_savings_seconds": 0.6, "cls_conversion_drag_pct": 52 } },
        "desktop": { "scores": {...}, "cwv": {...}, "derived": { "cls_conversion_drag_pct": 56 } }
      }
    }
  ],
  "robots": {
    "present": true,
    "bots": { "GPTBot": "not_mentioned", "PerplexityBot": "not_mentioned", ... },
    "wildcard_allows": true,
    "sitemaps": ["https://example.com/sitemap.xml"]
  },
  "llms_txt": { "present": false, "status": 404, "bytes": 0 },
  "llms_full_txt": { "present": false, "status": 404 },
  "derived": {
    "pages_discovered": 218,
    "audited_pages": 1,
    "headline": {
      "today_mb": 2.21, "target_mb": 2.21, "saved_mb": 0,
      "top_savings_seconds": 0.6,
      "cls_conversion_drag_mobile": 52, "cls_conversion_drag_desktop": 56
    },
    "quick_wins_count": 10,
    "quick_wins": ["Add homepage meta description", "Add Open Graph image", ...]
  }
}
```

**The Hero Stat Strip, Numeric Findings bullets, AI Search Visibility section, and Marketing Snippets all read directly from `audit-data.json`.** No further computation is needed in the LLM — your job from here is narrative, layout, and base64-embedding the assets.

Helper scripts (all called by `gather-audit-data.mjs`, but runnable individually for debugging):
- `scripts/audit/extract-page-signals.mjs <html-file> <url>` — per-page SEO/GEO regex extraction
- `scripts/audit/analyze-robots.mjs <robots.txt>` — AI crawler access matrix for 12 bots
- `scripts/audit/extract-lighthouse.mjs <psi.json>` — scores, CWV, opportunities, derived metrics

Raw fetched HTML is cached under `$RESEARCH/raw/` (`robots.txt`, `llms.txt`, `<slug>.html` per audited page) so reruns are cheap.

**Still the LLM's responsibility** (not covered by the script):
- Selecting 2–3 pages to audit and ensuring PSI JSON files exist for them (call PSI first if needed)
- Checking entity signals on the homepage/about page (founding date, address, opening hours, `sameAs`, named founder) — read from `$RESEARCH/content/*.json`
- Counting "time to first product/artwork" clicks from the homepage nav
- Optional live Perplexity/OpenAI citation test (`PERPLEXITY_API_KEY` / `OPENAI_API_KEY` from `.env`, gracefully skip if absent)
- Synthesizing the 6–8 item AI-ready quick wins checklist (the script provides a baseline `quick_wins` list — refine it with context-specific items like "Add LocalBusiness JSON-LD", "Publish llms.txt pointing at About + Services")
- Translating every number into the plain-language "Findings" bullets

### Write the Report (HTML)

### Write the Report (HTML)

Save to `$REPORT/index.html`. This is a **self-contained HTML file** with embedded CSS — no external dependencies. It must look professional enough to share directly with a **lead** (before any clone or build has happened) AND function as marketing collateral.

**First line of `<body>` must be this exact detector marker so `/clone-website` can recognize it later:**

```html
<!-- publifai-site-audit v2 -->
```

The HTML must include, in this top-to-bottom order:

0. **Sticky top nav** — pure CSS (`position: sticky; top: 0; z-index: 10; backdrop-filter: blur(8px);`), horizontal pill row. On mobile it becomes a horizontal-scroll row (`overflow-x: auto; white-space: nowrap;`) — no hamburger. Hidden in print (`@media print { nav { display: none; } }`). Anchors: `#tldr`, `#wins`, `#improve`, `#design`, `#geo`, `#perf`, `#recommendation`. Every section must have `id="..."` AND `scroll-margin-top: 80px`.

1. **Header block** — client logo + business name + domain + "Prepared by Publifai" + date. Same as before.

2. **TL;DR (`#tldr`)** — NEW, plain English, **max 150 words**, zero jargon. Banned words: "CLS", "LCP", "render-blocking", "DOM", "viewport", "LCP", "TBT". Three paragraphs:
   - ¶1 "Where your website stands today" — one verdict sentence + one headline stat (e.g., "your homepage is 4.8 MB — about 4x heavier than it needs to be").
   - ¶2 "Biggest opportunity" — highest-leverage improvement, in the owner's language.
   - ¶3 "What we'd do in week one" — 3 concrete shipped outcomes, no tech terms.
   - **Hard constraint:** if your draft is over 150 words, cut ruthlessly before rendering.

3. **What works (`#wins`)** — NEW, 3-5 positive bullets drawn from the *same* `audit-data.json`. Examples: "JSON-LD structured data is in place on your homepage", "Mobile accessibility scores 95/100", "Your sitemap is published and healthy". Must be real findings, not fillers.

4. **What to improve (`#improve`)** — the old Numeric Findings content, reorganized under **four subheadings**:
   - **Speed & weight** — today MB, target MB, CLS-driven conversion drag callout.
   - **SEO fundamentals** — title, meta description, canonical, heading hierarchy, alt text coverage.
   - **AI search readiness (GEO)** — all 8 GEO checks + the new **Entity Completeness** row sourced from `audit-data.entity.completeness_pct` and the sub-fields (org_name, founding_date, address, phone, hours, founder_name).
   - **Trust signals** — GBP linked, social presence, directory profiles (from `audit-data.social` + `audit-data.entity`).
   - Every bullet still carries a real number.

5. **Design (`#design`)** — NEW section, three subsections:

   **5a. Your current design at a glance**
   - Homepage desktop + mobile screenshots (base64-embedded from Phase 2).
   - Color palette: rendered swatches with hex + friendly names (from `client.json[design][colors]`).
   - Typography: heading + body pairing, each rendered as a live sample at 32px / 16px.
   - Layout observations: free-text from Phase 2's vision LLM description (vibe + layout archetype).

   **5b. Category benchmark** — **render only if `audit-data.derived.competitor_design[]` is non-empty.**
   - 2-4 competitor homepage thumbnails side-by-side with the client's homepage thumbnail.
   - Under each competitor: one-line "what they do well" (`does_well` field).
   - One pattern-callout paragraph that names a shared move the competitors make and contrasts it with the client (e.g., *"All three use a full-bleed hero with a single CTA; yours uses a 4-column grid above the fold, which fragments attention."*). Write this fresh each run from the actual screenshots + design_language fields — do not hardcode.

   **5c. What we'd change** — 3-5 concrete, opinionated design moves ("drop the 4-col grid above the fold for a single full-bleed artwork carousel", "swap the uppercase nav for title case in a serif that matches your wordmark"). Anchor each with a competitor thumbnail if available, otherwise text-only.

6. **SEO & AI search (`#geo`)** — the existing GEO section, pulled out as a top-level nav-addressable section. Substance unchanged: AI crawler access table, llms.txt status, structured data scorecard, entity signals (now cross-linked with the Entity Completeness row in #improve), content extractability, heading/link quality, optional live citation test, AI-ready quick wins checklist.

7. **Performance (`#perf`)** — existing PageSpeed gauges + Core Web Vitals table + per-page deep dives + WhatsApp share preview + Google SERP preview + favicon/tap-targets. Substance unchanged, just nav-addressable.

8. **Recommendation (`#recommendation`)** — existing two-option block (Faithful Rebuild / Same Bones, New Look), unchanged.

9. **Marketing snippets** — existing, unchanged.

10. **Footer** — Publifai contact + a single line: *"Reply to the WhatsApp thread to ship this."*

The old Hero Stat Strip, "At a Glance", "Pages & Structure", and free-floating Design & Branding sections are **replaced** by the TL;DR + What works + Design structure above. Do not render them alongside.

The HTML must include, in order (legacy detail — keep as reference for subsection content only, not top-level order):

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
    - Favicon: read from `audit-data.favicon` (pure disk inspection — `favicon.ico` + `apple-touch-icon.png`). Mark as detected / missing.
    - Mobile tap target failures (from Lighthouse `tap-targets` audit, numeric)
    - **Your presence beyond your website** row — read `audit-data.social`. List each social profile found in `social.found_via_links` with a ✓. If `social.gbp_linked` is false, flag as a quick win: *"Link your Google Business Profile from your site footer — it's the single biggest trust signal for local SMBs."* List any `directory_profiles` (Yelp/JustDial/IndiaMart/etc.) found.

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

### Deploy the Audit to the Root of `<slug>.pages.dev`

Audit goes to the **root** (`/`) so we can share a clean URL with leads before any clone has run. When `/clone-website` runs later, it detects the `<!-- publifai-site-audit v2 -->` marker in `public/index.html` and moves the audit to `public/audit/index.html`, then drops a low-emphasis footer link in the cloned site.

**Steps:**

1. **Read slug** from `client.json[slug]`.
2. **Copy the report to the deploy root** — `$REPORT/index.html` → `$CLIENTS_DIR/<name>/public/index.html`. The HTML already contains the detector marker on the first line of `<body>`.
3. **Do not create a placeholder.** The audit *is* the root until clone runs.
4. **Call the publifai-level deploy script:**
   ```bash
   cd <publifai-repo-root>
   ./scripts/deploy-client.sh <client-folder>
   ```
5. **Update `client.json`:**
   - `phases.B_capture.discover.audit_report.report_deployed_url` = `https://<slug>.pages.dev/` (no `/audit/` suffix yet — clone will flip this later).

The audit is now live at `https://<slug>.pages.dev/` and shareable on WhatsApp as a lead magnet. No clone is required to share it.

## Completion

When all requested phases are done, print a summary. Only include sections for phases that were actually run. If `--phases` was used, also note which phases were skipped.

```
Site Discovery Complete: example.com
═══════════════════════════════════════
Phases run: 1, 2, 3  (or "1, 2" if --phases was used)

Extract (Phase 1):                     ← only if Phase 1 ran
  • 6 unique pages discovered, 2 template groups (47 products, 12 blog posts), 64 total
  • PageSpeed fetched for N audit pages (mobile + desktop)
  • robots.txt, llms.txt, raw HTML, entity signals, social/GBP links cached
  • Logo + favicon + OG image downloaded
  Saved → $RESEARCH/site-map.json, audit-pages.json, audit-data.json, raw/, pagespeed/
  client.json updated: branding, business.socials, assets

Perceive (Phase 2):                    ← only if Phase 2 ran
  • Screenshots captured for every audit page (desktop + mobile) + homepage tablet
  • Design system derived from pixels via vision LLM
  • Primary: #313131, Accent: #007cba · Fonts: Playfair Display / Open Sans
  Saved → $SCREENSHOTS/
  client.json updated: full design tree

Report (Phase 3):                      ← only if Phase 3 ran
  • Client-facing audit synthesized from Phase 1 + Phase 2 outputs
  • Desktop: Performance XX/100, Accessibility XX/100, SEO XX/100
  • Mobile:  Performance XX/100, Accessibility XX/100, SEO XX/100
  Saved  → $REPORT/index.html
  Live   → https://<slug>.pages.dev/   (lead-shareable; clone will later move to /audit/)

Next step: Share the audit report with the client, then run /clone-website with the same --client flag to build the site.
```

If phases were skipped, suggest the next command to run remaining phases:
```
To run remaining phases: /discover-site <url> --client <name> --phases 2,3
```

---

**Future (v2, not shipped):** Active social presence audit. Today the discover skill only detects whether a business *links to* its social profiles and Google Business Profile from the website. A future enhancement will actively look up the business by name + location on Google Places API, fetch GBP rating/review count/photo count, and probe Instagram/Facebook handles for activity. This is gated on a Places API key and a budget decision — tracked as a separate enhancement.
