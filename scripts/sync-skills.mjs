#!/usr/bin/env node

/**
 * Generates command/skill files for all supported AI coding platforms.
 * Source of truth: .claude/skills/<skill-name>/SKILL.md
 *
 * Automatically discovers all skills in .claude/skills/ and syncs each one.
 *
 * Usage: node scripts/sync-skills.mjs
 */

import { readFileSync, writeFileSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SKILLS_DIR = join(ROOT, '.claude', 'skills');

// --- Helpers ---

function write(relPath, content) {
  const full = join(ROOT, relPath);
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, content, 'utf8');
  console.log(`  \u2713 ${relPath}`);
}

const HEADER = (skillName) =>
  `<!-- AUTO-GENERATED from .claude/skills/${skillName}/SKILL.md \u2014 do not edit directly.\n` +
  `     Run \`node scripts/sync-skills.mjs\` to regenerate. -->\n\n`;

const noArgs = (text) => text.replace(/\$ARGUMENTS/g, 'the target URL provided by the user');

// --- Discover skills ---

const skillDirs = readdirSync(SKILLS_DIR).filter((name) => {
  const skillPath = join(SKILLS_DIR, name);
  return statSync(skillPath).isDirectory() && statSync(join(skillPath, 'SKILL.md')).isFile();
});

if (skillDirs.length === 0) {
  console.error('Error: No skills found in .claude/skills/');
  process.exit(1);
}

console.log(`Found ${skillDirs.length} skill(s): ${skillDirs.join(', ')}\n`);

let totalFiles = 0;

for (const skillName of skillDirs) {
  const sourcePath = join(SKILLS_DIR, skillName, 'SKILL.md');

  let raw;
  try {
    raw = readFileSync(sourcePath, 'utf8').replace(/\r\n/g, '\n');
  } catch {
    console.error(`Error: Could not read ${sourcePath}`);
    continue;
  }

  const match = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) {
    console.error(`Error: Could not parse frontmatter in ${skillName}/SKILL.md`);
    continue;
  }

  const frontmatter = match[1];
  const body = match[2];

  // Extract description from frontmatter
  const descMatch = frontmatter.match(/description:\s*(.+?)(?:\n|$)/);
  const shortDesc = descMatch
    ? descMatch[1].replace(/^["']|["']$/g, '').slice(0, 120)
    : `AI skill: ${skillName}`;

  console.log(`Syncing skill: ${skillName}`);
  console.log(`  Source: .claude/skills/${skillName}/SKILL.md\n`);

  // 1. Codex CLI — same SKILL.md format, same $ARGUMENTS syntax
  write(`.codex/skills/${skillName}/SKILL.md`, raw);

  // 2. GitHub Copilot — same SKILL.md format
  write(`.github/skills/${skillName}/SKILL.md`, raw);

  // 3. Cursor — plain markdown, no argument substitution support
  write(`.cursor/commands/${skillName}.md`, HEADER(skillName) + noArgs(body));

  // 4. Windsurf — markdown workflow
  write(`.windsurf/workflows/${skillName}.md`, HEADER(skillName) + noArgs(body));

  // 5. Gemini CLI — TOML format, {{args}} for arguments
  const geminiBody = body.replace(/\$ARGUMENTS/g, '{{args}}');
  write(
    `.gemini/commands/${skillName}.toml`,
    `# AUTO-GENERATED from .claude/skills/${skillName}/SKILL.md\n` +
      `# Run \`node scripts/sync-skills.mjs\` to regenerate.\n\n` +
      `description = "${shortDesc}"\n\n` +
      `[prompt]\ntext = '''\n${geminiBody}\n'''\n`
  );

  // 6. OpenCode — markdown + YAML frontmatter, $ARGUMENTS works natively
  write(
    `.opencode/commands/${skillName}.md`,
    `---\ndescription: "${shortDesc}"\n---\n${HEADER(skillName)}${body}`
  );

  // 7. Augment Code — markdown + YAML frontmatter
  write(
    `.augment/commands/${skillName}.md`,
    `---\ndescription: "${shortDesc}"\nargument-hint: "<url>"\n---\n${HEADER(skillName)}${body}`
  );

  // 8. Continue — prompt file with invokable: true
  write(
    `.continue/commands/${skillName}.md`,
    `---\nname: ${skillName}\ndescription: "${shortDesc}"\ninvokable: true\n---\n${HEADER(skillName)}${body}`
  );

  // 9. Amazon Q — JSON agent definition
  write(
    `.amazonq/cli-agents/${skillName}.json`,
    JSON.stringify(
      {
        name: skillName,
        description: shortDesc,
        prompt: noArgs(body),
        fileContext: ['AGENTS.md', 'docs/research/**'],
      },
      null,
      2
    ) + '\n'
  );

  totalFiles += 9;
  console.log('');
}

console.log(`Done! ${totalFiles} platform command files generated from ${skillDirs.length} skill(s).`);
