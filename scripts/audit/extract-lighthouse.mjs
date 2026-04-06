#!/usr/bin/env node
// Extract numeric findings from a PageSpeed Insights JSON response.
// Usage: node extract-lighthouse.mjs <psi-json-path>

import fs from 'node:fs';

const [, , file] = process.argv;
if (!file) {
  console.error('Usage: extract-lighthouse.mjs <psi-json-path>');
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(file, 'utf8'));
if (data.error) {
  console.log(JSON.stringify({ error: data.error }, null, 2));
  process.exit(0);
}

const lh = data.lighthouseResult;
const a = lh.audits;
const c = lh.categories;

const pick = (k) => {
  const x = a[k];
  if (!x) return null;
  return {
    score: x.score,
    displayValue: x.displayValue ?? null,
    numericValue: x.numericValue ?? null,
    savings_bytes: x.details?.overallSavingsBytes ?? 0,
    savings_ms: x.details?.overallSavingsMs ?? 0,
    items: x.details?.items?.length ?? 0,
  };
};

const scores = {
  performance: Math.round((c.performance?.score ?? 0) * 100),
  accessibility: Math.round((c.accessibility?.score ?? 0) * 100),
  seo: Math.round((c.seo?.score ?? 0) * 100),
  best_practices: Math.round((c['best-practices']?.score ?? 0) * 100),
};

const cwv = {
  lcp: pick('largest-contentful-paint'),
  cls: pick('cumulative-layout-shift'),
  tbt: pick('total-blocking-time'),
  fcp: pick('first-contentful-paint'),
  si: pick('speed-index'),
  inp: pick('interaction-to-next-paint'),
};

const opportunities = {
  total_byte_weight: pick('total-byte-weight'),
  uses_optimized_images: pick('uses-optimized-images'),
  uses_responsive_images: pick('uses-responsive-images'),
  modern_image_formats: pick('modern-image-formats'),
  offscreen_images: pick('offscreen-images'),
  unused_css: pick('unused-css-rules'),
  unused_js: pick('unused-javascript'),
  render_blocking: pick('render-blocking-resources'),
};

const seo_audits = {
  meta_description: pick('meta-description'),
  document_title: pick('document-title'),
  structured_data: pick('structured-data'),
  image_alt: pick('image-alt'),
  tap_targets: pick('tap-targets'),
  is_crawlable: pick('is-crawlable'),
  viewport: pick('viewport'),
  hreflang: pick('hreflang'),
  canonical: pick('canonical'),
};

// Derived
const byteWeight = opportunities.total_byte_weight?.numericValue ?? 0;
const imgSavings =
  (opportunities.uses_optimized_images?.savings_bytes ?? 0) +
  (opportunities.uses_responsive_images?.savings_bytes ?? 0) +
  (opportunities.modern_image_formats?.savings_bytes ?? 0) +
  (opportunities.offscreen_images?.savings_bytes ?? 0);
const topSavingsMs = [
  opportunities.render_blocking?.savings_ms ?? 0,
  opportunities.unused_css?.savings_ms ?? 0,
  opportunities.unused_js?.savings_ms ?? 0,
].reduce((s, x) => s + x, 0);

// CLS → conversion drag: 7% drop per 0.1 above 0.1 threshold
const clsValue = cwv.cls?.numericValue ?? 0;
const cls_conversion_drag_pct = Math.max(0, ((clsValue - 0.1) / 0.1) * 7);

const derived = {
  today_mb: +(byteWeight / 1024 / 1024).toFixed(2),
  image_savings_mb: +(imgSavings / 1024 / 1024).toFixed(2),
  target_mb: +((byteWeight - imgSavings) / 1024 / 1024).toFixed(2),
  top_savings_seconds: +(topSavingsMs / 1000).toFixed(1),
  cls_value: clsValue,
  cls_conversion_drag_pct: Math.round(cls_conversion_drag_pct),
};

console.log(
  JSON.stringify(
    {
      strategy: data.lighthouseResult?.configSettings?.formFactor ?? 'unknown',
      url: data.lighthouseResult?.finalUrl ?? null,
      scores,
      cwv,
      opportunities,
      seo_audits,
      derived,
    },
    null,
    2,
  ),
);
