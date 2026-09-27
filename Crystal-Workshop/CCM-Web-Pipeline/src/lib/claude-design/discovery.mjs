/**
 * Purpose: Discover HTML entry points and inspect static dependencies without executing design code.
 * Shared by local/VPS listing and queue validation. Runtime loading still needs a render smoke test.
 */
import fs from 'node:fs';
import path from 'node:path';

const ignored = new Set(['node_modules', '.git', '.next', 'exported-videos', 'zip-files']);
const textTypes = /\.(html?|css|[cm]?js|jsx)$/i;
const sourceExtensions = /\.(html?|css|js|mjs|jsx|json|svg|png|jpe?g|webp|gif|avif|mp4|webm|mp3|wav|woff2?|ttf|otf)$/i;

/** Include collection assets to retain dynamic relative references, excluding executable tooling/secrets. */
export function collectDesignSources(root, rootRel, mimeFor) {
  const readiness = inspectDesign(root, rootRel);
  if (!readiness.ready) throw new Error('Source dependencies are incomplete.');
  const collection = rootRel.split('/')[0];
  if (!rootRel.includes('/') || collection.startsWith('.')) throw new Error('Use a named collection.');
  if (readiness.dependencies.some(file => !file.startsWith(collection + '/'))) throw new Error('Cross-collection dependencies require review.');
  const files = [];
  function walk(relative) {
    const directory = confined(root, relative);
    if (!directory) throw new Error('Invalid source directory.');
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (entry.name.startsWith('.') || ignored.has(entry.name) || /^(?:secrets?|credentials?|package(?:-lock)?\.json)$/i.test(entry.name)) continue;
      if (entry.isSymbolicLink()) throw new Error('Linked sources cannot be transferred.');
      const key = relative + '/' + entry.name;
      if (entry.isDirectory()) walk(key);
      else if (entry.isFile() && sourceExtensions.test(entry.name)) files.push({ path: confined(root, key), relativePath: key, role: 'source', mime: mimeFor(key) });
      if (files.length > 1000) throw new Error('Collection is too large.');
    }
  }
  walk(collection);
  return files;
}

function confined(root, relative) {
  if (typeof relative !== 'string' || /[\\\0]/.test(relative) || path.isAbsolute(relative)) return null;
  const base = fs.realpathSync(root);
  const target = path.resolve(base, relative);
  if (!target.startsWith(base + path.sep)) return null;
  let cursor = base;
  for (const part of path.relative(base, target).split(path.sep)) {
    cursor = path.join(cursor, part);
    if (fs.existsSync(cursor) && fs.lstatSync(cursor).isSymbolicLink()) return null;
  }
  return target;
}

