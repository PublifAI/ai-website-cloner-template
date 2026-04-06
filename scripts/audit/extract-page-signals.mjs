#!/usr/bin/env node
// Extract SEO / GEO signals from a single HTML file.
// Usage: node extract-page-signals.mjs <html-file> <url>
// Emits JSON on stdout.

import fs from 'node:fs';

const [, , file, url] = process.argv;
if (!file || !url) {
  console.error('Usage: extract-page-signals.mjs <html-file> <url>');
  process.exit(1);
}

const h = fs.readFileSync(file, 'utf8');
const m = (re) => {
  const x = h.match(re);
  return x ? x[1] : null;
};

const imgTags = h.match(/<img\s[^>]*>/gi) || [];
const imgWithoutAlt = imgTags.filter((t) => !/\salt\s*=/i.test(t)).length;
const imgEmptyAlt = imgTags.filter((t) => /\salt\s*=\s*["']\s*["']/i.test(t)).length;

const jsonldScripts = [
  ...h.matchAll(/<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi),
];
const jsonldTypes = jsonldScripts
  .map((s) => {
    try {
      const p = JSON.parse(s[1]);
      if (p['@graph']) return p['@graph'].map((x) => x['@type']).flat();
      return p['@type'];
    } catch {
      return 'parse_error';
    }
  })
  .flat()
  .filter(Boolean);

const bodyText = h
  .replace(/<script[\s\S]*?<\/script>/gi, '')
  .replace(/<style[\s\S]*?<\/style>/gi, '')
  .replace(/<[^>]+>/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

const title = m(/<title>\s*([^<]*?)\s*<\/title>/i);
const metaDesc = m(/<meta[^>]*name=["']description["'][^>]*content=["']([^"']*)["']/i);

const out = {
  url,
  title,
  title_length: (title || '').length,
  meta_description: metaDesc,
  meta_description_length: (metaDesc || '').length,
  og_title: m(/<meta[^>]*property=["']og:title["'][^>]*content=["']([^"']*)["']/i),
  og_description: m(/<meta[^>]*property=["']og:description["'][^>]*content=["']([^"']*)["']/i),
  og_image: m(/<meta[^>]*property=["']og:image["'][^>]*content=["']([^"']*)["']/i),
  twitter_card: m(/<meta[^>]*name=["']twitter:card["'][^>]*content=["']([^"']*)["']/i),
  canonical: m(/<link[^>]*rel=["']canonical["'][^>]*href=["']([^"']*)["']/i),
  favicon: m(/<link[^>]*rel=["'](?:shortcut )?icon["'][^>]*href=["']([^"']*)["']/i),
  h1_count: (h.match(/<h1[\s>]/gi) || []).length,
  h2_count: (h.match(/<h2[\s>]/gi) || []).length,
  jsonld_blocks: jsonldScripts.length,
  jsonld_types: jsonldTypes,
  img_total: imgTags.length,
  img_without_alt: imgWithoutAlt,
  img_empty_alt: imgEmptyAlt,
  raw_html_bytes: h.length,
  body_text_chars: bodyText.length,
  ssr_ratio: +(bodyText.length / h.length).toFixed(3),
  generic_link_count: (h.match(/>(click here|read more|learn more|\bhere\b)</gi) || []).length,
  last_updated_visible: /last updated|updated on|updated:/i.test(h),
};

console.log(JSON.stringify(out, null, 2));
