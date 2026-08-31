/*
 * File: src/lib/cockpit-2d-blanks.js
 * Purpose:
 *  - Expose every locally extracted Cockpit3D 2D crystal template to the
 *    relief form without bundling proprietary source geometry.
 *  - Keep physical dimensions, safe margins and optional local preview GLBs
 *    beside the user-facing template id.
 */

export const COCKPIT_2D_BLANKS = {
  "2d-candle-100x60": { name: "2D Candle 100x60", width: 60, height: 80, depth: 60, border: 3, group: "Cockpit3D · Candle" },
  "2d-cut-corner-diamond-large-80x80": { name: "2D Cut Corner Diamond Large 80x80", width: 80, height: 80, depth: 80, border: 5, group: "Cockpit3D · Diamond" },
  "2d-cut-corner-diamond-small-50x50": { name: "2D Cut Corner Diamond Small 50x50", width: 50, height: 50, depth: 50, border: 2, group: "Cockpit3D · Diamond" },
  "2d-cut-corner-diamond-medium-60x60": { name: "2D Cut Corner Diamond Medium 60x60", width: 60, height: 60, depth: 60, border: 3, group: "Cockpit3D · Diamond" },
  "2d-heart-keychain": { name: "2D Heart Keychain", width: 35, height: 35, depth: 12, border: 1, group: "Cockpit3D · Heart", model: "2d-heart-keychain.glb" },
  "2d-heart-large-125x110": { name: "2D Heart Large 125x110", width: 125, height: 110, depth: 47, border: 1, group: "Cockpit3D · Heart", model: "2d-heart-large-125x110.glb" },
  "2d-heart-medium-100x90": { name: "2D Heart Medium 100x90", width: 100, height: 90, depth: 47, border: 1, group: "Cockpit3D · Heart", model: "2d-heart-medium-100x90.glb" },
  "2d-heart-necklace": { name: "2D Heart Necklace", width: 35, height: 35, depth: 8, border: 1, group: "Cockpit3D · Heart", model: "2d-heart-necklace.glb" },
  "2d-heart-small-80x70": { name: "2D Heart Small 80x70", width: 80, height: 70, depth: 38, border: 1, group: "Cockpit3D · Heart", model: "2d-heart-small-80x70.glb" },
  "2d-notched-crystal-180x130": { name: "2D Notched Crystal 180x130", width: 180, height: 130, depth: 30, border: 10, group: "Cockpit3D · Special" },
  "2d-ornament-diameter": { name: "2D Ornament Diameter", width: 80, height: 80, depth: 9.5, border: 1, group: "Cockpit3D · Ornament", model: "2d-ornament-diameter.glb" },
  "2d-prestige-iceberg-medium-flipped-170x140": { name: "2D Prestige Iceberg Medium Flipped 170x140", width: 137, height: 171, depth: 58, border: 1, group: "Cockpit3D · Prestige", model: "2d-prestige-iceberg-medium-flipped-170x140.glb" },
  "2d-prestige-iceberg-medium-170x140": { name: "2D Prestige Iceberg Medium 170x140", width: 137, height: 171, depth: 58, border: 1, group: "Cockpit3D · Prestige", model: "2d-prestige-iceberg-medium-170x140.glb" },
  "2d-prestige-iceberg-small-130x100": { name: "2D Prestige Iceberg Small 130x100", width: 105, height: 128, depth: 48, border: 1, group: "Cockpit3D · Prestige", model: "2d-prestige-iceberg-small-130x100.glb" },
  "2d-prestige-iceberg-small-flipped-130x100": { name: "2D Prestige Iceberg Small Flipped 130x100", width: 105, height: 128, depth: 48, border: 1, group: "Cockpit3D · Prestige", model: "2d-prestige-iceberg-small-flipped-130x100.glb" },
  "2d-prestige-new-large-flipped-200x160": { name: "2D Prestige New Large Flipped 200x160", width: 157, height: 202, depth: 58, border: 1, group: "Cockpit3D · Prestige", model: "2d-prestige-new-large-flipped-200x160.glb" },
  "2d-prestige-new-large-200x160": { name: "2D Prestige New Large 200x160", width: 157, height: 202, depth: 58, border: 1, group: "Cockpit3D · Prestige", model: "2d-prestige-new-large-200x160.glb" },
  "2d-rectangle-keychain": { name: "2D Rectangle Keychain", width: 20, height: 30, depth: 15, border: 2, group: "Cockpit3D · Rectangle" },
  "2d-rectangle-large-90x60": { name: "2D Rectangle Large 90x60", width: 60, height: 90, depth: 60, border: 3, group: "Cockpit3D · Rectangle" },
  "2d-rectangle-mantel-180x120": { name: "2D Rectangle Mantel 180x120", width: 120, height: 180, depth: 80, border: 6, group: "Cockpit3D · Rectangle" },
  "2d-rectangle-medium-80x50": { name: "2D Rectangle Medium 80x50", width: 50, height: 80, depth: 50, border: 3, group: "Cockpit3D · Rectangle" },
  "2d-rectangle-mini-mantel-150x100": { name: "2D Rectangle Mini Mantel 150x100", width: 100, height: 150, depth: 60, border: 6, group: "Cockpit3D · Rectangle" },
  "2d-rectangle-mini-presidential-220x160": { name: "2D Rectangle Mini Presidential 220x160", width: 160, height: 220, depth: 80, border: 10, group: "Cockpit3D · Rectangle" },
  "2d-rectangle-necklace": { name: "2D Rectangle Necklace", width: 35, height: 35, depth: 8, border: 1, group: "Cockpit3D · Rectangle" },
  "2d-rectangle-presidential-270x180": { name: "2D Rectangle Presidential 270x180", width: 180, height: 270, depth: 80, border: 10, group: "Cockpit3D · Rectangle" },
  "2d-rectangle-xlarge-120x80": { name: "2D Rectangle XLarge 120x80", width: 80, height: 120, depth: 60, border: 5, group: "Cockpit3D · Rectangle" },
  "2d-urn-150x120": { name: "2D URN 150x120", width: 120, height: 120, depth: 60, border: 6, group: "Cockpit3D · Special" },
};
