#!/usr/bin/env python3
"""Build the Publifai client-facing audit report.

Usage:
  python3 scripts/audit/build-report.py <client-dir>

Reads:
  <client-dir>/client.json
  <client-dir>/research/audit-data.json
  <client-dir>/research/report-narrative.json   (LLM-written narrative overlay)
  <client-dir>/research/screenshots/*.png
  <client-dir>/assets/images/logo.png

Writes:
  <client-dir>/report/index.html
  <client-dir>/public/index.html   (same content — deploy root for lead magnet)

Design principle: this script owns ALL structural HTML, CSS, gauge rendering,
table generation, and screenshot embedding. The LLM's job is only to write
report-narrative.json — a small JSON file with TL;DR paragraphs, "what works"
bullets, "what to improve" bullets per bucket, design observations, and
marketing snippets. Everything else is computed deterministically from
audit-data.json + client.json + screenshots on disk.

This file is generic — there is NOTHING client-specific in here.
"""
import base64, json, pathlib, datetime, mimetypes, sys, html as _html

import re as _re
_ALLOWED_TAGS = ('strong', 'em', 'code', 'b', 'i')
def esc(x):
    """HTML-escape, then unescape a small safelist of inline tags so narrative
    bullets can still use <strong>/<em>/<code> for emphasis without letting
    a stray <h1> blow up the layout."""
    if x is None: return ''
    s = _html.escape(str(x), quote=False)
    for t in _ALLOWED_TAGS:
        s = s.replace(f'&lt;{t}&gt;', f'<{t}>').replace(f'&lt;/{t}&gt;', f'</{t}>')
    return s

if len(sys.argv) < 2:
    print("Usage: build-report.py <client-dir>", file=sys.stderr)
    sys.exit(1)

ROOT = pathlib.Path(sys.argv[1]).resolve()
if not (ROOT/'client.json').exists():
    print(f"Error: {ROOT}/client.json not found", file=sys.stderr)
    sys.exit(1)

DATA = json.loads((ROOT/'research/audit-data.json').read_text())
CLIENT = json.loads((ROOT/'client.json').read_text())
DESIGN = CLIENT.get('design', {})
NARR_PATH = ROOT/'research/report-narrative.json'
if not NARR_PATH.exists():
    print(f"Error: {NARR_PATH} not found. Generate it before building the report.", file=sys.stderr)
    sys.exit(1)
NARR = json.loads(NARR_PATH.read_text())

BIZ_NAME = (CLIENT.get('branding', {}) or {}).get('business_name') or CLIENT.get('name') or CLIENT.get('slug')
DOMAIN = CLIENT.get('domains', {}).get('custom') or (CLIENT.get('existing_site', {}) or {}).get('url', '').replace('https://','').replace('http://','').strip('/')
SUBDOMAIN = (CLIENT.get('domains', {}) or {}).get('subdomain') or f"{CLIENT.get('slug','')}.publifai.in"
PUBLIC_URL = f"https://{SUBDOMAIN}/"
TODAY = datetime.date.today().strftime("%B %Y")
OG_DESC = f"Publifai's website review for {BIZ_NAME} — speed, SEO, AI search readiness, and a week-one rebuild plan."

# Resolve the logo source (if any) and the matching og image filename. We
# preserve the original extension so /og.png isn't actually a JPEG.
LOGO_SRC = None
for _ext in ('png', 'jpg', 'jpeg', 'webp', 'svg'):
    _cand = ROOT/f'assets/images/logo.{_ext}'
    if _cand.exists():
        LOGO_SRC = _cand
        break
OG_FILENAME = f"og.{LOGO_SRC.suffix.lstrip('.')}" if LOGO_SRC else "og.png"
OG_URL = f"{PUBLIC_URL}{OG_FILENAME}"

PUBLIC = ROOT/'public'
ASSETS = PUBLIC/'assets'
ASSETS.mkdir(parents=True, exist_ok=True)

def asset(rel, dest_name=None):
    """Copy ROOT/rel into public/assets/<dest_name> and return the relative
    URL the HTML should use. Returns None if the source doesn't exist or is
    too small to be a real image."""
    p = ROOT/rel
    if not p.exists() or p.stat().st_size < 100:
        return None
    name = dest_name or p.name
    out = ASSETS/name
    out.write_bytes(p.read_bytes())
    return f"assets/{name}"

LOGO = None
if LOGO_SRC:
    LOGO = asset(str(LOGO_SRC.relative_to(ROOT)), f"logo.{LOGO_SRC.suffix.lstrip('.')}")

