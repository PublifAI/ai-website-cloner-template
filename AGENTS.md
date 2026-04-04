<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Website Reverse-Engineer Template

## What This Is
A reusable template for reverse-engineering any website. Two-step workflow:
1. **`/discover-site <url> --client <name>`** — Crawls the site structure, extracts the design system, and pulls content from representative pages
2. **`/clone-website <url> --client <name>`** — Builds pixel-perfect static HTML + Tailwind CSS pages from the discovery output

Use `--client <name>` to isolate each client's data into `clients/<name>/`. Omit it for backward-compatible repo-root output.

## Output Format
The cloner outputs **plain HTML + Tailwind CSS** (no frameworks):
- Standalone `.html` files per page
- Tailwind CSS via standalone CLI (no Node.js required for the output site)
- Minimal vanilla JS only where interactivity is needed
- All assets downloaded locally

## Tech Stack (Development Environment)
- **Framework:** Next.js 16 (App Router, React 19, TypeScript strict) — used for the template scaffold only
- **UI:** shadcn/ui (Radix primitives, Tailwind CSS v4, `cn()` utility) — available during development
- **Icons:** Lucide React — available during development
- **Styling:** Tailwind CSS v4
- **Output:** Plain HTML + Tailwind CSS (standalone CLI)

## Client Output Directory

Client data lives **outside this repo**, in a shared `clients/` directory configured via `.env`:

```env
# .env (copy from .env.example)
CLIENTS_DIR=../clients    # Default: parent-level, shared across all Publifai tools
```

```
$CLIENTS_DIR/<name>/
├── research/
│   ├── site-map.json             # Full site structure
│   ├── design-system.json        # Colors, fonts, spacing
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

## Commands
- `npm run dev` — Start dev server (for development scaffold)
- `npm run build` — Production build (for development scaffold)
- `npm run lint` — ESLint check
- `npm run typecheck` — TypeScript check
- `npm run check` — Run lint + typecheck + build
- `cd output && bash build.sh` — Build Tailwind CSS for output site

## Design Principles
- **Pixel-perfect emulation** — match the target's spacing, colors, typography exactly
- **No personal aesthetic changes during emulation phase** — match 1:1 first, customize later
- **Real content** — use actual text and assets from the target site, not placeholders
- **Beauty-first** — every pixel matters
- **Smart scraping** — never scrape more than ~10 pages; unique pages + 1 per template group

## MOST IMPORTANT NOTES
- When launching Claude Code agent teams, ALWAYS have each teammate work in their own worktree branch and merge everyone's work at the end, resolving any merge conflicts smartly since you are basically serving the orchestrator role and have full context to our goals, work given, work achieved, and desired outcomes.
- After editing `AGENTS.md`, run `bash scripts/sync-agent-rules.sh` to regenerate platform-specific instruction files.
- After editing any skill in `.claude/skills/*/SKILL.md`, run `node scripts/sync-skills.mjs` to regenerate skills for all platforms.
