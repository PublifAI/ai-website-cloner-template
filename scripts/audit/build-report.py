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
import base64, json, pathlib, datetime, mimetypes, sys

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
TODAY = datetime.date.today().strftime("%B %Y")

def b64(rel):
    p = ROOT/rel
    if not p.exists() or p.stat().st_size < 100: return None
    mime = mimetypes.guess_type(str(p))[0] or 'image/png'
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"

LOGO = b64('assets/images/logo.png') or b64('assets/images/logo.svg') or b64('assets/images/logo.jpg') or b64('assets/images/logo.webp')

PAGES = {p['slug']: p for p in DATA['audited_pages']}
HEAD = DATA['derived']['headline']
ROBOTS = DATA.get('robots', {})
SOCIAL = DATA.get('social', {})
COMPS = []
for c in DATA['derived'].get('competitor_design', []) or []:
    sd = ROOT/c['desktop_screenshot']
    if sd.exists() and sd.stat().st_size > 50000:
        c['_d'] = b64(c['desktop_screenshot'])
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
    d = b64(f'research/screenshots/{slug}-desktop.png')
    m = b64(f'research/screenshots/{slug}-mobile.png')
    parts = []
    if d: parts.append(f'<figure><img src="{d}" alt="{slug} desktop"/><figcaption>Desktop · 1440px</figcaption></figure>')
    if m: parts.append(f'<figure><img src="{m}" alt="{slug} mobile"/><figcaption>Mobile · 390px</figcaption></figure>')
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
comp_html = ''
if COMPS:
    your_home = b64('research/screenshots/homepage-desktop.png')
    your_card = f'<div class="ccard you"><img src="{your_home}" alt="{DOMAIN}"/><div class="cmeta"><div class="cdom">{DOMAIN} (you)</div><div class="cdo">{NARR.get("design",{}).get("your_card_one_liner","")}</div></div></div>'
    cards = ''.join(
        f'<div class="ccard"><img src="{c["_d"]}" alt="{c["domain"]}"/><div class="cmeta"><div class="cdom">{c["domain"]}</div><div class="cdo"><strong>What they do well:</strong> {c["does_well"]}</div></div></div>'
        for c in COMPS
    )
    comp_html = f'''
    <h3>How peer sites in your category present themselves</h3>
    <div class="comp-grid">{your_card}{cards}</div>
    <p class="pattern-callout">{NARR.get("design",{}).get("pattern_callout","")}</p>
    '''

def ul(items):
    return '<ul>' + ''.join(f'<li>{x}</li>' for x in (items or [])) + '</ul>'

def wins_ul(items):
    return '<ul class="wins-list">' + ''.join(f'<li>{x}</li>' for x in (items or [])) + '</ul>'

# JSON-LD scorecard rows from narrative (since not all sites need same schema types)
def jsonld_rows():
    rows = NARR.get('geo', {}).get('jsonld_scorecard', [])
    return ''.join(
        f'<tr><td><code>{r["type"]}</code></td><td><span class="pill {r.get("status","fail")}">{r.get("label",r.get("status",""))}</span></td><td>{r.get("why","")}</td></tr>'
        for r in rows
    )

def quick_wins_li():
    items = NARR.get('geo', {}).get('quick_wins', [])
    return ''.join(f'<li>✓ <strong>{i["time"]}</strong> — {i["text"]}</li>' for i in items)