PAGES = {p['slug']: p for p in DATA['audited_pages']}
HEAD = DATA['derived']['headline']
ROBOTS = DATA.get('robots', {})
SOCIAL = DATA.get('social', {})
COMPS = []
for c in DATA['derived'].get('competitor_design', []) or []:
    sd = ROOT/c['desktop_screenshot']
    if sd.exists() and sd.stat().st_size > 50000:
        c['_d'] = asset(c['desktop_screenshot'], f"competitor-{c['domain']}-desktop.png")
        COMPS.append(c)

def gauge(score, label):
    score = score or 0
    color = '#0cce6b' if score>=90 else ('#ffa400' if score>=50 else '#ff4e42')
    return f'<div class="gauge"><div class="circ" style="--c:{color};--p:{score}"><span>{score}</span></div><div class="g-label">{label}</div></div>'

def cwv_row(label, m, d):
    def pill(v, score):
        s = score or 0
        cls = 'pass' if s>=0.9 else ('warn' if s>=0.5 else 'fail')
        return f'<span class="pill {cls}">{v}</span>'
    return f'<tr><td>{label}</td><td>{pill(m["displayValue"], m.get("score"))}</td><td>{pill(d["displayValue"], d.get("score"))}</td></tr>'

def page_screenshots(slug):
    d = asset(f'research/screenshots/{slug}-desktop.png', f'{slug}-desktop.png')
    m = asset(f'research/screenshots/{slug}-mobile.png', f'{slug}-mobile.png')
    parts = []
    if d: parts.append(f'<figure><img src="{d}" alt="{slug} desktop" loading="lazy"/><figcaption>Desktop · 1440px</figcaption></figure>')
    if m: parts.append(f'<figure><img src="{m}" alt="{slug} mobile" loading="lazy"/><figcaption>Mobile · 390px</figcaption></figure>')
    return ''.join(parts)

def page_block(slug, name):
    if slug not in PAGES: return ''
    p = PAGES[slug]; s = p['signals']; lh = p['lighthouse']
    mob, dsk = lh['mobile'], lh['desktop']
    ms, ds = mob['scores'], dsk['scores']
    title = s.get('title') or '(empty)'
    meta = s.get('meta_description') or ''
    cwv = ''.join([
        cwv_row('Largest Contentful Paint (main image appears)', mob['cwv']['lcp'], dsk['cwv']['lcp']),
        cwv_row('Cumulative Layout Shift (page jumping around)', mob['cwv']['cls'], dsk['cwv']['cls']),
        cwv_row('Total Blocking Time (frozen interactions)', mob['cwv']['tbt'], dsk['cwv']['tbt']),
        cwv_row('Speed Index (perceived load time)', mob['cwv']['si'], dsk['cwv']['si']),
    ])
    seo_rows = []
    def row(k, v, st):
        seo_rows.append(f'<tr><td>{k}</td><td>{v}</td><td><span class="pill {st}">{ "PASS" if st=="pass" else "FIX" }</span></td></tr>')
    row('Title tag', f'"{title}" ({s.get("title_length")} chars)', 'fail' if (s.get("title_length") or 0) < 25 else 'pass')
    row('Meta description', meta or '<em>missing</em>', 'fail' if not meta else 'pass')
    row('Open Graph image', s.get('og_image') or '<em>missing — WhatsApp/social previews break</em>', 'fail' if not s.get('og_image') else 'pass')
    row('H1 heading', f'{s.get("h1_count")} found', 'fail' if not s.get('h1_count') else 'pass')
    row('Structured data (JSON-LD)', ', '.join(s.get('jsonld_types') or []) or '<em>none</em>', 'fail' if not s.get('jsonld_types') else 'pass')
    row('Images missing alt text', f'{s.get("img_without_alt")} of {s.get("img_total")} images', 'fail' if (s.get("img_without_alt") or 0) > 0 else 'pass')
    drag = mob['derived'].get('cls_conversion_drag_pct', 0)
    cls_call = ''
    if drag:
        cls_call = (
            f'<p class="callout">Google Web.dev research shows every 0.1 of CLS above 0.1 correlates with a ~7% drop in conversions. '
            f'This page\'s mobile CLS of <strong>{mob["cwv"]["cls"]["numericValue"]:.2f}</strong> implies roughly '
            f'<strong>{drag}% conversion drag</strong> on phones.</p>'
        )
    return f'''
    <section id="page-{slug}" class="page-audit">
      <h2>{name} — Deep Dive</h2>
      <div class="page-screenshots">{page_screenshots(slug)}</div>
      <h3>Speed &amp; performance on this page</h3>
      <div class="gauges">
        <div class="gauge-col"><div class="strat">Mobile</div>{gauge(ms['performance'],'Performance')}{gauge(ms['accessibility'],'Accessibility')}{gauge(ms['seo'],'SEO')}</div>
        <div class="gauge-col"><div class="strat">Desktop</div>{gauge(ds['performance'],'Performance')}{gauge(ds['accessibility'],'Accessibility')}{gauge(ds['seo'],'SEO')}</div>
      </div>
      <p class="note">Why mobile and desktop can disagree: when CLS (the page jumping around as it loads) is the dominant issue, the larger desktop viewport amplifies it.</p>
      <table class="cwv">
        <thead><tr><th>What we measure</th><th>Mobile</th><th>Desktop</th></tr></thead>
        <tbody>{cwv}</tbody>
      </table>
      {cls_call}
      <h3>Search visibility checks</h3>
      <table class="seo">
        <thead><tr><th>Check</th><th>What we found</th><th>Status</th></tr></thead>
        <tbody>{''.join(seo_rows)}</tbody>
      </table>
    </section>
    '''