/** Literal references only; dynamic expressions are reported as requiring runtime verification. */
export function references(text) {
  const result = new Set();
  for (const regex of [
    /\b(?:src|href|poster)\s*=\s*["']([^"']+)["']/g,
    /\b(?:fetch|import)\s*\(\s*["']([^"']+)["']/g,
    /\bfrom\s+["']([^"']+)["']/g,
    /url\(\s*["']?([^)'"\s]+)["']?\s*\)/g,
  ]) for (const match of text.matchAll(regex)) result.add(match[1]);
  // Claude's x-import attribute is a whitespace-delimited source list, not an ES import.
  for (const match of text.matchAll(/<x-import\b[^>]*\bfrom\s*=\s*["']([^"']+)["']/g)) {
    for (const name of match[1].split(/\s+/)) result.add(name);
  }
  return [...result];
}

export function inspectDesign(root, relative) {
  const issues = [], external = new Set(), visited = new Set();
  let dynamic = false;
  const entry = confined(root, relative);
  if (!entry || !/\.html?$/i.test(relative)) return { ready: false, issues: ['unsupported-entry'], dependencies: [], external: [] };
  const pending = [relative];
  while (pending.length) {
    const current = pending.pop();
    if (visited.has(current)) continue;
    if (visited.size >= 500) { issues.push('dependency-limit'); break; }
    visited.add(current);
    const absolute = confined(root, current);
    if (!absolute) { issues.push(`outside-root: ${current}`); continue; }
    if (!fs.existsSync(absolute) || !fs.statSync(absolute).isFile()) { issues.push(`missing: ${current}`); continue; }
    if (!textTypes.test(current)) continue;
    if (fs.statSync(absolute).size > 10 * 1024 * 1024) { issues.push(`inspection-limit: ${current}`); continue; }
    const text = fs.readFileSync(absolute, 'utf8');
    dynamic ||= /\b(?:fetch|import)\s*\(\s*[^\s"']/.test(text);
    for (const ref of references(text)) {
      if (/^(?:https?:)?\/\//i.test(ref)) { external.add(ref); continue; }
      if (/^(?:data:|blob:|#|mailto:|tel:)/i.test(ref) || ref.includes('{{')) continue;
      if (/^[a-z][a-z0-9+.-]*:/i.test(ref)) { issues.push(`unsupported-reference: ${ref}`); continue; }
      let decoded;
      try { decoded = decodeURIComponent(ref.split(/[?#]/)[0]); } catch { issues.push('invalid-reference'); continue; }
      if (!decoded) continue;
      // Root-relative browser requests resolve under the renderer's explicit serve root.
      const next = decoded.startsWith('/') ? decoded.slice(1) : path.posix.join(path.posix.dirname(current), decoded);
      pending.push(next);
    }
  }
  return { ready: issues.length === 0, issues: [...new Set(issues)], dependencies: [...visited].filter(file => file !== relative), external: [...external], runtimeCheckRequired: dynamic || external.size > 0 };
}

export function discoverLocal(root) {
  if (!fs.existsSync(root)) return [];
  const collections = new Map();
  function walk(directory, prefix = '', depth = 0) {
    if (depth > 20) return;
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (entry.isSymbolicLink() || entry.name.startsWith('.') || ignored.has(entry.name)) continue;
      const relative = prefix ? prefix + '/' + entry.name : entry.name;
      if (entry.isDirectory()) { walk(path.join(directory, entry.name), relative, depth + 1); continue; }
      if (!entry.isFile() || !/\.(html?|zip|jsx)$/i.test(entry.name)) continue;
      const name = relative.includes('/') ? relative.split('/')[0] : '(root)';
      const group = collections.get(name) || { name, designs: [], unsupported: [] };
      if (/\.html?$/i.test(entry.name)) {
        const info = fs.statSync(path.join(directory, entry.name));
        group.designs.push({ name: entry.name, rootRel: relative, relPath: name === '(root)' ? relative : relative.slice(name.length + 1), bytes: info.size, modified: info.mtimeMs, readiness: inspectDesign(root, relative) });
      } else group.unsupported.push({ rootRel: relative, reason: /\.zip$/i.test(entry.name) ? 'archive-needs-extraction' : 'component-needs-html-entry' });
      collections.set(name, group);
    }
  }
  walk(root);
  return [...collections.values()].sort((a, b) => a.name.localeCompare(b.name));
}

/** R2 inventory is discoverable before hydration; existence alone never claims readiness. */
export function mergeRemote(local, objects, prefix = 'claude-design/sources/') {
  const groups = new Map(local.map(group => [group.name, { ...group, designs: [...group.designs] }]));
  for (const object of objects) {
    const relative = object.key.slice(prefix.length);
    if (!object.key.startsWith(prefix) || !/\.html?$/i.test(relative) || relative.split('/').some(p => !p || p === '..' || p.startsWith('.'))) continue;
    const name = relative.includes('/') ? relative.split('/')[0] : '(root)';
    const group = groups.get(name) || { name, designs: [], unsupported: [] };
    if (!group.designs.some(design => design.rootRel === relative)) group.designs.push({ name: path.posix.basename(relative), relPath: relative.slice(name.length + 1), rootRel: relative, bytes: object.bytes, modified: object.modified, remoteOnly: true, readiness: { ready: false, issues: ['fetch-collection-first'] } });
    groups.set(name, group);
  }
  return [...groups.values()].sort((a, b) => a.name.localeCompare(b.name));
}
