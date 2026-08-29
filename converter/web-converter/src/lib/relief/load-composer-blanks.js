/*
 * ═══════════════════════════════════════════════════════════════
 * Composer Blank Loader
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/relief/load-composer-blanks.js
 * Purpose: Read the local Cockpit3D-derived 2D blank catalogue and project
 *          original OBJ front faces into browser-safe crop masks.
 */

import { readFile, readdir } from "node:fs/promises";
import path from "node:path";

import { RELIEF_BLANKS_DIR } from "@/lib/paths";

const COCKPIT_SHAPES_PATH = "C:\\ProgramData\\Cockpit 3D\\Shapes";
const FALLBACK_BLANKS = [
  {
    id: "2d-rectangle-medium-80x50",
    name: "2D Rectangle Medium 80x50",
    width: 50,
    height: 80,
    depth: 50,
    border: [3, 3, 3],
    bevel: 3,
    family: "rectangle",
    maskPoints: null,
  },
];

function familyOf(blank) {
  const name = blank.name.toLowerCase();
  if (name.includes("heart")) return "heart";
  if (name.includes("prestige")) return "prestige";
  if (name.includes("ornament")) return "ornament";
  if (name.includes("diamond")) return "diamond";
  if (name.includes("rectangle") || name.includes("candle")) return "rectangle";
  return "special";
}

async function objectFilesIn(directory) {
  const objects = new Map();
  async function visit(current) {
    const entries = await readdir(current, { withFileTypes: true });
    await Promise.all(
      entries.map(async (entry) => {
        const entryPath = path.join(current, entry.name);
        if (entry.isDirectory()) await visit(entryPath);
        else if (entry.isFile() && entry.name.toLowerCase().endsWith(".obj")) {
          objects.set(path.parse(entry.name).name, entryPath);
        }
      }),
    );
  }
  await visit(directory);
  return objects;
}

function signedArea(points) {
  return points.reduce((sum, point, index) => {
    const next = points[(index + 1) % points.length];
    return sum + point[0] * next[1] - next[0] * point[1];
  }, 0);
}

function simplify(points, tolerance = 0.0018) {
  if (points.length < 4) return points;
  const kept = points.filter((current, index) => {
    const previous = points[(index - 1 + points.length) % points.length];
    const next = points[(index + 1) % points.length];
    const cross = Math.abs(
      (current[0] - previous[0]) * (next[1] - current[1]) -
        (current[1] - previous[1]) * (next[0] - current[0]),
    );
    return cross > tolerance || index % 4 === 0;
  });
  return kept.length >= 3 ? kept : points;
}

/** Project the largest front-cap boundary to normalized XY crop coordinates. */
async function readSilhouette(objectPath) {
  const source = await readFile(objectPath, "utf8");
  const vertices = [];
  const faces = [];
  for (const line of source.split(/\r?\n/)) {
    if (line.startsWith("v ")) {
      const [, x, y, z] = line.trim().split(/\s+/).map(Number);
      vertices.push([x, y, z]);
    } else if (line.startsWith("f ")) {
      faces.push(
        line
          .trim()
          .slice(2)
          .split(/\s+/)
          .map((token) => Number(token.split("/")[0]) - 1),
      );
    }
  }
  if (!vertices.length || !faces.length) return null;

  const zValues = vertices.map((vertex) => vertex[2]);
  const maximumZ = Math.max(...zValues);
  const minimumZ = Math.min(...zValues);
  const tolerance = Math.max(0.0001, (maximumZ - minimumZ) * 0.0001);

  function boundaryAt(zPlane) {
    const counts = new Map();
    for (const face of faces) {
      if (!face.every((index) => Math.abs(vertices[index][2] - zPlane) <= tolerance)) continue;
      for (let index = 0; index < face.length; index += 1) {
        const first = face[index];
        const second = face[(index + 1) % face.length];
        const key = first < second ? `${first}:${second}` : `${second}:${first}`;
        const old = counts.get(key);
        counts.set(key, old ? { ...old, count: old.count + 1 } : { first, second, count: 1 });
      }
    }
    return [...counts.values()].filter((edge) => edge.count === 1);
  }

  const front = boundaryAt(maximumZ);
  const edges = front.length ? front : boundaryAt(minimumZ);
  if (!edges.length) return null;
  const adjacency = new Map();
  for (const { first, second } of edges) {
    adjacency.set(first, [...(adjacency.get(first) || []), second]);
    adjacency.set(second, [...(adjacency.get(second) || []), first]);
  }

  const remaining = new Set(edges.flatMap(({ first, second }) => [first, second]));
  const loops = [];
  while (remaining.size) {
    const start = remaining.values().next().value;
    const loop = [start];
    let previous = null;
    let current = start;
    for (let safety = 0; safety < edges.length + 2; safety += 1) {
      const next = (adjacency.get(current) || []).find((candidate) => candidate !== previous);
      if (next === undefined || next === start) break;
      loop.push(next);
      previous = current;
      current = next;
    }
    loop.forEach((index) => remaining.delete(index));
    if (loop.length >= 3) loops.push(loop.map((index) => vertices[index].slice(0, 2)));
  }
  if (!loops.length) return null;

  const outline = loops.sort(
    (first, second) => Math.abs(signedArea(second)) - Math.abs(signedArea(first)),
  )[0];
  const xs = outline.map(([x]) => x);
  const ys = outline.map(([, y]) => y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return simplify(
    outline.map(([x, y]) => [
      Number(((x - minX) / Math.max(maxX - minX, 0.0001)).toFixed(5)),
      Number(((maxY - y) / Math.max(maxY - minY, 0.0001)).toFixed(5)),
    ]),
  );
}

/** Load the local 2D catalogue without copying proprietary geometry into the app. */
export async function loadComposerBlanks() {
  let blanks = FALLBACK_BLANKS;
  try {
    const catalogue = JSON.parse(
      await readFile(path.join(RELIEF_BLANKS_DIR, "blanks.json"), "utf8"),
    );
    blanks = catalogue.blanks.filter((blank) => blank.id.startsWith("2d-") && blank.type !== 8);
  } catch {
    return FALLBACK_BLANKS;
  }

  let objectFiles = new Map();
  try {
    objectFiles = await objectFilesIn(COCKPIT_SHAPES_PATH);
  } catch {
    // The full size catalogue remains useful on machines without Cockpit3D.
  }

  return Promise.all(
    blanks.map(async (blank) => {
      let maskPoints = null;
      if (blank.sourceShape && objectFiles.has(blank.sourceShape)) {
        try {
          maskPoints = await readSilhouette(objectFiles.get(blank.sourceShape));
        } catch {
          maskPoints = null;
        }
      }
      return {
        id: blank.id,
        name: blank.name,
        width: blank.width,
        height: blank.height,
        depth: blank.depth,
        border: blank.border || null,
        bevel: blank.bevel || null,
        family: familyOf(blank),
        sourceShape: blank.sourceShape || null,
        maskPoints,
      };
    }),
  );
}