# Color swatches
SW = (DESIGN.get('colors') or {})
swatch_keys = [('primary','primary'),('accent','accent'),('background','background'),('foreground','foreground'),('footer bg','footer_bg'),('button','button_bg')]
swatches_html = ''.join(
    f'<div class="sw"><div class="dot" style="background:{SW.get(key,"#ccc")};border:1px solid #ccc"></div><div class="sw-meta"><div class="sw-name">{name}</div><div class="sw-hex">{SW.get(key,"")}</div></div></div>'
    for name, key in swatch_keys if SW.get(key)
)

# AI bots
AI_BOTS = {
    'GPTBot': "ChatGPT's training crawler — controls whether ChatGPT can learn about you",
    'OAI-SearchBot': "ChatGPT Search crawler — needed to be cited in ChatGPT search results",
    'PerplexityBot': "Perplexity's main crawler — needed to be cited in Perplexity answers",
    'ClaudeBot': "Anthropic Claude's crawler",
    'Google-Extended': "Controls whether Google's Gemini can train on your content",
    'Applebot-Extended': "Apple Intelligence training crawler",
    'CCBot': "Common Crawl — feeds many AI training datasets",
    'Bytespider': "ByteDance / TikTok's crawler",
}
robots_rows = ''.join(
    f'<tr><td><code>{bot}</code></td><td><span class="pill {"pass" if status=="allowed" else ("warn" if status=="not_mentioned" else "fail")}">{status.replace("_"," ")}</span></td><td>{AI_BOTS[bot]}</td></tr>'
    for bot, status in (ROBOTS.get('bots') or {}).items() if bot in AI_BOTS
)

# Competitor cards
peers_section_html = ''
if COMPS:
    your_home = asset('research/screenshots/homepage-desktop.png', 'homepage-desktop.png')
    your_card = f'<div class="ccard you"><img src="{your_home}" alt="{DOMAIN}"/><div class="cmeta"><div class="cdom">{DOMAIN} (you)</div><div class="cdo">{NARR.get("design",{}).get("your_card_one_liner","")}</div></div></div>'
    cards = ''.join(
        f'<div class="ccard"><img src="{c["_d"]}" alt="{c["domain"]}"/><div class="cmeta"><div class="cdom">{c["domain"]}</div><div class="cdo"><strong>What they do well:</strong> {c["does_well"]}</div></div></div>'
        for c in COMPS
    )
    peers_section_html = f'''
<section id="peers">
  <h2>How peers in your category present themselves</h2>
  <div class="comp-grid">{your_card}{cards}</div>
  <p class="pattern-callout">{NARR.get("design",{}).get("pattern_callout","")}</p>
</section>
'''

def ul(items):
    return '<ul>' + ''.join(f'<li>{esc(x)}</li>' for x in (items or [])) + '</ul>'

def improve_card(icon, title, items, accent_color):
    if not items: return ''
    lis = ''.join(f'<li>{esc(x)}</li>' for x in items)
    n = len(items)
    label = f'{n} issue' if n == 1 else f'{n} issues'
    return f'''
    <div class="imp-card" style="--accent:{accent_color}">
      <div class="imp-head">
        <span class="imp-icon">{icon}</span>
        <h3>{title}</h3>
        <span class="imp-count">{label}</span>
      </div>
      <ul>{lis}</ul>
    </div>'''

def seo_per_page_table():
    rows = []
    for p in NARR.get('pages_to_render', []):
        slug = p if isinstance(p, str) else p['slug']
        name = p if isinstance(p, str) else p.get('display_name', slug)
        if slug not in PAGES: continue
        s = PAGES[slug]['signals']
        def cell(ok):
            cls = 'pass' if ok else 'fail'
            label = '✓' if ok else '✗'
            return f'<td><span class="pill {cls}">{label}</span></td>'
        rows.append(
            f'<tr><td><strong>{name}</strong></td>'
            f'{cell(bool(s.get("title")) and 25 <= (s.get("title_length") or 0) <= 65)}'
            f'{cell(bool(s.get("meta_description")))}'
            f'{cell(bool(s.get("og_image")))}'
            f'{cell((s.get("h1_count") or 0) == 1)}'
            f'{cell(bool(s.get("canonical")))}'
            f'</tr>'
        )
    return ''.join(rows)

