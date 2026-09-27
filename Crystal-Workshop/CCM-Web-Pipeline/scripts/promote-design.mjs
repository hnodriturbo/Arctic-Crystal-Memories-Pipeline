/** Purpose: Agent CLI for the same explicit design handoff used by Workshop's button. No publication. */
import fs from 'node:fs';
import path from 'node:path';
import { collectDesignSources } from '../src/lib/claude-design/discovery.mjs';
import { promotePackage } from '../src/lib/claude-design/promotion.mjs';
import { contentTypeFor } from '../src/lib/storage/workshop-r2.js';
import { sharedStore } from '../src/lib/storage/shared-r2.mjs';

const args = process.argv.slice(2);
const flag = name => args[args.indexOf(name) + 1];
try {
  if (!['--entry', '--variant', '--receipt'].every(name => args.includes(name))) throw new Error('Need --entry, --variant and --receipt.');
  const root = process.env.CLAUDE_DESIGN_ROOT;
  if (!root || !path.isAbsolute(root)) throw new Error('Configure an absolute CLAUDE_DESIGN_ROOT.');
  const entryPath = flag('--entry');
  const receiptPath = flag('--receipt');
  const files = collectDesignSources(root, entryPath, contentTypeFor);
  // Reserve evidence before making any remote writes.
  fs.writeFileSync(receiptPath, '', { flag: 'wx' });
  const receipt = await promotePackage({ kind: 'design', variant: flag('--variant'), entryPath, files, store: sharedStore() });
  fs.writeFileSync(receiptPath, JSON.stringify(receipt, null, 2));
  console.log(JSON.stringify(receipt));
} catch (error) {
  console.error('Promotion failed:', error.$metadata?.httpStatusCode || error.code || error.message);
  process.exitCode = 1;
}
