<!-- AUTO-GENERATED from .claude/skills/discover-site/SKILL.md — do not edit directly.
     Run `node scripts/sync-skills.mjs` to regenerate. -->


# Discover Site

You are about to discover and document the full structure of **the target URL provided by the user**.

This skill produces THREE outputs that feed into the site-building process:
1. **Site map** — every page categorized as unique or template instance
2. **Design system** — colors, fonts, spacing, component patterns
3. **Content extraction** — text, images, and structure from representative pages

## Pre-Flight

1. **Browser automation is required.** Check for available browser MCP tools (Chrome MCP, Playwright MCP, Browserbase MCP, Puppeteer MCP, etc.). Use whichever is available — if multiple exist, prefer Chrome MCP. If none are detected, ask the user which browser tool they have and how to connect it.
2. Parse `the target URL provided by the user` as a base URL. Normalize it (add `https://` if missing, strip trailing paths to get the domain root). Verify the site is accessible.
3. Create output directories:
   - `docs/research/`
   - `docs/research/content/`
   - `docs/design-references/`
   - `public/images/`

## Phase 1: Site Map Discovery (Output 1)

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

Save to `docs/research/site-map.json`:

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

Goal: Extract the visual design language from 2-3 key pages.

### Pages to Inspect

- The homepage (always)
- 1-2 other pages with distinct layouts (e.g., a content page and a listing/gallery page)
- Do NOT inspect every page — the design system should be derivable from a few pages

### What to Extract

Use browser MCP to navigate to each page and run JavaScript extraction:

**Colors** — Run `getComputedStyle()` across key elements to find:
- Background colors (page, sections, cards, buttons, footer)
- Text colors (headings, body, muted, links, link hover)
- Border colors
- Accent/brand colors
- Determine which is primary, secondary, accent

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
- Save to `docs/design-references/`

### Download Global Assets

1. Find and download all images referenced on scraped pages to `public/images/`
2. Download favicon, apple-touch-icon, OG images to `public/images/seo/`
3. Note any external fonts (Google Fonts URLs, self-hosted font files)

Write and run a `scripts/download-assets.mjs` script for batch downloading (4 concurrent).

### Output Design System

Save to `docs/research/design-system.json`:

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

## Phase 3: Content Extraction (Output 3)

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
   - Download each to `public/images/`

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

Save one file per scraped page in `docs/research/content/`:

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

When all 3 phases are done, print a summary:

```
Site Discovery Complete: example.com
═══════════════════════════════════════

Site Map:
  • 6 unique pages discovered
  • 2 template groups (47 products, 12 blog posts)
  • 64 total pages on site
  Saved → docs/research/site-map.json

Design System:
  • Primary: #313131, Accent: #007cba
  • Fonts: Playfair Display (headings), Open Sans (body)
  • 16 assets downloaded to public/
  Saved → docs/research/design-system.json

Content Extracted:
  • 8 pages scraped (6 unique + 2 templates)
  • 24 images downloaded
  Saved → docs/research/content/

Next step: Review the outputs, then run /clone-website to build the site.
```