def wins_ul(items):
    return '<ul class="wins-list">' + ''.join(f'<li>{esc(x)}</li>' for x in (items or [])) + '</ul>'

# JSON-LD scorecard rows from narrative (since not all sites need same schema types)
def jsonld_rows():
    rows = NARR.get('geo', {}).get('jsonld_scorecard', [])
    return ''.join(
        f'<tr><td><code>{esc(r["type"])}</code></td><td><span class="pill {r.get("status","fail")}">{esc(r.get("label",r.get("status","")))}</span></td><td>{esc(r.get("why",""))}</td></tr>'
        for r in rows
    )

def quick_wins_li():
    items = NARR.get('geo', {}).get('quick_wins', [])
    out = []
    for i in items:
        if isinstance(i, dict):
            out.append(f'<li>✓ <strong>{i.get("time","")}</strong> — {i.get("text","")}</li>')
        else:
            out.append(f'<li>✓ {i}</li>')
    return ''.join(out)

# TL;DR + improvement bullets all come from narrative JSON
TLDR = NARR.get('tldr', {})
WINS = NARR.get('wins', [])
IMPROVE = NARR.get('improve', {})
DESIGN_NARR = NARR.get('design', {})
GEO = NARR.get('geo', {})
RECO = NARR.get('recommendation', {})
for _k in ('option_a','option_b'):
    if isinstance(RECO.get(_k), str):
        RECO[_k] = {'title': 'Faithful Rebuild' if _k=='option_a' else 'Same Bones, New Look', 'body': RECO[_k], 'week_one': ''}
SNIPPETS = NARR.get('snippets', {})

# Auto-generate the "share with client" WhatsApp message if the narrative
# doesn't supply one. This is the message Publifai pastes into WhatsApp to
# hand the audit over to the client — separate from the marketing snippets.
if not SNIPPETS.get('client_share'):
    _owner = ((CLIENT.get('owner') or {}).get('name') or '').split(' ')[0] or 'there'
    SNIPPETS['client_share'] = (
        f"Hi {_owner}, I took a fresh look at {DOMAIN} and put together a quick review — "
        f"what's working, what we'd improve, and what we'd ship in week one:\n\n{PUBLIC_URL}\n\n"
        f"All of this is what we'll fix when we build your new website."
    )

_jsonld_scorecard = NARR.get('geo', {}).get('jsonld_scorecard', []) or []
discoverable = (
    not any(v == 'blocked' for v in (ROBOTS.get('bots') or {}).values())
    and any(r.get('status') == 'pass' for r in _jsonld_scorecard)
)
ai_verdict = (
    "Yes — your site is reachable, but you've given AI engines almost nothing to anchor to."
    if discoverable else
    "Not really — at least one major AI crawler can't reach you, and there's no structured data to anchor a citation."
)

