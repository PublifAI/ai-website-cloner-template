#!/usr/bin/env node
// Extract social profile links, Google Business Profile links, and directory
// profile links from a single HTML file. Zero network calls — pure HTML parse.
//
// Usage: node extract-social-links.mjs <html-file>
// Emits JSON on stdout.

import fs from 'node:fs';

const file = process.argv[2];
if (!file) {
  console.error('Usage: extract-social-links.mjs <html-file>');
  process.exit(1);
}

const h = fs.readFileSync(file, 'utf8');

const SOCIAL_PATTERNS = [
  { name: 'facebook', re: /https?:\/\/(?:www\.)?facebook\.com\/[^"'\s<>]+/gi },
  { name: 'instagram', re: /https?:\/\/(?:www\.)?instagram\.com\/[^"'\s<>]+/gi },
  { name: 'twitter', re: /https?:\/\/(?:www\.)?(?:twitter|x)\.com\/[^"'\s<>]+/gi },
  { name: 'youtube', re: /https?:\/\/(?:www\.)?youtube\.com\/[^"'\s<>]+/gi },
  { name: 'linkedin', re: /https?:\/\/(?:www\.)?linkedin\.com\/[^"'\s<>]+/gi },
  { name: 'telegram', re: /https?:\/\/(?:www\.)?t\.me\/[^"'\s<>]+/gi },
  { name: 'whatsapp', re: /https?:\/\/(?:www\.)?wa\.me\/[^"'\s<>]+/gi },
  { name: 'pinterest', re: /https?:\/\/(?:www\.)?pinterest\.com\/[^"'\s<>]+/gi },
  { name: 'tiktok', re: /https?:\/\/(?:www\.)?tiktok\.com\/[^"'\s<>]+/gi },
];

const GBP_PATTERNS = [
  /https?:\/\/maps\.google\.com\/[^"'\s<>]+/gi,
  /https?:\/\/g\.page\/[^"'\s<>]+/gi,
  /https?:\/\/goo\.gl\/maps\/[^"'\s<>]+/gi,
  /https?:\/\/(?:www\.)?google\.com\/maps\/place\/[^"'\s<>]+/gi,
  /https?:\/\/maps\.app\.goo\.gl\/[^"'\s<>]+/gi,
];

const DIRECTORY_PATTERNS = [
  { name: 'yelp', re: /https?:\/\/(?:www\.)?yelp\.com\/biz\/[^"'\s<>]+/gi },
  { name: 'tripadvisor', re: /https?:\/\/(?:www\.)?tripadvisor\.[a-z.]+\/[^"'\s<>]+/gi },
  { name: 'justdial', re: /https?:\/\/(?:www\.)?justdial\.com\/[^"'\s<>]+/gi },
  { name: 'indiamart', re: /https?:\/\/(?:www\.)?indiamart\.com\/[^"'\s<>]+/gi },
];

const unique = (arr) => [...new Set(arr)];

const foundViaLinks = [];
for (const { re } of SOCIAL_PATTERNS) {
  const hits = h.match(re) || [];
  foundViaLinks.push(...hits);
}

let gbpUrl = null;
for (const re of GBP_PATTERNS) {
  const hits = h.match(re);
  if (hits && hits.length) {
    gbpUrl = hits[0];
    break;
  }
}

const directoryProfiles = [];
for (const { name, re } of DIRECTORY_PATTERNS) {
  const hits = h.match(re) || [];
  for (const url of hits) directoryProfiles.push({ platform: name, url });
}

// sameAs from JSON-LD
const jsonldScripts = [
  ...h.matchAll(/<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi),
];
const foundViaSameAs = [];
for (const s of jsonldScripts) {
  try {
    const parsed = JSON.parse(s[1]);
    const walk = (node) => {
      if (!node || typeof node !== 'object') return;
      if (Array.isArray(node)) return node.forEach(walk);
      if (node.sameAs) {
        const arr = Array.isArray(node.sameAs) ? node.sameAs : [node.sameAs];
        foundViaSameAs.push(...arr);
      }
      if (node['@graph']) node['@graph'].forEach(walk);
    };
    walk(parsed);
  } catch {
    // ignore parse errors
  }
}

const out = {
  found_via_links: unique(foundViaLinks),
  found_via_sameas: unique(foundViaSameAs),
  gbp_linked: Boolean(gbpUrl),
  gbp_url: gbpUrl,
  directory_profiles: directoryProfiles,
};

console.log(JSON.stringify(out, null, 2));
