# AI Website Cloner Template

<a href="https://github.com/JCodesMore/ai-website-cloner-template/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License" /></a> <a href="https://github.com/JCodesMore/ai-website-cloner-template/stargazers"><img src="https://img.shields.io/github/stars/JCodesMore/ai-website-cloner-template?style=flat" alt="Stars" /></a> <a href="https://discord.gg/hrTSX5yTpB"><img src="https://img.shields.io/discord/1400896964597383279?label=discord" alt="Discord" /></a>

A reusable template for reverse-engineering any website into **plain HTML + Tailwind CSS** using AI coding agents. No frameworks in the output — just clean, static HTML files styled with the Tailwind standalone CLI.

**Recommended: [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with Opus 4.6 for best results** — but works with a variety of AI coding agents.

## Two-Step Workflow

1. **`/discover-site <url>`** — Crawls the site structure via sitemap/navigation, extracts the design system (colors, fonts, spacing, components), and pulls content from representative pages. Produces `site-map.json`, `design-system.json`, and per-page content files.

2. **`/clone-website <url>`** — Reads the discovery output and builds pixel-perfect static HTML + Tailwind CSS pages. Inspects each section, writes component specs, and dispatches parallel builder agents to reconstruct every section.

## Demo

[![Watch the demo](docs/design-references/comparison.png)](https://youtu.be/O669pVZ_qr0)

> Click the image above to watch the full demo on YouTube.

## Quick Start

1. **Clone this repository**
   ```bash
   git clone https://github.com/JCodesMore/ai-website-cloner-template.git my-clone
   cd my-clone
   ```
2. **Install dependencies**
   ```bash
   npm install
   ```
3. **Start your AI agent** — Claude Code recommended:
   ```bash
   claude --chrome
   ```
4. **Discover the site structure** (recommended first step):
   ```
   /discover-site example.com
   ```
5. **Clone the site**:
   ```
   /clone-website https://example.com
   ```
6. **Build the output CSS**:
   ```bash
   cd output && bash build.sh
   ```

> Using a different agent? Open `AGENTS.md` for project instructions — most agents pick it up automatically.

## Supported Platforms

| Agent                                                         | Status                     |
| ------------------------------------------------------------- | -------------------------- |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | **Recommended** — Opus 4.6 |
| [Codex CLI](https://github.com/openai/codex)                  | Supported                  |
| [OpenCode](https://opencode.ai/)                              | Supported                  |
| [GitHub Copilot](https://github.com/features/copilot)         | Supported                  |
| [Cursor](https://cursor.com/)                                 | Supported                  |
| [Windsurf](https://codeium.com/windsurf)                      | Supported                  |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli)     | Supported                  |
| [Cline](https://github.com/cline/cline)                       | Supported                  |
| [Roo Code](https://github.com/RooCodeInc/Roo-Code)            | Supported                  |
| [Continue](https://continue.dev/)                              | Supported                  |
| [Amazon Q](https://aws.amazon.com/q/developer/)               | Supported                  |
| [Augment Code](https://www.augmentcode.com/)                   | Supported                  |
| [Aider](https://aider.chat/)                                   | Supported                  |

## Prerequisites

- [Node.js](https://nodejs.org/) 24+ (for the development scaffold and skill scripts)
- An AI coding agent (see [Supported Platforms](#supported-platforms))
- Browser automation MCP tool (Chrome MCP recommended) for site inspection

## Output Format

The cloner produces **plain HTML + Tailwind CSS** — no React, no Next.js, no Node.js required for the final output:

- Standalone `.html` files (one per unique page, one per template type)
- Tailwind CSS via [standalone CLI](https://tailwindcss.com/blog/standalone-cli) — no npm needed
- Minimal vanilla JS only where interactivity is required (carousels, dropdowns, etc.)
- All images, fonts, and assets downloaded locally
- Template pages use `<!-- VARIABLE: field_name -->` comment markers for fields that change per instance

## How It Works

### Phase 1: Discovery (`/discover-site`)

1. **Sitemap crawl** — fetches `sitemap.xml` / `sitemap_index.xml`, falls back to navigation crawling
2. **Page categorization** — groups URLs into unique pages vs template instances based on URL patterns
3. **Design system extraction** — colors, typography, spacing, components, decorative patterns from computed styles
4. **Content extraction** — scrapes representative pages (all unique + one per template group, max ~10 total)
5. **Template field marking** — identifies which fields are variable (change per instance) vs fixed (same on every instance)

### Phase 2: Cloning (`/clone-website`)

1. **Reconnaissance** — screenshots, interaction sweep (scroll, click, hover, responsive)
2. **Foundation** — updates fonts, colors, globals, downloads all assets
3. **Component specs** — writes detailed spec files with exact computed CSS values, states, behaviors, and content
4. **Parallel build** — dispatches builder agents in git worktrees, one per section/component
5. **Assembly & QA** — merges worktrees, wires up pages, runs visual diff against the original

### Smart Scraping

The discovery phase is designed to handle sites of any size efficiently:

- **Never scrapes more than ~10 pages** regardless of site size
- All unique pages get scraped (typically 4-6)
- One representative page per template group (typically 1-3)
- Skips authentication-required pages, pagination, search results, and feeds
- A 500-page WooCommerce site with 200 products? That's ~6 unique pages + 3-4 template types = ~10 pages scraped

## Use Cases

- **Platform migration** — rebuild a site you own from WordPress/Webflow/Squarespace into clean static HTML
- **Lost source code** — your site is live but the repo is gone, the developer left, or the stack is legacy
- **Learning** — deconstruct how production sites achieve specific layouts, animations, and responsive behavior
- **Client onboarding** — quickly replicate a client's existing site as a starting point for a redesign

## Not Intended For

- **Phishing or impersonation** — this project must not be used for deceptive purposes, impersonation, or any activity that breaks the law.
- **Passing off someone's design as your own** — logos, brand assets, and original copy belong to their owners.
- **Violating terms of service** — some sites explicitly prohibit scraping or reproduction. Check first.

## Project Structure

```
src/                           # Development scaffold (Next.js)
  app/                         # Next.js routes
  components/                  # React components
    ui/                        # shadcn/ui primitives
    icons.tsx                  # Extracted SVG icons
  lib/utils.ts                 # cn() utility
  types/                       # TypeScript interfaces
output/                        # Cloner output (plain HTML + Tailwind)
  index.html                   # Homepage
  about.html                   # One HTML file per unique page
  css/input.css                # Tailwind directives + custom CSS
  css/output.css               # Generated by Tailwind CLI
  js/main.js                   # Minimal vanilla JS
  images/                      # Downloaded images
  tailwind.config.js           # Design tokens from extraction
  build.sh                     # Tailwind CLI build command
docs/
  research/
    site-map.json              # Full site structure (from /discover-site)
    design-system.json          # Colors, fonts, spacing (from /discover-site)
    content/                   # Per-page content JSON (from /discover-site)
    components/                # Section spec files (from /clone-website)
    BEHAVIORS.md               # Interaction patterns
    PAGE_TOPOLOGY.md           # Section map
  design-references/           # Screenshots and visual references
scripts/
  sync-agent-rules.sh         # Regenerate agent instruction files
  sync-skills.mjs             # Regenerate skills for all platforms
  download-assets.mjs         # Asset download script
AGENTS.md                     # Agent instructions (single source of truth)
CLAUDE.md                     # Claude Code config (imports AGENTS.md)
```

## Commands

```bash
# Development scaffold
npm run dev        # Start dev server
npm run build      # Production build
npm run lint       # ESLint check
npm run typecheck  # TypeScript check
npm run check      # Run lint + typecheck + build

# Output site
cd output && bash build.sh   # Build Tailwind CSS for output site
```

### If using Docker

```bash
docker compose up app --build  # Build and run the app
docker compose up dev --build  # Run the app in dev mode on port 3001
```

## Updating for Other Platforms

Three source-of-truth files power all platform support. Edit the source, then run the sync script:

| What                   | Source of truth                         | Sync command                       |
| ---------------------- | --------------------------------------- | ---------------------------------- |
| Project instructions   | `AGENTS.md`                             | `bash scripts/sync-agent-rules.sh` |
| `/discover-site` skill | `.claude/skills/discover-site/SKILL.md` | `node scripts/sync-skills.mjs`     |
| `/clone-website` skill | `.claude/skills/clone-website/SKILL.md` | `node scripts/sync-skills.mjs`     |

Each script regenerates the platform-specific copies automatically. Agents that read the source files natively need no regeneration.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=JCodesMore/ai-website-cloner-template&type=Date)](https://star-history.com/#JCodesMore/ai-website-cloner-template&Date)

## License

MIT
