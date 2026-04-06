#!/usr/bin/env node
// fetch-pagespeed.mjs <client-dir>
//
// Reads <client-dir>/research/audit-pages.json and fetches Google PageSpeed
// Insights (mobile + desktop) for every page. Writes raw responses to
// <client-dir>/research/pagespeed/<slug>-<strategy>.json.
//
// Idempotent: skips files that already exist and are > 1KB. Hard-fails if
// PSI_API_KEY is missing — the unauthenticated endpoint's shared quota is
// almost always exhausted.

import fs from 'node:fs';
import path from 'node:path';

const CLIENT_DIR = process.argv[2];
if (!CLIENT_DIR) {
  console.error('Usage: fetch-pagespeed.mjs <client-dir>');
  process.exit(1);
}

const ROOT = path.resolve(CLIENT_DIR);
const PAGES_FILE = path.join(ROOT, 'research/audit-pages.json');
const OUT_DIR = path.join(ROOT, 'research/pagespeed');

if (!fs.existsSync(PAGES_FILE)) {
  console.error(`Error: ${PAGES_FILE} not found. Run Phase 1 Step 5 first.`);
  process.exit(1);
}

// Read PSI_API_KEY from repo .env (cloner template) or env var.
function loadPsiKey() {
  if (process.env.PSI_API_KEY) return process.env.PSI_API_KEY;
  const candidates = [
    path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../.env'),
    path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../../.env'),
    path.join(ROOT, '.env'),
  ];
  for (const p of candidates) {
    if (!fs.existsSync(p)) continue;
    for (const line of fs.readFileSync(p, 'utf8').split('\n')) {
      const m = line.match(/^\s*PSI_API_KEY\s*=\s*"?([^"\s]+)"?/);
      if (m) return m[1];
    }
  }
  return null;
}

const PSI_KEY = loadPsiKey();
if (!PSI_KEY) {
  console.error('Error: PSI_API_KEY not set. Add it to .env or env vars before running.');
  console.error('The unauthenticated PSI endpoint shares a quota that is almost always exhausted.');
  process.exit(1);
}

fs.mkdirSync(OUT_DIR, { recursive: true });

const { pages } = JSON.parse(fs.readFileSync(PAGES_FILE, 'utf8'));
const STRATEGIES = ['mobile', 'desktop'];

function urlFor(pageUrl, strategy) {
  const u = new URL('https://www.googleapis.com/pagespeedonline/v5/runPagespeed');
  u.searchParams.set('url', pageUrl);
  u.searchParams.set('strategy', strategy);
  for (const c of ['performance', 'accessibility', 'seo']) u.searchParams.append('category', c);
  u.searchParams.set('key', PSI_KEY);
  return u.toString();
}

async function fetchOne(page, strategy) {
  const out = path.join(OUT_DIR, `${page.slug}-${strategy}.json`);
  if (fs.existsSync(out) && fs.statSync(out).size > 1024) {
    return { page: page.slug, strategy, status: 'skip', score: scoreFromFile(out) };
  }
  try {
    const r = await fetch(urlFor(page.url, strategy));
    const body = await r.text();
    if (!r.ok) {
      fs.writeFileSync(out, JSON.stringify({ error: `HTTP ${r.status}`, body: body.slice(0, 500) }, null, 2));
      return { page: page.slug, strategy, status: 'error', score: null };
    }
    fs.writeFileSync(out, body);
    return { page: page.slug, strategy, status: 'ok', score: scoreFromFile(out) };
  } catch (e) {
    fs.writeFileSync(out, JSON.stringify({ error: String(e) }, null, 2));
    return { page: page.slug, strategy, status: 'error', score: null };
  }
}

function scoreFromFile(p) {
  try {
    const j = JSON.parse(fs.readFileSync(p, 'utf8'));
    const s = j?.lighthouseResult?.categories?.performance?.score;
    return s == null ? null : Math.round(s * 100);
  } catch { return null; }
}

// Bounded parallelism (cap 6 — PSI per-second limit).
async function runAll() {
  const jobs = [];
  for (const p of pages) for (const s of STRATEGIES) jobs.push([p, s]);
  const results = [];
  const CONCURRENCY = 6;
  let i = 0;
  await Promise.all(Array.from({ length: CONCURRENCY }, async () => {
    while (i < jobs.length) {
      const [p, s] = jobs[i++];
      const r = await fetchOne(p, s);
      results.push(r);
      const tag = r.status === 'ok' ? '✓' : (r.status === 'skip' ? '·' : '✗');
      console.log(`  ${tag} ${r.page.padEnd(24)} ${r.strategy.padEnd(8)} ${r.score ?? ''}`);
    }
  }));
  return results;
}

console.log(`PSI fetch → ${OUT_DIR}`);
console.log(`  ${pages.length} pages × ${STRATEGIES.length} strategies = ${pages.length * STRATEGIES.length} requests\n`);
const results = await runAll();
const ok = results.filter(r => r.status === 'ok').length;
const skip = results.filter(r => r.status === 'skip').length;
const err = results.filter(r => r.status === 'error').length;
console.log(`\n  ok=${ok} skipped=${skip} errors=${err}`);
if (err && ok + skip === 0) process.exit(2);
