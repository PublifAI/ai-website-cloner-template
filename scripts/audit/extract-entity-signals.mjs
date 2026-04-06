#!/usr/bin/env node
// Extract entity / business signals from a single HTML file.
// Zero network — pure HTML parse. Same style as extract-social-links.mjs.
//
// Extracts: org_name, org_type[], founding_date (+source), address (PostalAddress,
// <address> tag), opening_hours[], founder_name, phone, email, same_as[].
//
// Usage: node extract-entity-signals.mjs <html-file>
// Emits JSON on stdout. Every field is nullable.

import fs from 'node:fs';

const file = process.argv[2];
if (!file) {
  console.error('Usage: extract-entity-signals.mjs <html-file>');
  process.exit(1);
}

const h = fs.readFileSync(file, 'utf8');

// ---------- JSON-LD walk ----------
const ldScripts = [
  ...h.matchAll(/<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi),
];

const ldNodes = [];
for (const m of ldScripts) {
  try {
    const raw = m[1].trim();
    const parsed = JSON.parse(raw);
    const walk = (n) => {
      if (!n || typeof n !== 'object') return;
      if (Array.isArray(n)) return n.forEach(walk);
      ldNodes.push(n);
      if (n['@graph']) n['@graph'].forEach(walk);
    };
    walk(parsed);
  } catch {
    /* ignore */
  }
}

const pickLd = (pred) => ldNodes.find(pred) || null;

const orgLike = pickLd(
  (n) =>
    n['@type'] &&
    (Array.isArray(n['@type'])
      ? n['@type'].some((t) => /Organization|LocalBusiness|Store|Restaurant|ArtGallery/i.test(t))
      : /Organization|LocalBusiness|Store|Restaurant|ArtGallery/i.test(n['@type'])),
);

// ---------- org_name / org_type ----------
let org_name = orgLike?.name || null;
let org_type = null;
if (orgLike?.['@type']) {
  org_type = Array.isArray(orgLike['@type']) ? orgLike['@type'] : [orgLike['@type']];
}

// ---------- founding_date ----------
let founding_date = null;
let founding_date_source = null;
if (orgLike?.foundingDate) {
  const m = String(orgLike.foundingDate).match(/(\d{4})/);
  if (m) {
    founding_date = m[1];
    founding_date_source = 'jsonld';
  }
}
if (!founding_date) {
  // Strip tags for body regex
  const text = h.replace(/<[^>]+>/g, ' ');
  const re = /(?:est(?:ablished)?|since|founded)[. ]+(\d{4})/i;
  const bm = text.match(re);
  if (bm) {
    founding_date = bm[1];
    founding_date_source = 'body_regex';
  }
}

// ---------- address ----------
let address = null;
const addrNode =
  orgLike?.address ||
  pickLd((n) => n['@type'] === 'PostalAddress') ||
  null;
if (addrNode && typeof addrNode === 'object') {
  address = {
    street: addrNode.streetAddress || null,
    locality: addrNode.addressLocality || null,
    region: addrNode.addressRegion || null,
    postal_code: addrNode.postalCode || null,
    country: addrNode.addressCountry || null,
  };
}
if (!address) {
  const am = h.match(/<address[^>]*>([\s\S]*?)<\/address>/i);
  if (am) {
    const txt = am[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    if (txt) address = { street: null, locality: null, region: null, postal_code: null, country: null, raw: txt };
  }
}

// ---------- opening_hours ----------
let opening_hours = null;
if (orgLike?.openingHours) {
  opening_hours = Array.isArray(orgLike.openingHours) ? orgLike.openingHours : [orgLike.openingHours];
} else if (orgLike?.openingHoursSpecification) {
  const arr = Array.isArray(orgLike.openingHoursSpecification)
    ? orgLike.openingHoursSpecification
    : [orgLike.openingHoursSpecification];
  opening_hours = arr.map((s) => {
    const days = Array.isArray(s.dayOfWeek) ? s.dayOfWeek.join(',') : s.dayOfWeek || '';
    return `${days} ${s.opens || ''}-${s.closes || ''}`.trim();
  });
}

// ---------- founder_name ----------
let founder_name = null;
if (orgLike?.founder) {
  const f = Array.isArray(orgLike.founder) ? orgLike.founder[0] : orgLike.founder;
  founder_name = typeof f === 'string' ? f : f?.name || null;
}

// ---------- phone ----------
let phone = orgLike?.telephone || null;
if (!phone) {
  const tm = h.match(/href=["']tel:([^"']+)["']/i);
  if (tm) phone = tm[1];
}

// ---------- email ----------
let email = orgLike?.email || null;
if (!email) {
  const em = h.match(/href=["']mailto:([^"'?]+)/i);
  if (em) email = em[1];
}

// ---------- same_as ----------
let same_as = [];
for (const n of ldNodes) {
  if (n.sameAs) {
    const arr = Array.isArray(n.sameAs) ? n.sameAs : [n.sameAs];
    same_as.push(...arr);
  }
}
same_as = [...new Set(same_as)];

const out = {
  org_name,
  org_type,
  founding_date,
  founding_date_source,
  address,
  opening_hours,
  founder_name,
  phone,
  email,
  same_as,
};

console.log(JSON.stringify(out, null, 2));
