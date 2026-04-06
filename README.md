# AI Website Cloner — Publifai Fork

Fork of [JCodesMore/ai-website-cloner-template](https://github.com/JCodesMore/ai-website-cloner-template), adapted for Publifai's client onboarding pipeline.

## Why We Use This

Publifai builds websites for small businesses via WhatsApp. When a client already has a website (Case 2 in our process), we need to capture their existing site's content, structure, and design before building the new one. This cloner powers **Phase B: Capture** in our site building process (Phases A–F, see publifai-docs).

Instead of asking clients to manually provide every piece of content, we scrape their existing site and use the output to:
- Pre-fill business info (content, images, contact details)
- Show the client what we captured for confirmation
- Feed the design system into our build step
- Generate a client-facing site audit report shared via WhatsApp

See [`publifai-docs/product/site-building-process.md`](https://github.com/PublifAI/publifai-docs/blob/main/product/site-building-process.md) for the full onboarding flow.

## How It Fits Into Publifai

```
Client shares URL on WhatsApp
  → AI agent calls scrape_site(url)
  → This cloner runs /discover-site
  → Outputs: site map, design system, content extraction
  → Agent summarizes findings, sends to client
  → Agent generates site audit report
  → Feeds into Phases C-D of site building process
```

The three outputs map directly to our process:

| Output | File | Feeds into |
|--------|------|------------|
| Site map | `research/site-map.json` | Phase C1 — agree on page structure with client |
| Design system | `research/design-system.json` | Phase C2 — agree on design direction |
| Page content | `research/content/*.json` | Phase D — generate the new site without re-asking for content |

## Two-Step Workflow

1. **`/discover-site <url> --client <name>`** — Crawls site structure via sitemap/navigation, extracts design system (colors, fonts, spacing), pulls content from representative pages. Produces `site-map.json`, `design-system.json`, audit report, and per-page content files.

2. **`/clone-website <url> --client <name>`** — Reads discovery output and builds pixel-perfect static HTML + Tailwind CSS pages. Inspects each section, writes component specs, dispatches parallel builder agents.

`--client <name>` isolates each client's data into a shared clients directory (configured via `.env`). This lets us run the cloner for multiple clients without conflicts, and the output is accessible to other Publifai tools.

### Running specific discovery phases

`/discover-site` has 4 phases that can be run selectively with `--phases`:

| Phase | Output | Description |
|-------|--------|-------------|
| 1 | `site-map.json` | Sitemap/navigation crawl, page categorization |
| 2 | `design-system.json` | Colors, fonts, spacing, screenshots, asset download |
| 3 | `site-audit.md` | Client-facing audit report (requires phases 1+2 output) |
| 4 | `content/*.json` | Per-page content extraction (requires phase 1 output) |

```bash
# Run only site map discovery
/discover-site galleryoneindia.com --client galleryoneindia --phases 1

# Run site map + design system
/discover-site galleryoneindia.com --client galleryoneindia --phases 1,2

# Generate audit report later (phases 1+2 must have run previously)
/discover-site galleryoneindia.com --client galleryoneindia --phases 3

# Run all phases (default — same as omitting --phases)
/discover-site galleryoneindia.com --client galleryoneindia
```

Phases 3 and 4 depend on earlier outputs. If the required files don't exist, the phase is skipped with a warning.

## Quick Start

```bash
# Clone
git clone https://github.com/publifai/ai-website-cloner-template.git
cd ai-website-cloner-template
npm install

# Configure clients directory (defaults to ../clients)
cp .env.example .env
# Edit .env if you need a different path

# Start Claude Code with browser access
claude --chrome

# Discover a client's existing site
/discover-site galleryoneindia.com --client galleryoneindia

# Clone the site (optional — only if we want a full rebuild as starting point)
/clone-website https://galleryoneindia.com --client galleryoneindia
```

## Configuration

Client data is stored **outside this repo** in a shared directory. Set the path in `.env`:

```env
# Default: ../clients (parent-level, shared across all Publifai tools)
CLIENTS_DIR=../clients
```

## Client Output Structure

```
$CLIENTS_DIR/<name>/
├── research/
│   ├── site-map.json             # Full site structure + template categorization
│   ├── design-system.json        # Colors, fonts, spacing, component patterns
│   ├── screenshots/              # Page screenshots from recon
│   ├── content/                  # Per-page content JSON
│   └── components/               # Section spec files
├── report/
│   └── site-audit.md             # Client-facing audit report
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

# Output site (path depends on CLIENTS_DIR in .env)
cd ../clients/<name>/output && bash build.sh   # Build Tailwind CSS for output site
```

## Keeping in Sync with Upstream

```bash
git fetch upstream
git merge upstream/main
# Resolve any conflicts with our modifications
```

## License

MIT — see upstream repo for full license.
