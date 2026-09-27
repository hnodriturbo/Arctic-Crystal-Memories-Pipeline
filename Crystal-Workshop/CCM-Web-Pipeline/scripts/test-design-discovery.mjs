/** Purpose: Validate deep/remote design discovery and dependency denial without rendering or network. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { discoverLocal, inspectDesign, mergeRemote } from '../src/lib/claude-design/discovery.mjs';

test('deep HTML entries, components and missing x-import dependencies are visible', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'ccm-discovery-'));
  try {
    const relative = 'journey/a/b/c/d/e/index.html';
    await mkdir(path.dirname(path.join(root, relative)), { recursive: true });
    await writeFile(path.join(root, relative), '<x-import from="./one.jsx ./two.jsx"></x-import>');
    await writeFile(path.join(root, 'journey/a/b/c/d/e/one.jsx'), 'const Scene = 1;');
    let groups = discoverLocal(root);
    assert.equal(groups[0].designs.length, 1);
    assert.equal(groups[0].designs[0].readiness.ready, false);
    assert.match(groups[0].designs[0].readiness.issues[0], /two.jsx/);
    await writeFile(path.join(root, 'journey/a/b/c/d/e/two.jsx'), 'const Other = 1;');
    groups = discoverLocal(root);
    assert.equal(groups[0].designs[0].readiness.ready, true);
    assert.equal(groups[0].unsupported.length, 2);
    assert.equal(inspectDesign(root, '../outside.html').ready, false);
    assert.equal(inspectDesign(root, 'journey/a/b/c/d/e/one.jsx').ready, false);
  } finally { await rm(root, { recursive: true, force: true }); }
});
test('remote HTML merged even into partially hydrated collections, never falsely ready', () => {
  const local = [{ name: 'hero', designs: [{ rootRel: 'hero/a.html' }], unsupported: [] }];
  const groups = mergeRemote(local, ['hero/a.html', 'hero/b.html', 'journey/deep/index.html', '../secret.html'].map(key => ({ key: 'claude-design/sources/' + key })));
  assert.equal(groups.length, 2);
  assert.equal(groups[0].designs.length, 2);
  assert.equal(groups[0].designs[1].readiness.ready, false);
  assert.equal(groups[0].designs[1].remoteOnly, true);
});
test('CSS and scripts traverse dependencies and report external runtime checks', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'ccm-dependencies-'));
  try {
    await writeFile(path.join(root, 'index.html'), '<link href="style.css"><script src="https://example.invalid/code.js"></script>');
    await writeFile(path.join(root, 'style.css'), 'body {background:url("missing.png")}');
    const result = inspectDesign(root, 'index.html');
    assert.equal(result.ready, false);
    assert.deepEqual(result.issues, ['missing: missing.png']);
    assert.equal(result.runtimeCheckRequired, true);
  } finally { await rm(root, { recursive: true, force: true }); }
});