stats_html = ''.join(
    f'<div class="stat"><div class="big">{s["value"]}</div><div class="label">{s["label"]}</div></div>'
    for s in NARR.get('hero_stats', [])
)

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{BIZ_NAME} — Website Review by Publifai</title>
<meta name="description" content="{OG_DESC}">
<link rel="canonical" href="{PUBLIC_URL}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Publifai">
<meta property="og:title" content="{BIZ_NAME} — Website Review">
<meta property="og:description" content="{OG_DESC}">
<meta property="og:url" content="{PUBLIC_URL}">
<meta property="og:image" content="{OG_URL}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{BIZ_NAME} — Website Review">
<meta name="twitter:description" content="{OG_DESC}">
<meta name="twitter:image" content="{OG_URL}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box}}
  html{{scroll-behavior:smooth}}
  body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#181818;background:#f4f4f5;margin:0;line-height:1.6;font-size:15px;-webkit-font-smoothing:antialiased}}
  .wrap{{max-width:920px;margin:0 auto;padding:32px 40px 96px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,0.04),0 8px 40px rgba(0,0,0,0.06)}}
  h1{{font-size:34px;margin:0 0 6px;letter-spacing:-0.8px;font-weight:800;line-height:1.15}}
  h2{{font-size:26px;margin:64px 0 18px;letter-spacing:-0.5px;font-weight:700;line-height:1.2}}
  h2::before{{content:"";display:block;width:32px;height:3px;background:#181818;border-radius:2px;margin-bottom:14px}}
  h3{{font-size:17px;margin:30px 0 10px;color:#181818;font-weight:600;letter-spacing:-0.2px}}
  p{{margin:0 0 14px;color:#3a3a3a}}
  a{{color:#0d6efd;text-decoration:none}}
  a:hover{{text-decoration:underline}}
  nav.sticky{{position:sticky;top:0;z-index:10;background:rgba(24,24,24,0.95);backdrop-filter:saturate(180%) blur(12px);-webkit-backdrop-filter:saturate(180%) blur(12px);border-bottom:1px solid rgba(255,255,255,0.08);margin:-32px -40px 28px;padding:14px 40px;overflow-x:auto;white-space:nowrap}}
  nav.sticky a{{display:inline-block;padding:7px 15px;margin-right:6px;border-radius:999px;background:rgba(255,255,255,0.08);color:#f4f4f5;text-decoration:none;font-size:13px;font-weight:500;transition:background 0.15s ease}}
  nav.sticky a:hover{{background:#fff;color:#181818;text-decoration:none}}
  section{{scroll-margin-top:88px}}
  header.report-head{{display:flex;align-items:center;gap:20px;padding-bottom:24px;border-bottom:1px solid #ececec;margin-bottom:10px}}
  header.report-head img{{height:54px}}
  .domain{{color:#666;font-size:14px;margin:2px 0 0}}
  .subtitle{{color:#999;font-size:12px;margin:6px 0 0;text-transform:uppercase;letter-spacing:0.6px;font-weight:500}}
  .stat-strip{{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:14px;margin:28px 0 10px}}
  .stat{{background:#f7f7f8;padding:22px 20px;border-radius:12px;text-align:left;border:1px solid #ececec}}
  .stat:first-child{{background:linear-gradient(135deg,#181818 0%,#2a2a2a 100%);color:#fff;border-color:#181818}}
  .stat:first-child .big{{color:#fff}}
  .stat:first-child .label{{color:rgba(255,255,255,0.6)}}
  .stat .big{{font-size:38px;font-weight:800;color:#181818;letter-spacing:-1.5px;line-height:1}}
  .stat .label{{font-size:11px;color:#888;margin-top:8px;text-transform:uppercase;letter-spacing:0.6px;font-weight:600}}
  .tldr p{{font-size:16px;color:#2a2a2a;line-height:1.65}}
  .wins-list{{list-style:none;padding:0;margin:14px 0}}
  .wins-list li{{padding:12px 16px;background:#f0faf3;border-left:2px solid #34a853;margin-bottom:8px;border-radius:6px;font-size:14.5px}}
  .improve-grid h3{{margin-top:28px;font-size:11px;text-transform:uppercase;letter-spacing:0.8px;color:#999;font-weight:700;border-bottom:1px solid #ececec;padding-bottom:6px}}
  .improve-grid ul{{margin:10px 0 22px;padding-left:20px}}
  .improve-grid li{{margin-bottom:8px;color:#3a3a3a}}
  .improve-grid strong{{color:#c43e10;font-weight:700}}
  .imp-grid{{display:grid;grid-template-columns:1fr;gap:14px;margin:16px 0 8px}}
  .imp-card{{background:#fff;border:1px solid #ececec;border-left:4px solid var(--accent,#c43e10);border-radius:10px;padding:16px 18px 6px;box-shadow:0 1px 2px rgba(0,0,0,0.03)}}
  .imp-head{{display:flex;align-items:center;gap:10px;margin-bottom:4px}}
  .imp-head h3{{margin:0;font-size:15px;font-weight:700;color:#181818;text-transform:none;letter-spacing:0;border:none;padding:0;flex:1}}
  .imp-icon{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;background:color-mix(in srgb,var(--accent) 14%,#fff);font-size:15px;line-height:1}}
  .imp-count{{display:inline-block;padding:3px 10px;border-radius:999px;background:var(--accent);color:#fff;font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;white-space:nowrap}}
  .imp-card ul{{margin:8px 0 10px;padding-left:20px}}
  .imp-card li{{margin-bottom:7px;color:#3a3a3a;font-size:14px}}
  .imp-card strong{{color:var(--accent);font-weight:700}}
  @media (min-width:760px){{.imp-grid{{grid-template-columns:1fr 1fr}}}}
  .swatches{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0}}
  .sw{{display:flex;gap:12px;align-items:center;background:#f7f7f8;padding:11px 14px;border-radius:8px;border:1px solid #ececec}}
  .sw .dot{{width:34px;height:34px;border-radius:50%;flex-shrink:0;box-shadow:inset 0 0 0 1px rgba(0,0,0,0.08)}}
  .sw-name{{font-size:11px;font-weight:700;text-transform:uppercase;color:#888;letter-spacing:0.5px}}
  .sw-hex{{font-family:'SF Mono',Menlo,monospace;font-size:13px;color:#181818;font-weight:500}}
  .comp-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:16px 0}}
  .ccard{{background:#fff;border-radius:8px;overflow:hidden;border:1px solid #ececec;transition:transform 0.15s ease}}
  .ccard.you{{border:2px solid #c43e10;box-shadow:0 4px 12px rgba(196,62,16,0.1)}}
  .ccard img{{width:100%;display:block;height:160px;object-fit:cover;object-position:top}}
  .cmeta{{padding:12px 14px;font-size:12.5px}}
  .cdom{{font-weight:700;color:#181818;margin-bottom:4px;font-size:13px}}
  .cdo{{color:#666;line-height:1.45}}
  .pattern-callout{{background:#fffbeb;border-left:2px solid #f59e0b;padding:14px 18px;margin:16px 0;font-size:14px;border-radius:6px;color:#3a3a3a}}
  .gauges{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0}}
  .gauge-col{{background:#f7f7f8;padding:22px 18px;border-radius:12px;border:1px solid #ececec}}
  .gauge-col .strat{{font-weight:700;font-size:11px;text-transform:uppercase;color:#888;margin-bottom:18px;text-align:center;letter-spacing:0.6px}}
  .gauge{{display:inline-block;text-align:center;width:33%}}
  .circ{{--p:0;--c:#ccc;width:74px;height:74px;border-radius:50%;background:conic-gradient(var(--c) calc(var(--p)*1%),#e8e8e8 0);display:flex;align-items:center;justify-content:center;margin:0 auto;position:relative}}
  .circ::before{{content:"";position:absolute;width:58px;height:58px;border-radius:50%;background:#f7f7f8}}
  .circ span{{position:relative;font-weight:800;font-size:18px;color:#181818;letter-spacing:-0.5px}}
  .g-label{{font-size:10.5px;color:#888;margin-top:10px;text-transform:uppercase;letter-spacing:0.5px;font-weight:600}}
  table{{width:100%;border-collapse:collapse;margin:14px 0;font-size:14px;border:1px solid #ececec;border-radius:8px;overflow:hidden}}
  th,td{{text-align:left;padding:12px 14px;vertical-align:top}}
  tbody tr:nth-child(odd){{background:#fafafa}}
  tbody tr{{border-top:1px solid #ececec}}
  th{{font-size:11px;text-transform:uppercase;color:#666;background:#f4f4f5;font-weight:700;letter-spacing:0.5px;border-bottom:2px solid #ececec}}
  .pill{{display:inline-block;padding:4px 11px;border-radius:999px;font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px}}
  .pill.pass{{background:#e6f7ed;color:#1e7c3d}}
  .pill.warn{{background:#fef3e2;color:#c2410c}}
  .pill.fail{{background:#fde8e8;color:#b91c1c}}
  .callout{{background:#fef2f2;border-left:2px solid #b91c1c;padding:14px 18px;border-radius:6px;font-size:14px;color:#3a3a3a;margin:14px 0}}
  .note{{font-size:13px;color:#888;font-style:italic;margin-top:-2px}}
  .page-screenshots{{display:grid;grid-template-columns:1fr 280px;gap:18px;margin:16px 0;align-items:start}}
  .page-screenshots img{{width:100%;border:1px solid #ececec;border-radius:6px;display:block}}
  .page-screenshots figure{{margin:0}}
  .page-screenshots figure:last-child img{{max-height:560px;object-fit:contain;object-position:top;background:#f7f7f8}}
  .page-screenshots figcaption{{font-size:11px;color:#999;text-align:center;margin-top:6px;text-transform:uppercase;letter-spacing:0.5px;font-weight:600}}
  .reco{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:18px 0}}
  .reco-card{{padding:22px;border-radius:12px;border:1px solid #ececec;background:#f7f7f8}}
  .reco-card.recommended{{border:2px solid #1e7c3d;background:#f0faf3}}
  .reco-card h3{{margin:0 0 10px;color:#181818;font-size:18px}}
  .reco-card .badge{{display:inline-block;background:#1e7c3d;color:#fff;font-size:9.5px;padding:4px 10px;border-radius:999px;text-transform:uppercase;letter-spacing:0.6px;font-weight:700;margin-bottom:10px}}
  .week-one{{background:#fff;padding:12px 16px;border-radius:6px;margin-top:12px;font-size:13px;color:#3a3a3a;border:1px solid #ececec}}
  footer{{margin-top:64px;padding-top:24px;border-top:1px solid #ececec;font-size:12px;color:#999;text-align:center;line-height:1.7}}
  .opportunity-frame{{background:#eff6ff;border-left:2px solid #1d4ed8;padding:14px 18px;border-radius:6px;font-size:14px;margin-top:20px;color:#1e3a8a}}
  .perf-subnav{{position:sticky;top:60px;z-index:9;display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 26px;padding:12px 16px;background:rgba(247,247,248,0.95);backdrop-filter:blur(8px);border:1px solid #ececec;border-radius:10px}}
  .perf-subnav .lbl{{font-size:10.5px;text-transform:uppercase;letter-spacing:0.6px;color:#888;font-weight:700;margin-right:8px;align-self:center}}
  .perf-subnav a{{display:inline-block;padding:6px 13px;border-radius:999px;background:#fff;border:1px solid #ddd;color:#3a3a3a;text-decoration:none;font-size:12.5px;font-weight:500;transition:all 0.15s ease}}
  .perf-subnav a:hover{{background:#181818;color:#fff;border-color:#181818;text-decoration:none}}
  code{{background:#f4f4f5;padding:2px 6px;border-radius:4px;font-size:13px;font-family:'SF Mono',Menlo,monospace;color:#c43e10}}
  @media print{{nav.sticky,.perf-subnav{{display:none}}body{{background:#fff}}.wrap{{box-shadow:none;max-width:100%;padding:0}}}}
  @media (max-width:680px){{.wrap{{padding:20px 18px 60px}}nav.sticky{{margin:-20px -18px 20px;padding:12px 18px}}.stat-strip,.swatches,.comp-grid,.reco,.page-screenshots,.gauges{{grid-template-columns:1fr}}.page-screenshots figure:last-child img{{max-height:none}}h1{{font-size:26px}}h2{{font-size:22px}}}}
</style>
</head>
<body>
<!-- publifai-site-audit v2 -->
<div class="wrap">

<nav class="sticky">
  <a href="#summary">Summary</a>
  <a href="#design">Design</a>
  {'<a href="#peers">Peers</a>' if COMPS else ''}
  <a href="#geo">SEO &amp; AI search</a>
  <a href="#perf">Performance</a>
  <a href="#recommendation">Recommendation</a>
</nav>

<header class="report-head">
  {f'<img src="{LOGO}" alt="{BIZ_NAME} logo">' if LOGO else ''}
  <div>
    <h1>{BIZ_NAME} — Website Review</h1>
    <p class="domain">{DOMAIN}</p>
    <p class="subtitle">Prepared by Publifai · {TODAY}</p>
  </div>
</header>

<section id="summary" class="tldr improve-grid">
  <h2>The summary</h2>

  <h3>Short version</h3>
  {''.join(f'<p>{p}</p>' for p in TLDR.get('paragraphs', []))}

  <div class="stat-strip">{stats_html}</div>

  <h3>What's already working</h3>
  {wins_ul(WINS)}

  <h3>What to improve</h3>
  <div class="imp-grid">
    {improve_card('⚡', 'Speed &amp; weight', IMPROVE.get('speed'), '#dc2626')}
    {improve_card('🔍', 'SEO fundamentals', IMPROVE.get('seo'), '#d97706')}
    {improve_card('🤖', 'AI search readiness', IMPROVE.get('geo'), '#1d4ed8')}
    {improve_card('🛡', 'Trust signals', IMPROVE.get('trust'), '#7c3aed')}
  </div>
</section>

<section id="design">
  <h2>Design</h2>
  <h3>Your current design at a glance</h3>
  <div class="page-screenshots">{page_screenshots('homepage')}</div>
  <p><strong>Vibe:</strong> {DESIGN.get('vibe','')}.</p>
  <p>{DESIGN_NARR.get('layout_observations','')}</p>
  <h3>Color palette</h3>
  <div class="swatches">{swatches_html}</div>
  <h3>What we'd change</h3>
  {ul(DESIGN_NARR.get('changes'))}
</section>

{peers_section_html}

<section id="geo">
  <h2>SEO &amp; AI search</h2>
  <p class="lead">{GEO.get('lead','')}</p>

  <h3>SEO fundamentals — per-page tag check</h3>
  <table>
    <thead><tr><th>Page</th><th>Title</th><th>Meta desc</th><th>OG image</th><th>H1</th><th>Canonical</th></tr></thead>
    <tbody>{seo_per_page_table()}</tbody>
  </table>

  <h3>AI discoverability — can ChatGPT find you?</h3>
  <p class="opportunity-frame"><strong>{ai_verdict}</strong></p>

  <h4 style="margin:18px 0 8px;color:#888;font-size:13px;text-transform:uppercase;letter-spacing:0.5px">AI crawler access</h4>
  <table>
    <thead><tr><th>Crawler</th><th>Status</th><th>What it means</th></tr></thead>
    <tbody>{robots_rows}</tbody>
  </table>

  <h4 style="margin:18px 0 8px;color:#888;font-size:13px;text-transform:uppercase;letter-spacing:0.5px">llms.txt</h4>
  <p>{GEO.get('llms_txt_paragraph','')}</p>

  <h4 style="margin:18px 0 8px;color:#888;font-size:13px;text-transform:uppercase;letter-spacing:0.5px">Structured data scorecard</h4>
  <table>
    <thead><tr><th>Schema type</th><th>Status</th><th>Why it matters</th></tr></thead>
    <tbody>{jsonld_rows()}</tbody>
  </table>

  <h4 style="margin:18px 0 8px;color:#888;font-size:13px;text-transform:uppercase;letter-spacing:0.5px">AI-ready quick wins</h4>
  <ul>{quick_wins_li()}</ul>

  <p class="opportunity-frame" style="margin-top:18px"><strong>{GEO.get('opportunity_frame','')}</strong></p>
</section>

<section id="perf">
  <h2>Performance — page by page</h2>
  <div class="perf-subnav">
    <span class="lbl">Jump to page</span>
    {''.join(f'<a href="#page-{(p if isinstance(p,str) else p["slug"])}">{(p.replace("-"," ").title() if isinstance(p,str) else p.get("display_name", p["slug"].replace("-"," ").title()))}</a>' for p in NARR.get('pages_to_render', []))}
  </div>
  {''.join(page_block(p, p.replace('-',' ').title()) if isinstance(p,str) else page_block(p['slug'], p.get('display_name', p['slug'].replace('-',' ').title())) for p in NARR.get('pages_to_render', []))}
</section>

<section id="recommendation">
  <h2>Our recommendation</h2>
  <div class="reco">
    <div class="reco-card recommended">
      <div class="badge">Recommended</div>
      <h3>{RECO.get('option_a',{}).get('title','')}</h3>
      <p>{RECO.get('option_a',{}).get('body','')}</p>
      {f'<div class="week-one"><strong>Week one we\'d ship:</strong> {RECO.get("option_a",{}).get("week_one","")}</div>' if RECO.get('option_a',{}).get('week_one') else ''}
    </div>
    <div class="reco-card">
      <h3>{RECO.get('option_b',{}).get('title','')}</h3>
      <p>{RECO.get('option_b',{}).get('body','')}</p>
    </div>
  </div>
  <p style="margin-top:14px"><em>{RECO.get('closer','')}</em></p>
</section>

<section id="next-steps">
  <h2>What happens next</h2>
  <ol>
    <li>We agree on the page structure together (5–8 pages for week one).</li>
    <li>We lock in the design direction — colours, type, hero treatment.</li>
    <li>We build the site and send you a preview link.</li>
    <li>You tell us what to change — as many rounds as you need.</li>
    <li>When you're happy, we go live on <code>{DOMAIN}</code>.</li>
  </ol>
</section>

<footer>
  <p>This report was generated by Publifai's automated audit pipeline on {TODAY}, then reviewed by hand.<br>
  Reply to the WhatsApp thread to ship this. · <a href="https://publifai.in" target="_blank" rel="noopener">publifai.in</a></p>
</footer>

</div>
</body>
</html>
'''

# Single HTML output, lives at public/index.html. All images are referenced
# from public/assets/ via relative URLs — keeps page weight under ~50KB
# instead of 15MB of base64. Deploy-client.sh ships the public/ folder as the
# pages.dev root. /clone-website later moves this to /audit/.
pub = ROOT/'public/index.html'
pub.parent.mkdir(parents=True, exist_ok=True)
pub.write_text(HTML)
print(f"wrote {pub} · {len(HTML):,} bytes")

# Mirror to report/index.html as a tiny redirect so anything still pointing
# at the old location (dashboards, bookmarks) lands on the live deployed copy.
report_out = ROOT/'report/index.html'
report_out.parent.mkdir(parents=True, exist_ok=True)
report_out.write_text(
    f'<!doctype html><meta charset="utf-8"><title>Redirecting…</title>'
    f'<meta http-equiv="refresh" content="0; url={PUBLIC_URL}">'
    f'<link rel="canonical" href="{PUBLIC_URL}">'
    f'<p>Redirecting to <a href="{PUBLIC_URL}">{PUBLIC_URL}</a>…</p>'
)
print(f"wrote {report_out} (redirect stub)")

# Copy the client logo to public/og.png so WhatsApp/Twitter link previews
# resolve. data: URIs in og:image are NOT followed by social crawlers — they
# need a real http(s) URL. Logo is a placeholder until we add a generated
# share card; it still beats a broken preview.
if LOGO_SRC:
    og_out = ROOT/f'public/{OG_FILENAME}'
    og_out.write_bytes(LOGO_SRC.read_bytes())
    print(f"wrote {og_out} (from {LOGO_SRC.name})")

# Write internal-only marketing snippets to a separate file the local
# dashboard reads. Never shipped to the client-facing report.
snip_out = ROOT/'report/snippets.json'
snip_out.write_text(json.dumps(SNIPPETS, indent=2))
print(f"wrote {snip_out}")
