# AI Website Cloner — Publifai Fork

Fork of [JCodesMore/ai-website-cloner-template](https://github.com/JCodesMore/ai-website-cloner-template), adapted for Publifai's client onboarding pipeline.

## Why We Use This

Publifai builds websites for small businesses via WhatsApp. When a client already has a website (Case 2 in our process), we need to capture their existing site's content, structure, and design before building the new one. This cloner handles **Step 0: Capture Existing Site** — the first step in our site building process.

Instead of asking clients to manually provide every piece of content, we scrape their existing site and use the output to:
- Pre-fill business info (content, images, contact details)
- Show the client what we captured for confirmation
- Feed the design system into our build step
- Generate a client-facing site audit report shared via WhatsApp

See [`publifai-docs/product/site-building-process.md`](https://github.com/publifai/publifai-docs) for the full onboarding flow.

## How It Fits Into Publifai

```
Client shares URL on WhatsApp
  → AI agent calls scrape_site(url)
  → This cloner runs /discover-site
  → Outputs: site map, design system, content extraction
  → Agent summarizes findings, sends to client
  → Agent generates site audit report
  → Feeds into Steps 1-4 of site building process
```

The three outputs map directly to our process:

| Output | File | Feeds into |
|--------|------|------------|
| Site map | `research/site-map.json` | Step 2 — agree on page structure with client |
| Design system | `research/design-system.json` | Step 3 — agree on design direction |
| Page content | `research/content/*.json` | Step 4 — generate the new site without re-asking for content |

## Two-Step Workflow

1. **`/discover-site <url> --client <name>`** — Crawls site structure via sitemap/navigation, extracts design system (colors, fonts, spacing), pulls content from representative pages. Produces `site-map.json`, `design-system.json`, and per-page content files.

2. **`/clone-website <url> --client <name>`** — Reads discovery output and builds pixel-perfect static HTML + Tailwind CSS pages. Inspects each section, writes component specs, dispatches parallel builder agents.

`--client <name>` isolates each client's data into `clients/<name>/`. This lets us run the cloner for multiple clients without conflicts.

## Quick Start

```bash
# Clone (will be forked to publifai org)
git clone https://github.com/publifai/ai-website-cloner-template.git
cd ai-website-cloner-template
npm install

# Start Claude Code with browser access
claude --chrome

# Discover a client's existing site
/discover-site galleryoneindia.com --client galleryoneindia

# Clone the site (optional — only if we want a full rebuild as starting point)
/clone-website https://galleryoneindia.com --client galleryoneindia

# Build output CSS
cd clients/galleryoneindia/output && bash build.sh
```

## Client Output Structure

```
clients/<name>/
├── research/
│   ├── site-map.json             # Full site structure + template categorization
│   ├── design-system.json        # Colors, fonts, spacing, component patterns
│   ├── screenshots/              # Page screenshots from recon
│   ├── content/                  # Per-page content JSON
│   └── components/               # Section spec files
├── assets/
│   ├── images/                   # Downloaded from source site
│   ├── videos/
│   └── seo/                      # Favicon, OG images
├── scripts/                      # Download scripts for this client
└── output/                       # Generated HTML+Tailwind site
    ├── index.html
    ├── about.html
    ├── css/
    ├── js/
    ├── images/
    ├── tailwind.config.js
    └── build.sh
```

## Smart Scraping Rules

- **Never scrapes more than ~10 pages** regardless of site size
- All unique pages get scraped (typically 4-6)
- One representative page per template group (typically 1-3)
- Skips authentication-required pages, pagination, search results
- A 500-page site with 200 products = ~6 unique pages + 3-4 template types = ~10 pages scraped

## Output Format

Plain HTML + Tailwind CSS — no React, no Next.js, no Node.js in the final output:
- Standalone `.html` files (one per unique page, one per template type)
- Tailwind CSS via [standalone CLI](https://tailwindcss.com/blog/standalone-cli)
- Minimal vanilla JS only where interactivity is needed
- All images, fonts, and assets downloaded locally
- Template pages use `<!-- VARIABLE: field_name -->` markers for per-instance fields

This matches Publifai's stack: plain HTML + Tailwind CSS, compiled with standalone CLI on the Mac Mini, deployed via `wrangler pages deploy` to Cloudflare Pages.

## Prerequisites

- [Node.js](https://nodejs.org/) 24+
- An AI coding agent ([Claude Code](https://docs.anthropic.com/en/docs/claude-code) with Opus 4.6 recommended)
- Browser automation MCP tool (Chrome MCP recommended)

## Commands

```bash
# Development scaffold
npm run dev        # Start dev server
npm run build      # Production build
npm run lint       # ESLint check
npm run typecheck  # TypeScript check
npm run check      # Run lint + typecheck + build

# Output site
cd clients/<name>/output && bash build.sh   # Build Tailwind CSS for output site
```

## Keeping in Sync with Upstream

```bash
git fetch upstream
git merge upstream/main
# Resolve any conflicts with our modifications
```

## License

MIT — see upstream repo for full license.
