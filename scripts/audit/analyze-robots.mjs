#!/usr/bin/env node
// Analyze robots.txt for AI crawler access + sitemap references.
// Usage: node analyze-robots.mjs <robots.txt-path>

import fs from 'node:fs';

const [, , file] = process.argv;
if (!file) {
  console.error('Usage: analyze-robots.mjs <robots.txt-path>');
  process.exit(1);
}

const AI_BOTS = [
  'GPTBot',
  'OAI-SearchBot',
  'ChatGPT-User',
  'PerplexityBot',
  'Perplexity-User',
  'ClaudeBot',
  'Claude-Web',
  'Google-Extended',
  'Applebot-Extended',
  'CCBot',
  'Bytespider',
  'Amazonbot',
];

let robots = '';
try {
  robots = fs.readFileSync(file, 'utf8');
} catch {
  console.log(JSON.stringify({ present: false, bots: {}, wildcard_allows: null, sitemaps: [] }, null, 2));
  process.exit(0);
}

const botStatus = {};
for (const bot of AI_BOTS) {
  const reBot = new RegExp(`User-agent:\\s*${bot}\\b`, 'i');
  if (reBot.test(robots)) {
    const idx = robots.search(reBot);
    const block = robots.substring(idx).split(/User-agent:/i)[0];
    if (/Disallow:\s*\/\s*$/m.test(block)) botStatus[bot] = 'blocked';
    else if (/Disallow:\s*\/\S/.test(block)) botStatus[bot] = 'partially_blocked';
    else botStatus[bot] = 'explicitly_allowed';
  } else {
    botStatus[bot] = 'not_mentioned';
  }
}

const hasWildcard = /User-agent:\s*\*/i.test(robots);
const wildcardBlockAll = /User-agent:\s*\*[\s\S]*?Disallow:\s*\/\s*$/m.test(robots);
const wildcardAllows = hasWildcard && !wildcardBlockAll;

const sitemaps = [...robots.matchAll(/Sitemap:\s*(\S+)/gi)].map((x) => x[1]);

console.log(
  JSON.stringify(
    {
      present: true,
      bytes: robots.length,
      bots: botStatus,
      wildcard_present: hasWildcard,
      wildcard_allows: wildcardAllows,
      sitemaps,
    },
    null,
    2,
  ),
);
