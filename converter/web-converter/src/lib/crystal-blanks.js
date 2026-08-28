/*
 * ═══════════════════════════════════════════════════════════════
 * Crystal Blanks
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/crystal-blanks.js
 * Purpose: Every blank a model can be fitted into, in one list.
 *
 * Mirrors CRYSTAL_TEMPLATES in
 * pipeline-converter/code/utils/printer_dxf.py. The Python side is
 * authoritative for the actual fit; this copy exists so the browser can name
 * the sizes and show usable millimetres without shelling out.
 *
 * Keys are WIDTHxHEIGHTxDEPTH. The acm.is shop lists its sizes
 * HEIGHT x WIDTH x DEPTH instead - "rectangle-crystal-large-landscape" is
 * "60 x 90 x 60 mm" and wide-format, so 90 is its width - which is why these
 * keys have the first two numbers swapped relative to the product pages.
 */

export const CRYSTAL_BLANKS = {
  // Original set, unchanged - these keep their original borders so nothing
  // already in production shifts.
  "60x80x30": { width: 60, height: 80, depth: 30, border: 5, group: "Standard" },
  "60x80x40": { width: 60, height: 80, depth: 40, border: 5, group: "Standard" },
  "80x50x50": { width: 80, height: 50, depth: 50, border: 3, group: "Standard" },
  "120x80x40": { width: 120, height: 80, depth: 40, border: 3, group: "Standard" },
  "90x60x60": { width: 90, height: 60, depth: 60, border: 5, group: "Standard" },

  "40x60x40": { width: 40, height: 60, depth: 40, border: 5, group: "Rectangle · portrait", name: "Small" },
  "50x80x50": { width: 50, height: 80, depth: 50, border: 5, group: "Rectangle · portrait", name: "Medium" },
  "60x90x60": { width: 60, height: 90, depth: 60, border: 5, group: "Rectangle · portrait", name: "Large" },
  "80x120x60": { width: 80, height: 120, depth: 60, border: 5, group: "Rectangle · portrait", name: "XL" },
  "100x150x80": { width: 100, height: 150, depth: 80, border: 5, group: "Rectangle · portrait", name: "Mini mantel" },
  "120x180x80": { width: 120, height: 180, depth: 80, border: 5, group: "Rectangle · portrait", name: "Mantel" },

  "60x40x40": { width: 60, height: 40, depth: 40, border: 5, group: "Rectangle · landscape", name: "Small" },
  "120x80x60": { width: 120, height: 80, depth: 60, border: 5, group: "Rectangle · landscape", name: "XL" },
  "150x100x80": { width: 150, height: 100, depth: 80, border: 5, group: "Rectangle · landscape", name: "Mini mantel" },
  "180x120x80": { width: 180, height: 120, depth: 80, border: 5, group: "Rectangle · landscape", name: "Mantel" },

  "100x130x50": { width: 100, height: 130, depth: 50, border: 5, group: "Prestige", name: "Small" },
  "140x170x60": { width: 140, height: 170, depth: 60, border: 5, group: "Prestige", name: "Medium" },
  "160x200x60": { width: 160, height: 200, depth: 60, border: 5, group: "Prestige", name: "Large" },

  // The notch sits at the base, outside the engravable area, so the plain
  // bounding box is the right model for fitting.
  "100x150x30": { width: 100, height: 150, depth: 30, border: 5, group: "Notched · portrait", name: "Small" },
  "130x180x30": { width: 130, height: 180, depth: 30, border: 5, group: "Notched · portrait", name: "Medium" },
  "150x100x30": { width: 150, height: 100, depth: 30, border: 5, group: "Notched · landscape", name: "Small" },
  "180x130x30": { width: 180, height: 130, depth: 30, border: 5, group: "Notched · landscape", name: "Medium" },

  "40x40x40": { width: 40, height: 40, depth: 40, border: 5, group: "Cube" },
  "50x50x50": { width: 50, height: 50, depth: 50, border: 5, group: "Cube" },
  "60x60x60": { width: 60, height: 60, depth: 60, border: 5, group: "Cube" },
  "80x80x80": { width: 80, height: 80, depth: 80, border: 5, group: "Cube" },
  "100x100x100": { width: 100, height: 100, depth: 100, border: 5, group: "Cube" },

  "20x30x15": { width: 20, height: 30, depth: 15, border: 2, group: "Keychain", name: "Rectangle" },
  "35x35x12": { width: 35, height: 35, depth: 12, border: 2, group: "Keychain", name: "Heart (bounding box)" },
};

/*
 * Circle and heart blanks are deliberately absent. The fitter scales a model
 * into a rectangular box, so a curved blank would take a cloud that overflows
 * its edges. Those need a mask, not a bounding box.
 */

export const CRYSTAL_BLANK_NAMES = Object.keys(CRYSTAL_BLANKS);

/** Engravable millimetres inside a blank, once its border is off every side. */
export function usableSpace(templateName) {
  const blank = CRYSTAL_BLANKS[templateName];
  if (!blank) return null;
  return {
    width: blank.width - 2 * blank.border,
    height: blank.height - 2 * blank.border,
    depth: blank.depth - 2 * blank.border,
  };
}

/** Which way up a blank sits, worked out from its own proportions. */
export function orientationOf(templateName) {
  const blank = CRYSTAL_BLANKS[templateName];
  if (!blank) return null;
  if (blank.width === blank.height) return "square";
  return blank.height > blank.width ? "portrait" : "landscape";
}

/**
 * Options for a `select` field, grouped and labelled.
 *
 * Twenty-nine bare keys in a dropdown is unreadable, so each carries the
 * usable space it actually offers - which is the number that decides whether
 * a subject fits.
 */
export function blankOptions({ includeNone = true, noneLabel = "none" } = {}) {
  const options = includeNone ? [{ value: "", label: noneLabel, labelIs: "ekkert — ákveða síðar" }] : [];
  const groupIs = {
    Standard: "Hefðbundinn",
    "Rectangle · portrait": "Rétthyrningur · lóðréttur",
    "Rectangle · landscape": "Rétthyrningur · láréttur",
    Prestige: "Prestige",
    "Notched · portrait": "Skorinn · lóðréttur",
    "Notched · landscape": "Skorinn · láréttur",
    Cube: "Teningur",
    Keychain: "Lyklakippa",
  };
  const nameIs = {
    Small: "Lítill",
    Medium: "Miðlungs",
    Large: "Stór",
    XL: "XL",
    "Mini mantel": "Lítill borðkristall",
    Mantel: "Borðkristall",
    Rectangle: "Rétthyrningur",
    "Heart (bounding box)": "Hjarta (ytri mörk)",
  };

  for (const [key, blank] of Object.entries(CRYSTAL_BLANKS)) {
    const space = usableSpace(key);
    const name = blank.name ? ` ${blank.name}` : "";
    options.push({
      value: key,
      label: `${blank.group}${name} — ${key} (${space.width}×${space.height}×${space.depth} preset usable)`,
      labelIs: `${groupIs[blank.group] || blank.group}${blank.name ? ` ${nameIs[blank.name] || blank.name}` : ""} — ${key} (${space.width}×${space.height}×${space.depth} mm sjálfgefið nýtanlegt)`,
    });
  }
  return options;
}