# TL;DR + improvement bullets all come from narrative JSON
TLDR = NARR.get('tldr', {})
WINS = NARR.get('wins', [])
IMPROVE = NARR.get('improve', {})
DESIGN_NARR = NARR.get('design', {})
GEO = NARR.get('geo', {})
RECO = NARR.get('recommendation', {})
SNIPPETS = NARR.get('snippets', {})

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
<style>
  *{{box-sizing:border-box}}
  html{{scroll-behavior:smooth}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;color:#1a1a1a;background:#fafafa;margin:0;line-height:1.55;font-size:15px}}
  .wrap{{max-width:880px;margin:0 auto;padding:24px 24px 80px;background:#fff;box-shadow:0 0 40px rgba(0,0,0,0.04)}}
  h1{{font-size:30px;margin:0 0 6px;letter-spacing:-0.5px}}
  h2{{font-size:22px;margin:48px 0 14px;border-bottom:2px solid #1a1a1a;padding-bottom:6px;letter-spacing:-0.3px}}
  h3{{font-size:17px;margin:28px 0 10px;color:#444}}
  p{{margin:0 0 12px}}
  a{{color:#0d6efd}}
  nav.sticky{{position:sticky;top:0;z-index:10;background:rgba(255,255,255,0.92);backdrop-filter:blur(8px);border-bottom:1px solid #eee;margin:-24px -24px 24px;padding:12px 24px;overflow-x:auto;white-space:nowrap}}
  nav.sticky a{{display:inline-block;padding:6px 14px;margin-right:6px;border-radius:999px;background:#f0f0f0;color:#333;text-decoration:none;font-size:13px;font-weight:500}}
  nav.sticky a:hover{{background:#1a1a1a;color:#fff}}
  section{{scroll-margin-top:80px}}
  header.report-head{{display:flex;align-items:center;gap:18px;padding-bottom:18px;border-bottom:1px solid #eee;margin-bottom:8px}}
  header.report-head img{{height:50px}}
  .domain{{color:#666;font-size:14px;margin:0}}
  .subtitle{{color:#888;font-size:13px;margin:4px 0 0}}
  .stat-strip{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 0 8px}}
  .stat{{background:#f6f6f6;padding:18px;border-radius:8px;text-align:center}}
  .stat .big{{font-size:32px;font-weight:700;color:#1a1a1a;letter-spacing:-1px}}
  .stat .label{{font-size:12px;color:#666;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px}}
  .tldr p{{font-size:15.5px}}
  .wins-list{{list-style:none;padding:0}}
  .wins-list li{{padding:10px 14px;background:#e8f5e9;border-left:3px solid #2e7d32;margin-bottom:8px;border-radius:4px}}
  .improve-grid h3{{margin-top:24px;font-size:15px;text-transform:uppercase;letter-spacing:0.5px;color:#888}}
  .improve-grid ul{{margin:0 0 18px;padding-left:18px}}
  .improve-grid li{{margin-bottom:6px}}
  .improve-grid strong{{color:#c43e10}}
  .swatches{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0}}
  .sw{{display:flex;gap:10px;align-items:center;background:#fafafa;padding:10px;border-radius:6px}}
  .sw .dot{{width:32px;height:32px;border-radius:50%}}
  .sw-name{{font-size:12px;font-weight:600;text-transform:uppercase;color:#666}}
  .sw-hex{{font-family:Menlo,monospace;font-size:13px;color:#333}}
  .type-sample h4{{font-size:13px;color:#888;text-transform:uppercase;margin:14px 0 4px}}
  .comp-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:16px 0}}
  .ccard{{background:#fafafa;border-radius:6px;overflow:hidden;border:1px solid #eee}}
  .ccard.you{{border:2px solid #c43e10}}
  .ccard img{{width:100%;display:block;height:160px;object-fit:cover;object-position:top}}
  .cmeta{{padding:10px 12px;font-size:12px}}
  .cdom{{font-weight:600;color:#1a1a1a;margin-bottom:4px}}
  .cdo{{color:#555;line-height:1.4}}
  .pattern-callout{{background:#fff8e1;border-left:3px solid #f9a825;padding:14px 18px;margin:14px 0;font-size:14px;border-radius:4px}}
  .gauges{{display:flex;gap:24px;flex-wrap:wrap;margin:14px 0}}
  .gauge-col{{flex:1;min-width:260px;background:#fafafa;padding:16px;border-radius:8px}}
  .gauge-col .strat{{font-weight:700;font-size:13px;text-transform:uppercase;color:#666;margin-bottom:10px;text-align:center}}
  .gauge{{display:inline-block;text-align:center;width:33%}}
  .circ{{--p:0;--c:#ccc;width:62px;height:62px;border-radius:50%;background:conic-gradient(var(--c) calc(var(--p)*1%),#eee 0);display:flex;align-items:center;justify-content:center;margin:0 auto;position:relative}}
  .circ::before{{content:"";position:absolute;width:48px;height:48px;border-radius:50%;background:#fafafa}}
  .circ span{{position:relative;font-weight:700;font-size:16px;color:#222}}
  .g-label{{font-size:11px;color:#666;margin-top:6px;text-transform:uppercase;letter-spacing:0.3px}}
  table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px}}
  th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid #eee;vertical-align:top}}
  th{{font-size:12px;text-transform:uppercase;color:#888;background:#fafafa}}
  .pill{{display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:600;text-transform:uppercase}}
  .pill.pass{{background:#e8f5e9;color:#2e7d32}}
  .pill.warn{{background:#fff3e0;color:#e65100}}
  .pill.fail{{background:#ffebee;color:#c62828}}
  .callout{{background:#ffebee;border-left:3px solid #c62828;padding:12px 16px;border-radius:4px;font-size:14px}}
  .note{{font-size:13px;color:#666;font-style:italic;margin-top:-4px}}
  .page-screenshots{{display:grid;grid-template-columns:2fr 1fr;gap:14px;margin:14px 0}}
  .page-screenshots img{{width:100%;border:1px solid #e0e0e0;border-radius:4px}}
  .page-screenshots figcaption{{font-size:12px;color:#888;text-align:center;margin-top:4px}}
  .reco{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:16px 0}}
  .reco-card{{padding:18px;border-radius:8px;border:1px solid #eee;background:#fafafa}}
  .reco-card.recommended{{border:2px solid #2e7d32;background:#f1f8e9}}
  .reco-card h3{{margin:0 0 8px;color:#1a1a1a}}
  .reco-card .badge{{display:inline-block;background:#2e7d32;color:#fff;font-size:10px;padding:3px 8px;border-radius:999px;text-transform:uppercase;letter-spacing:0.5px;font-weight:700;margin-bottom:8px}}
  .week-one{{background:#fff;padding:10px 14px;border-radius:4px;margin-top:10px;font-size:13px;color:#444}}
  .snippets{{background:#fafafa;border-radius:8px;padding:18px;margin-top:30px;border:1px dashed #ccc}}
  .snippets h2{{font-size:14px;text-transform:uppercase;letter-spacing:0.5px;border:none;color:#666;margin:0 0 12px}}
  .snippet{{margin-bottom:14px}}
  .snippet-label{{font-size:11px;font-weight:700;text-transform:uppercase;color:#888;margin-bottom:4px}}
  .snippet-body{{background:#fff;padding:10px 12px;border-radius:4px;font-size:13px;border:1px solid #eee}}
  footer{{margin-top:50px;padding-top:20px;border-top:1px solid #eee;font-size:12px;color:#888;text-align:center}}
  .opportunity-frame{{background:#e3f2fd;border-left:3px solid #1976d2;padding:14px 18px;border-radius:4px;font-size:14px;margin-top:18px}}
  @media print{{nav.sticky{{display:none}}body{{background:#fff}}.wrap{{box-shadow:none;max-width:100%}}}}
  @media (max-width:680px){{.stat-strip,.swatches,.comp-grid,.reco,.page-screenshots{{grid-template-columns:1fr}}.gauges{{flex-direction:column}}}}
</style>
</head>
<body>
<!-- publifai-site-audit v2 -->
<div class="wrap">

<nav class="sticky">
  <a href="#tldr">TL;DR</a>
  <a href="#wins">What works</a>
  <a href="#improve">What to improve</a>
  <a href="#design">Design</a>
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

<section id="tldr" class="tldr">
  <h2>TL;DR</h2>
  {''.join(f'<p>{p}</p>' for p in TLDR.get('paragraphs', []))}
</section>

<div class="stat-strip">{stats_html}</div>

<section id="wins">
  <h2>What's already working</h2>
  {wins_ul(WINS)}
</section>

<section id="improve" class="improve-grid">
  <h2>What to improve</h2>
  <h3>Speed &amp; weight</h3>{ul(IMPROVE.get('speed'))}
  <h3>SEO fundamentals</h3>{ul(IMPROVE.get('seo'))}
  <h3>AI search readiness (GEO)</h3>{ul(IMPROVE.get('geo'))}
  <h3>Trust signals</h3>{ul(IMPROVE.get('trust'))}
</section>

<section id="design">
  <h2>Design</h2>
  <h3>Your current design at a glance</h3>
  <div class="page-screenshots">{page_screenshots('homepage')}</div>
  <p><strong>Vibe:</strong> {DESIGN.get('vibe','')}.</p>
  <p>{DESIGN_NARR.get('layout_observations','')}</p>
  <h4 style="margin:18px 0 8px;color:#888;font-size:13px;text-transform:uppercase">Current palette</h4>
  <div class="swatches">{swatches_html}</div>
  {comp_html}
  <h3>What we'd change</h3>
  {ul(DESIGN_NARR.get('changes'))}
</section>

<section id="geo">
  <h2>SEO &amp; AI search visibility</h2>
  <p class="lead">{GEO.get('lead','')}</p>

  <h3>AI crawler access</h3>
  <table>
    <thead><tr><th>Crawler</th><th>Status</th><th>What it means</th></tr></thead>
    <tbody>{robots_rows}</tbody>
  </table>

  <h3>llms.txt</h3>
  <p>{GEO.get('llms_txt_paragraph','')}</p>

  <h3>Structured data scorecard</h3>
  <table>
    <thead><tr><th>Schema type</th><th>Status</th><th>Why it matters</th></tr></thead>
    <tbody>{jsonld_rows()}</tbody>
  </table>

  <h3>AI-ready quick wins checklist</h3>
  <ul>{quick_wins_li()}</ul>

  <p class="opportunity-frame"><strong>{GEO.get('opportunity_frame','')}</strong></p>
</section>

<section id="perf">
  <h2>Performance — page by page</h2>
  {''.join(page_block(p['slug'], p.get('display_name', p['slug'].replace('-',' ').title())) for p in NARR.get('pages_to_render', []))}
</section>

<section id="recommendation">
  <h2>Our recommendation</h2>
  <div class="reco">
    <div class="reco-card recommended">
      <div class="badge">Recommended</div>
      <h3>{RECO.get('option_a',{}).get('title','')}</h3>
      <p>{RECO.get('option_a',{}).get('body','')}</p>
      <div class="week-one"><strong>Week one we'd ship:</strong> {RECO.get('option_a',{}).get('week_one','')}</div>
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
  Reply to the WhatsApp thread to ship this. · publifai.in</p>
</footer>

</div>
</body>
</html>
'''

out = ROOT/'report/index.html'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(HTML)
print(f"wrote {out} · {len(HTML):,} bytes")

# Also drop a copy at public/index.html so deploy-client.sh ships it as the
# pages.dev root (lead-magnet). /clone-website later moves this to /audit/.
pub = ROOT/'public/index.html'
pub.parent.mkdir(parents=True, exist_ok=True)
pub.write_text(HTML)
print(f"wrote {pub}")

# Write internal-only marketing snippets to a separate file the local
# dashboard reads. Never shipped to the client-facing report.
snip_out = ROOT/'report/snippets.json'
snip_out.write_text(json.dumps(SNIPPETS, indent=2))
print(f"wrote {snip_out}")
