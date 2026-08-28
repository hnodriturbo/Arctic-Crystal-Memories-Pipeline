/*
 * ═══════════════════════════════════════════════════════════════
 * Image Pipeline Catalogue
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/image/catalog.js
 * Purpose: The photo clean-up chain - its three stages, every option they
 *          take, and the order they run in.
 *
 * Shared by two callers: the image pipeline's own tab, and the Meshy tab's
 * inline "clean it up on the way" controls. One definition, so a photo
 * cleaned in either place comes out identical.
 */

export const PHOTO_TYPES = [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"];

/**
 * Fixed order, and it matters.
 *
 * Restore faces at native resolution first, upscale the restored image, then
 * cut the background out last so the silhouette is traced at the largest size
 * available. Cutting first would upscale a matte whose edge decisions are
 * already baked in.
 */
export const IMAGE_STAGES = [
  { id: "enhance", script: "enhance.py", label: "Restore", toggle: "enhance" },
  { id: "upscale", script: "upscale.py", label: "Upscale", toggle: "upscale" },
  { id: "remove_bg", script: "remove_bg.py", label: "Cut out", toggle: "remove_bg" },
];

export const IMAGE_FIELD_GROUPS = [
  { id: "restore", emoji: "✨", label: "Restore", hint: "Repair a soft or aged photograph." },
  { id: "upscale", emoji: "🔍", label: "Upscale", hint: "More pixels for Meshy to read edges from." },
  { id: "cutout", emoji: "✂️", label: "Cut out", hint: "Isolate the subject on transparency." },
];

export const IMAGE_FIELDS = [
  // ── Restore ───────────────────────────────────────────────────────────────
  {
    name: "enhance",
    emoji: "✨",
    label: "Restore the photograph",
    group: "restore",
    type: "boolean",
    default: false,
    help: "Worth it on old or soft photographs. Skip it on a sharp modern one.",
  },
  {
    name: "enhance_engine",
    emoji: "🛠️",
    label: "Restore engine",
    group: "restore",
    type: "select",
    options: ["auto", "gfpgan", "pillow"],
    default: "auto",
    help: "auto picks GFPGAN where torch is installed, pillow adjustments otherwise.",
  },
  {
    name: "fidelity",
    emoji: "🎚️",
    label: "Face fidelity",
    group: "restore",
    type: "number",
    default: 0.7,
    min: 0,
    max: 1,
    step: 0.05,
    help: "GFPGAN only. 0 rebuilds aggressively, 1 stays close to the original face.",
  },
  {
    name: "brightness",
    emoji: "☀️",
    label: "Brightness",
    group: "restore",
    type: "number",
    default: 1,
    min: 0.2,
    max: 2,
    step: 0.05,
  },
  {
    name: "contrast",
    emoji: "◐",
    label: "Contrast",
    group: "restore",
    type: "number",
    default: 1,
    min: 0.2,
    max: 2,
    step: 0.05,
    help: "Contrast and sharpness are what Meshy actually reads as form.",
  },
  {
    name: "sharpness",
    emoji: "🔪",
    label: "Sharpness",
    group: "restore",
    type: "number",
    default: 1,
    min: 0.2,
    max: 3,
    step: 0.05,
  },
  {
    name: "color",
    emoji: "🎨",
    label: "Saturation",
    group: "restore",
    type: "number",
    default: 1,
    min: 0,
    max: 2,
    step: 0.05,
  },

  // ── Upscale ───────────────────────────────────────────────────────────────
  {
    name: "upscale",
    emoji: "🔍",
    label: "Upscale the photograph",
    group: "upscale",
    type: "boolean",
    default: false,
    help: "Skipped automatically when the photo already exceeds the target.",
  },
  {
    name: "upscale_engine",
    emoji: "⚙️",
    label: "Upscale engine",
    group: "upscale",
    type: "select",
    options: ["auto", "realesrgan", "lanczos"],
    default: "auto",
    help: "Real-ESRGAN needs torch. On a machine without it, auto resolves to lanczos.",
  },
  {
    name: "upscale_target",
    emoji: "📏",
    label: "Target long edge (px)",
    group: "upscale",
    type: "number",
    default: 2048,
    min: 512,
    max: 6000,
    step: 128,
  },

  // ── Cut out ───────────────────────────────────────────────────────────────
  {
    name: "remove_bg",
    emoji: "✂️",
    label: "Remove the background",
    group: "cutout",
    type: "boolean",
    default: true,
    help: "The single biggest win before Meshy - it stops the sofa behind a shoulder becoming part of the bust.",
  },
  {
    name: "remove_bg_model",
    emoji: "🧠",
    label: "Cut-out model",
    group: "cutout",
    type: "select",
    options: [
      "birefnet-portrait",
      "birefnet-general",
      "isnet-general-use",
      "u2net_human_seg",
      "u2net",
      "u2netp",
    ],
    default: "birefnet-portrait",
    help:
      "BiRefNet gives the cleanest edges but uses the most RAM. isnet-general-use is the balanced CPU choice; u2netp is the smallest safe fallback on a constrained VPS.",
    optionHelp: {
      "birefnet-portrait": "Best portrait and hair detail; roughly a 1 GB model and the heaviest CPU/RAM option.",
      "birefnet-general": "High-quality cut-outs for objects and buildings; roughly a 1 GB model.",
      "isnet-general-use": "Balanced general-purpose CPU model with a much smaller download and memory footprint.",
      u2net_human_seg: "Older person-specific model with softer edges and moderate resource use.",
      u2net: "Original general-purpose U²-Net model; reliable but older.",
      u2netp: "Tiny U²-Net variant; lowest RAM and disk use, with less fine-edge detail.",
    },
  },
  {
    name: "alpha_matting",
    emoji: "💇",
    label: "Alpha matting",
    group: "cutout",
    type: "boolean",
    default: false,
    help: "Slower, but recovers fine hair against a busy background.",
  },
];

/** Default form state for the chain. */
export function defaultImageValues() {
  return Object.fromEntries(IMAGE_FIELDS.map((field) => [field.name, field.default]));
}

/** Which stages the current form actually asks for, in canonical order. */
export function selectedStages(values = {}) {
  return IMAGE_STAGES.filter((stage) => Boolean(values[stage.toggle]));
}

/** Turn the form into argv for one stage, given resolved input and output paths. */
export function buildStageArgs(stageId, values, inputPath, outputPath) {
  const args = ["--input", inputPath, "--output", outputPath];

  if (stageId === "enhance") {
    args.push("--engine", values.enhance_engine || "auto");
    args.push("--fidelity", String(values.fidelity ?? 0.7));
    args.push("--brightness", String(values.brightness ?? 1));
    args.push("--contrast", String(values.contrast ?? 1));
    args.push("--sharpness", String(values.sharpness ?? 1));
    args.push("--color", String(values.color ?? 1));
  }

  if (stageId === "upscale") {
    args.push("--engine", values.upscale_engine || "auto");
    args.push("--target", String(values.upscale_target || 2048));
  }

  if (stageId === "remove_bg") {
    args.push("--model", values.remove_bg_model || "birefnet-portrait");
    if (values.alpha_matting) args.push("--alpha-matting");
  }

  return args;
}
