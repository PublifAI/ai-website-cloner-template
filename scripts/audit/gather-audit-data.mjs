#!/usr/bin/env node
// Orchestrator: gather all deterministic data needed for the Phase 3 audit report.
//
// Usage:
//   node gather-audit-data.mjs <client-dir> [--pages url1,url2,url3]
//
// Reads:
//   <client-dir>/research/site-map.json          (required — for base_url, page counts)
//   <client-dir>/research/pagespeed/*.json       (required — PSI responses per page+strategy)
//
// Fetches (cached):
//   <base_url>/robots.txt                         → <client-dir>/research/raw/robots.txt
//   <base_url>/llms.txt                           → <client-dir>/research/raw/llms.txt (if present)
//   <page-url> for each audited page              → <client-dir>/research/raw/<slug>.html
//
// Writes:
//   <client-dir>/research/audit-data.json
//
// Page selection: if --pages is not passed, uses the first PSI file set as a hint
// plus any files matching `pagespeed-*-mobile.json` / `homepage-mobile.json`.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const args = process.argv.slice(2);
const clientDir = args.find((a) => !a.startsWith('--'));
if (!clientDir) {
  console.error('Usage: gather-audit-data.mjs <client-dir> [--pages url1,url2]');
  process.exit(1);
}
const pagesFlag = args.find((a) => a.startsWith('--pages='));
const pagesOverride = pagesFlag ? pagesFlag.slice('--pages='.length).split(',') : null;

const RESEARCH = path.join(clientDir, 'research');
const PSI_DIR = path.join(RESEARCH, 'pagespeed');
const RAW_DIR = path.join(RESEARCH, 'raw');
const ASSETS_SEO = path.join(clientDir, 'assets', 'seo');
fs.mkdirSync(RAW_DIR, { recursive: true });

// 1. Load site-map.json
const siteMapPath = path.join(RESEARCH, 'site-map.json');
if (!fs.existsSync(siteMapPath)) {
  console.error(`Missing ${siteMapPath}. Run Phase 1 first.`);
  process.exit(1);
}
const siteMap = JSON.parse(fs.readFileSync(siteMapPath, 'utf8'));
const baseUrl = siteMap.base_url.replace(/\/$/, '');

// 2. Determine audited pages. Prefer audit-pages.json (canonical list written by Phase 1).
const auditPagesPath = path.join(RESEARCH, 'audit-pages.json');
let canonicalAuditPages = null;
if (fs.existsSync(auditPagesPath)) {
  try {
    canonicalAuditPages = JSON.parse(fs.readFileSync(auditPagesPath, 'utf8')).pages || null;
  } catch {
    canonicalAuditPages = null;
  }
}

// If override provided, use it. Otherwise use audit-pages.json, fall back to PSI file names.
const psiFiles = fs.existsSync(PSI_DIR) ? fs.readdirSync(PSI_DIR).filter((f) => f.endsWith('.json')) : [];
const pageSlugs = new Set();
for (const f of psiFiles) {
  const m = f.match(/^(.+?)-(mobile|desktop)\.json$/);
  if (m) pageSlugs.add(m[1]);
}

