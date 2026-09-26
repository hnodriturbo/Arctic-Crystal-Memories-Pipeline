/** Purpose: Daily/manual two-way Claude Design sync; never propagate deletions or silently resolve conflicting edits. */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { syncTree } from '../src/lib/claude-design/sync-engine.mjs';
import { designStore } from '../src/lib/claude-design/sync-store.mjs';
const app = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = process.env.CLAUDE_DESIGN_ROOT ? path.resolve(process.env.CLAUDE_DESIGN_ROOT) : path.resolve(app, '../../../Claude-Design-Stuff');
const store = designStore();
const options = { store, dryRun: process.argv.includes('--dry-run'), onLine: console.log };
const sources = await syncTree({ ...options, root });
const videos = await syncTree({ ...options, root: path.join(root, 'exported-videos'), prefix: 'claude-design/videos/' });
console.log('CLAUDE_DESIGN_SYNC_' + (sources.conflicts || videos.conflicts ? 'CONFLICTS' : 'OK'), JSON.stringify({ sources, videos }));
if (sources.conflicts || videos.conflicts) process.exitCode = 2;