// Map slug → URL. homepage is always baseUrl/. Other slugs: look up in site-map unique_pages by label-ish.
const slugToUrl = (slug) => {
  if (slug === 'homepage' || slug === 'home') return baseUrl + '/';
  // Try to find a matching unique page
  const hit = (siteMap.unique_pages || []).find((p) => {
    const s = p.url.replace(/^\/|\/$/g, '').replace(/\//g, '-').toLowerCase();
    return s === slug || s.includes(slug);
  });
  if (hit) return baseUrl + hit.url;
  // Try template groups
  const tg = (siteMap.template_groups || []).find((t) =>
    (t.example_url || '').toLowerCase().includes(slug),
  );
  if (tg) return baseUrl + tg.example_url;
  return null;
};

let auditedPages;
if (pagesOverride) {
  auditedPages = pagesOverride.map((url, i) => ({
    slug: i === 0 ? 'homepage' : `page-${i}`,
    url,
  }));
} else if (canonicalAuditPages) {
  auditedPages = canonicalAuditPages.map((p) => ({
    slug: p.slug,
    url: p.url.startsWith('http') ? p.url : baseUrl + p.url,
  }));
} else {
  auditedPages = [...pageSlugs]
    .map((slug) => ({ slug, url: slugToUrl(slug) }))
    .filter((p) => p.url);
}

if (auditedPages.length === 0) {
  console.error('No audited pages could be resolved. Pass --pages=url1,url2 explicitly.');
  process.exit(1);
}

// 3. Fetch helper (cached)
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

const fetchCached = async (url, cachePath) => {
  // Cache read: if the file exists and is non-empty, reuse it (regardless of
  // whether this run or a prior Phase 1 wrote it). This is the handshake that
  // lets discover-site Phase 1 avoid duplicate fetches.
  if (fs.existsSync(cachePath) && fs.statSync(cachePath).size > 0) {
    if (process.env.DEBUG_AUDIT) console.log('cache hit:', cachePath);
    return { cached: true, body: fs.readFileSync(cachePath, 'utf8'), status: 200 };
  }
  try {
    const res = await fetch(url, { headers: { 'User-Agent': UA }, redirect: 'follow' });
    const body = await res.text();
    if (res.ok) fs.writeFileSync(cachePath, body);
    return { cached: false, body, status: res.status };
  } catch (e) {
    return { cached: false, body: '', status: 0, error: String(e) };
  }
};

// 4. Fetch per-page HTML + robots.txt + llms.txt
const robotsRes = await fetchCached(`${baseUrl}/robots.txt`, path.join(RAW_DIR, 'robots.txt'));
const llmsRes = await fetchCached(`${baseUrl}/llms.txt`, path.join(RAW_DIR, 'llms.txt'));
const llmsFullRes = await fetchCached(`${baseUrl}/llms-full.txt`, path.join(RAW_DIR, 'llms-full.txt'));

for (const p of auditedPages) {
  // Prefer .raw.html (unrendered fetch from Phase 1) for signal extraction,
  // fall back to .html (browser-rendered dump) or a fresh fetch.
  const rawHtmlPath = path.join(RAW_DIR, `${p.slug}.raw.html`);
  const cachePath = path.join(RAW_DIR, `${p.slug}.html`);
  let chosenPath = null;
  if (fs.existsSync(rawHtmlPath) && fs.statSync(rawHtmlPath).size > 0) {
    chosenPath = rawHtmlPath;
    p.html_status = 200;
  } else {
    const r = await fetchCached(p.url, cachePath);
    p.html_status = r.status;
    chosenPath = fs.existsSync(cachePath) ? cachePath : null;
  }
  p.html_path = chosenPath;
}

// 5. Run extractors via spawn (keep each script independently testable).
const runNode = (scriptName, extraArgs) => {
  const script = path.join(__dirname, scriptName);
  const result = spawnSync(process.execPath, [script, ...extraArgs], { encoding: 'utf8' });
  if (result.status !== 0) {
    console.error(`[${scriptName}] failed:`, result.stderr);
    return null;
  }
  try {
    return JSON.parse(result.stdout);
  } catch {
    return null;
  }
};

const pagesData = [];
for (const p of auditedPages) {
  const entry = { slug: p.slug, url: p.url };
  if (p.html_path) {
    entry.signals = runNode('extract-page-signals.mjs', [p.html_path, p.url]);
  } else {
    entry.signals = { error: `fetch_failed:${p.html_status}` };
  }
  entry.lighthouse = {};
  for (const strategy of ['mobile', 'desktop']) {
    const psiPath = path.join(PSI_DIR, `${p.slug}-${strategy}.json`);
    if (fs.existsSync(psiPath)) {
      entry.lighthouse[strategy] = runNode('extract-lighthouse.mjs', [psiPath]);
    }
  }
  pagesData.push(entry);
}

const robots = runNode('analyze-robots.mjs', [path.join(RAW_DIR, 'robots.txt')]) || {
  present: false,
};

// Social / GBP / directory link extraction — runs on homepage raw HTML only.
let social = null;
const homepageEntry = pagesData.find((p) => p.slug === 'homepage') || pagesData[0];
const homepageHtmlPath = (() => {
  // Locate the source file we used for homepage signals
  const auditedHome = auditedPages.find((p) => p.slug === 'homepage') || auditedPages[0];
  return auditedHome?.html_path || null;
})();
if (homepageHtmlPath) {
  social = runNode('extract-social-links.mjs', [homepageHtmlPath]);
}

// Entity signals — homepage + first about-like page merged, homepage wins conflicts.
let entity = null;
if (homepageHtmlPath) {
  const homeEntity = runNode('extract-entity-signals.mjs', [homepageHtmlPath]) || {};
  const aboutPage = auditedPages.find(
    (p) => /^about/i.test(p.slug) || /\/about/i.test(p.url),
  );
  let aboutEntity = {};
  if (aboutPage && aboutPage.html_path && aboutPage.html_path !== homepageHtmlPath) {
    aboutEntity = runNode('extract-entity-signals.mjs', [aboutPage.html_path]) || {};
  }
  // Merge: about fills gaps, homepage wins on conflict.
  entity = { ...aboutEntity, ...Object.fromEntries(Object.entries(homeEntity).filter(([, v]) => v != null && !(Array.isArray(v) && v.length === 0))) };
  // Ensure all keys present
  for (const k of ['org_name', 'org_type', 'founding_date', 'address', 'opening_hours', 'founder_name', 'phone', 'email', 'same_as']) {
    if (!(k in entity)) entity[k] = homeEntity[k] ?? aboutEntity[k] ?? null;
  }
  // Completeness: non-null of 7 key fields.
  const checks = [
    entity.org_name,
    Array.isArray(entity.org_type) && entity.org_type.length > 0 ? entity.org_type : null,
    entity.founding_date,
    entity.address?.locality || entity.address?.raw || null,
    entity.phone,
    Array.isArray(entity.opening_hours) && entity.opening_hours.length > 0 ? entity.opening_hours : null,
    entity.founder_name,
  ];
  const filled = checks.filter((v) => v != null && v !== '').length;
  entity.completeness_pct = Math.round((filled / 7) * 100);
}

// Favicon inspection — pure disk read, no network.
const inspectAsset = (p) => {
  if (!fs.existsSync(p)) return { present: false, bytes: 0 };
  const stat = fs.statSync(p);
  return { present: true, bytes: stat.size };
};
const favicon = {
  favicon_ico: inspectAsset(path.join(ASSETS_SEO, 'favicon.ico')),
  apple_touch_icon: inspectAsset(path.join(ASSETS_SEO, 'apple-touch-icon.png')),
};
favicon.present = favicon.favicon_ico.present || favicon.apple_touch_icon.present;

// Site-wide alt coverage — computed in Phase 1 during nav crawl,
// written to site-map.json. We just read it here.
const siteWideAltCoverage = siteMap.site_wide_alt_coverage || null;

// TODO(gbp-v2): active GBP/social presence lookup via Google Places API and
// Instagram/Facebook handle probes. Gated on Places API key + budget approval.

// 6. Derived site-wide metrics (prefer homepage mobile as the headline)
const homepage = pagesData.find((p) => p.slug === 'homepage') || pagesData[0];
const homeMobile = homepage?.lighthouse?.mobile;
const homeDesktop = homepage?.lighthouse?.desktop;

const derived = {
  pages_discovered: siteMap.summary?.total_pages_discovered ?? null,
  unique_pages: siteMap.summary?.unique_pages ?? null,
  template_groups: siteMap.summary?.template_groups ?? null,
  audited_pages: pagesData.length,
  headline: {
    today_mb: homeMobile?.derived?.today_mb ?? null,
    target_mb: homeMobile?.derived?.target_mb ?? null,
    saved_mb:
      homeMobile?.derived
        ? +(homeMobile.derived.today_mb - homeMobile.derived.target_mb).toFixed(2)
        : null,
    top_savings_seconds: homeMobile?.derived?.top_savings_seconds ?? null,
    cls_conversion_drag_mobile: homeMobile?.derived?.cls_conversion_drag_pct ?? null,
    cls_conversion_drag_desktop: homeDesktop?.derived?.cls_conversion_drag_pct ?? null,
  },
};

// Count "quick wins" — simple heuristic based on which checks failed
const quickWins = [];
const sig = homepage?.signals || {};
if (!sig.meta_description) quickWins.push('Add homepage meta description');
if (!sig.og_image) quickWins.push('Add Open Graph image');
if (!sig.og_title) quickWins.push('Add Open Graph title');
if (sig.h1_count === 0) quickWins.push('Add H1 to homepage');
if (!sig.jsonld_types || sig.jsonld_types.length === 0) quickWins.push('Add JSON-LD structured data');
if (sig.img_without_alt > 0) quickWins.push(`Fix ${sig.img_without_alt} images missing alt text`);
if ((sig.title_length || 0) < 20) quickWins.push('Expand homepage title (too short)');
if (!llmsRes.body || llmsRes.status !== 200) quickWins.push('Publish llms.txt for AI crawlers');
if (homeMobile?.scores?.performance < 90) quickWins.push('Improve mobile performance score');
if (homeMobile?.derived?.image_savings_mb > 0.5) quickWins.push('Convert images to modern formats (WebP/AVIF)');
if (homeMobile?.cwv?.cls?.numericValue > 0.1) quickWins.push('Stabilize layout (reduce CLS)');
if (!sig.canonical) quickWins.push('Add canonical URLs');
derived.quick_wins_count = quickWins.length;
derived.quick_wins = quickWins;

const out = {
  generated_at: new Date().toISOString(),
  client_dir: path.resolve(clientDir),
  base_url: baseUrl,
  site_map_summary: siteMap.summary || null,
  audited_pages: pagesData,
  robots,
  llms_txt: {
    present: llmsRes.status === 200,
    status: llmsRes.status,
    bytes: llmsRes.status === 200 ? llmsRes.body.length : 0,
  },
  llms_full_txt: {
    present: llmsFullRes.status === 200,
    status: llmsFullRes.status,
    bytes: llmsFullRes.status === 200 ? llmsFullRes.body.length : 0,
  },
  derived,
  favicon,
  social,
  entity,
};
derived.site_wide_alt_coverage = siteWideAltCoverage;
// Phase 2 appends competitor_design[] into derived via read-modify-write.
if (!derived.competitor_design) derived.competitor_design = [];

const outPath = path.join(RESEARCH, 'audit-data.json');
fs.writeFileSync(outPath, JSON.stringify(out, null, 2));
console.log(`Wrote ${outPath}`);
console.log(
  `  audited: ${pagesData.length} pages · quick wins: ${derived.quick_wins_count} · headline MB: ${derived.headline.today_mb}`,
);
