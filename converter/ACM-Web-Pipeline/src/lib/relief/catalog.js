/*
 * ═══════════════════════════════════════════════════════════════
 * Relief Pipeline Catalogue
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/relief/catalog.js
 * Purpose: The 2.5D chain - its two stages, every option they take, and how
 *          the form becomes argv.
 *
 * Same shape as lib/image/catalog.js, so OptionFields renders it without
 * knowing anything about relief. One definition, read by both the form and
 * the API route, so a new script flag is added in exactly one place.
 */

import { blankOptions } from "@/lib/crystal-blanks";

export const PHOTO_TYPES = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"];

/**
 * Two stages, both always run.
 *
 * Unlike the image chain these are not individually optional: a depth map
 * with no mesh is not a deliverable, and a mesh needs a depth map to exist.
 * They are listed separately so the console shows which one is working.
 */
export const RELIEF_STAGES = [
  { id: "depth", script: "depth_map.py", label: "Depth map" },
  { id: "mesh", script: "depth_to_mesh.py", label: "Relief mesh" },
];

export const RELIEF_FIELD_GROUPS = [
  { id: "depth", emoji: "🧠", label: "Depth model", hint: "The one stage with a model in it." },
  { id: "quality", emoji: "🔬", label: "Depth quality", hint: "Slower and better, or faster and flatter." },
  { id: "size", emoji: "💠", label: "Crystal fit", hint: "Which blank, and how much of its depth to use." },
  { id: "mesh", emoji: "🕸️", label: "Mesh", hint: "Resolution and silhouette of the relief surface." },
  {
    id: "sampling",
    label: "Laser point cloud",
    hint: "Production sampling after the GLB and OBJ have been built. Preview dots stay fixed at 0.08 mm.",
  },
  {
    id: "layers",
    label: "Depth layers and toning",
    hint: "How continuous relief becomes the final layered engraving cloud.",
  },
];

export const RELIEF_FIELDS = [
  // ── Depth model ───────────────────────────────────────────────────────────
  {
    name: "engine",
    emoji: "🧠",
    label: "Depth engine",
    group: "depth",
    type: "select",
    options: ["depth-anything", "marigold"],
    default: "depth-anything",
    help: "Depth Anything is fast and dependable. Marigold is slower with finer facial relief.",
    optionHelp: {
      "depth-anything": "Feed-forward, seconds on GPU. The right default for almost every photograph.",
      marigold: "Diffusion-based and much slower, but resolves soft cheek and brow relief a portrait lives on.",
    },
  },
  {
    name: "model",
    emoji: "📦",
    label: "Checkpoint size",
    group: "depth",
    type: "select",
    options: ["large", "base", "small"],
    default: "large",
    help: "Large is ~1.3 GB and the quality choice. Drop to base only on a memory-constrained box.",
    showWhen: (values) => values.engine === "depth-anything",
  },
  {
    name: "device",
    emoji: "⚙️",
    label: "Device",
    group: "depth",
    type: "select",
    options: ["auto", "cpu", "cuda"],
    default: "auto",
    help: "auto is CUDA when it exists and CPU otherwise. An explicit cuda fails loudly on a CPU-only box.",
  },
  {
    name: "steps",
    emoji: "🔁",
    label: "Marigold steps",
    group: "depth",
    type: "number",
    default: 4,
    min: 1,
    max: 50,
    step: 1,
    showWhen: (values) => values.engine === "marigold",
  },
  {
    name: "ensemble",
    emoji: "🎲",
    label: "Marigold ensemble",
    group: "depth",
    type: "number",
    default: 5,
    min: 1,
    max: 20,
    step: 1,
    help: "Averages several predictions. The main quality lever, and linear in time.",
    showWhen: (values) => values.engine === "marigold",
  },

  // ── Depth quality ─────────────────────────────────────────────────────────
  {
    name: "resolution",
    emoji: "📐",
    label: "Inference size (px)",
    group: "quality",
    type: "number",
    default: 0,
    min: 0,
    max: 1536,
    step: 128,
    help:
      "0 uses the checkpoint's own training size, which is what you want. Measured: 1024px costs 2.6x the time for 0.97x the detail. An experiment knob, not a quality knob.",
  },
  {
    name: "smooth",
    emoji: "🫧",
    label: "Smoothing (px)",
    group: "quality",
    type: "number",
    default: 1,
    min: 0,
    max: 8,
    step: 0.25,
    help: "Depth noise becomes physical bumps on the surface, so a little is wanted. Too much flattens the face.",
  },
  {
    name: "clip_percent",
    emoji: "✂️",
    label: "Percentile clip (%)",
    group: "quality",
    type: "number",
    default: 1,
    min: 0,
    max: 10,
    step: 0.25,
    help: "Ignores this much at each end before stretching, so one stray pixel cannot eat the whole range.",
  },
  {
    name: "mask_from_alpha",
    emoji: "✂️",
    label: "Flatten the background",
    group: "quality",
    type: "boolean",
    default: true,
    help: "Uses the cut-out's alpha, so only the subject gets relief. Needs a PNG from the image pipeline.",
  },
  {
    name: "edge_profile",
    emoji: "✂️",
    label: "Silhouette profile",
    group: "quality",
    type: "select",
    options: ["feathered", "soft", "standard"],
    default: "feathered",
    help: "What the depth does at the subject's outline. Carried over from pipeline-old's DEPTH_PROFILES.",
    optionHelp: {
      feathered:
        "Blurs the alpha before weighting, so the outline fades. The only one that works on a hard binary mask.",
      soft: "Alpha used directly as a weight. Natural, but needs a mask that already has soft edges.",
      standard: "Hard binary cut. Leaves a geometric cliff at the outline that shows up as a wall in the mesh.",
    },
    showWhen: (values) => values.mask_from_alpha,
  },
  {
    name: "feather",
    emoji: "🪶",
    label: "Feather (px)",
    group: "quality",
    type: "number",
    default: 0,
    min: 0,
    max: 40,
    step: 1,
    help: "0 scales the blur to the image, 0.26% of the long edge - the ratio pipeline-old settled on.",
    showWhen: (values) => values.mask_from_alpha && values.edge_profile === "feathered",
  },
  {
    name: "invert",
    emoji: "🔄",
    label: "Invert the relief",
    group: "quality",
    type: "boolean",
    default: false,
    help: "Only if the result comes out inside-out - nose sunken instead of raised.",
  },

  // ── Crystal fit ───────────────────────────────────────────────────────────
  {
    name: "template",
    emoji: "💠",
    label: "Crystal blank",
    group: "size",
    type: "select",
    options: blankOptions({ includeNone: false }),
    default: "60x80x40",
    help: "Width x height x depth in mm. The relief is fitted inside, never cropped to fill.",
  },
  {
    name: "border",
    emoji: "🖼️",
    label: "Crystal margin (mm)",
    group: "size",
    type: "number",
    default: 1,
    min: 0.1,
    step: 0.1,
    help: "Unengraved margin on every side.",
  },
  {
    name: "relief_depth",
    emoji: "🧊",
    label: "Relief depth (mm)",
    group: "size",
    type: "number",
    default: 0,
    min: 0,
    step: 1,
    help:
      "Nearest point to deepest. 0 uses the blank's whole usable depth. A relief wants far less than a full 3D bust - try 10-20 mm on a portrait.",
  },

  // ── Mesh ──────────────────────────────────────────────────────────────────
  {
    name: "grid",
    emoji: "🕸️",
    label: "Grid long edge (vertices)",
    group: "mesh",
    type: "number",
    default: 512,
    min: 0,
    max: 2048,
    step: 64,
    help: "512 is ~400k vertices - plenty for the preview and for the sampler to read. 0 keeps full resolution.",
  },
  {
    name: "alpha_threshold",
    emoji: "🔲",
    label: "Silhouette threshold",
    group: "mesh",
    type: "number",
    default: 0.5,
    min: 0,
    max: 1,
    step: 0.05,
    help: "Cut-out alpha below this gets no geometry at all.",
  },
  {
    name: "backing",
    emoji: "🧱",
    label: "Backing (mm)",
    group: "mesh",
    type: "number",
    default: 0,
    min: 0,
    max: 40,
    step: 1,
    help:
      "Closes the relief into a solid for 3D printing. Never reaches the engraver - the OBJ handed on is always the bare surface.",
  },
  {
    name: "vertex_color",
    emoji: "🎨",
    label: "Vertex colour",
    group: "mesh",
    type: "select",
    options: ["luma", "rgb", "none"],
    default: "luma",
    help: "luma drives dot brightness in the preview the way toning drives dot density in the glass.",
  },

  // ── Printer point cloud ──────────────────────────────────────────────────
  {
    name: "point_budget_mode",
    label: "Point budget",
    group: "sampling",
    type: "select",
    options: [
      { value: "auto", label: "Automatic · 250k–1M from image size" },
      { value: "manual", label: "Manual target" },
      { value: "spacing", label: "Spacing only" },
    ],
    default: "auto",
    help:
      "Automatic scales from 250,000 points for a small source to 1,000,000 for four megapixels or more.",
  },
  {
    name: "point_target",
    label: "Manual point target",
    group: "sampling",
    type: "number",
    default: 500000,
    min: 250000,
    max: 1000000,
    step: 50000,
    showWhen: (values) => values.point_budget_mode === "manual",
  },
  {
    name: "point_spacing",
    label: "Point spacing XY (mm)",
    group: "sampling",
    type: "number",
    default: 0.08,
    min: 0.01,
    max: 1,
    step: 0.01,
    help: "The reference centre-to-centre spacing. It is not the rendered dot diameter.",
  },
  {
    name: "minimum_point_distance",
    label: "Minimum point distance (mm)",
    group: "sampling",
    type: "number",
    default: 0.08,
    min: 0.01,
    max: 1,
    step: 0.01,
    help: "Safety floor used by the thinning grid so dots are not over-burned.",
  },
  {
    name: "z_distance",
    label: "Z distance before layers (mm)",
    group: "sampling",
    type: "number",
    default: 0,
    min: 0,
    max: 1,
    step: 0.01,
    help: "0 reuses XY spacing. This is separate from final layer spacing.",
  },
  {
    name: "maximum_points",
    label: "Final safety cap",
    group: "sampling",
    type: "number",
    default: 1000000,
    min: 250000,
    max: 1000000,
    step: 50000,
    help: "A deterministic final cap. Automatic mode never asks for more than this value.",
  },
  {
    name: "layers",
    label: "Fixed layer count",
    group: "layers",
    type: "number",
    default: 8,
    min: 0,
    max: 128,
    step: 1,
    help: "0 keeps continuous depth unless layer spacing is set.",
  },
  {
    name: "layer_spacing",
    label: "Layer distance (mm)",
    group: "layers",
    type: "number",
    default: 0.08,
    min: 0,
    max: 2,
    step: 0.01,
    help: "When above 0 this overrides fixed layer count.",
  },
  {
    name: "stagger",
    label: "Layer stagger",
    group: "layers",
    type: "number",
    default: 2,
    min: 1,
    max: 8,
    step: 1,
    help: "Offsets alternate planes so points do not form visible columns.",
  },
  {
    name: "toning",
    label: "Toning gamma",
    group: "layers",
    type: "number",
    default: 1.8,
    min: 0.2,
    max: 5,
    step: 0.1,
    help: "Cockpit3D reference is 1.8; higher values deepen sparse shadow regions.",
  },
  {
    name: "density_floor",
    label: "Dark-area density floor",
    group: "layers",
    type: "number",
    default: 0.05,
    min: 0,
    max: 1,
    step: 0.05,
  },
  {
    name: "invert_texture",
    label: "Invert density image",
    group: "layers",
    type: "boolean",
    default: false,
    help: "Treat dark pixels as dense instead of bright pixels.",
  },
  {
    name: "sampling_seed",
    label: "Sampling seed",
    group: "layers",
    type: "number",
    default: 7,
    min: 0,
    step: 1,
    help: "The same source, settings and seed reproduce the same point placement.",
  },
  {
    name: "write_xyz",
    label: "Write XYZ preview",
    group: "layers",
    type: "boolean",
    default: true,
  },
];

/** Default form state for the chain. */
export function defaultReliefValues() {
  return Object.fromEntries(RELIEF_FIELDS.map((field) => [field.name, field.default]));
}

/** argv for depth_map.py, given resolved input and output paths. */
export function buildDepthArgs(values, inputPath, outputPath) {
  const args = [
    "--input",
    inputPath,
    "--output",
    outputPath,
    "--engine",
    values.engine || "depth-anything",
    "--device",
    values.device || "auto",
    "--resolution",
    String(values.resolution ?? 0),
    "--smooth",
    String(values.smooth ?? 1),
    "--clip-percent",
    String(values.clip_percent ?? 1),
  ];

  if (values.engine === "marigold") {
    args.push("--steps", String(values.steps ?? 4));
    args.push("--ensemble", String(values.ensemble ?? 5));
  } else {
    args.push("--model", values.model || "large");
  }

  if (values.mask_from_alpha) {
    args.push("--mask-from-alpha");
    args.push("--edge-profile", values.edge_profile || "feathered");
    args.push("--feather", String(values.feather ?? 0));
  }
  if (values.invert) args.push("--invert");
  return args;
}

/** argv for depth_to_mesh.py. The OBJ is always written - it is the handoff. */
export function buildMeshArgs(values, depthPath, photoPath, glbPath, objPath) {
  const args = [
    "--depth",
    depthPath,
    "--photo",
    photoPath,
    "--output",
    glbPath,
    "--obj",
    objPath,
    "--template",
    values.template || "60x80x40",
    "--border",
    String(values.border ?? 1),
    "--relief-depth",
    String(values.relief_depth ?? 0),
    "--grid",
    String(values.grid ?? 512),
    "--alpha-threshold",
    String(values.alpha_threshold ?? 0.5),
    "--vertex-color",
    values.vertex_color || "luma",
  ];

  if (Number(values.backing) > 0) args.push("--backing", String(values.backing));
  return args;
}

/**
 * Scale the automatic output budget from source image area.
 * 0.25 MP maps to 250k, 4 MP maps to 1M, and values are rounded to 50k.
 */
export function automaticPointBudget(width, height, maximum = 1000000) {
  const megapixels = Math.max(0, Number(width) * Number(height)) / 1_000_000;
  const progress = Math.min(1, Math.max(0, (megapixels - 0.25) / 3.75));
  const budget = Math.round((250000 + progress * 750000) / 50000) * 50000;
  return Math.min(Math.max(250000, budget), Math.max(250000, Number(maximum) || 1000000));
}

/** argv for the existing pipeline-converter sampler, with 2.5D axes locked. */
export function buildPointCloudArgs(values, { objPath, photoPath, outputDir, pointBudget }) {
  const [width, height, depth] = String(values.template || "60x80x40").split("x").map(Number);
  const manual = values.point_budget_mode === "manual" ? Number(values.point_target) : pointBudget;
  const points = values.point_budget_mode === "spacing" ? 0 : Math.max(250000, manual || 250000);
  const maximum = Math.min(
    1000000,
    Math.max(250000, Number(values.maximum_points) || 1000000),
  );
  const args = [
    "--file",
    objPath,
    "--template",
    "60x80x40",
    "--width",
    String(width || 60),
    "--height",
    String(height || 80),
    "--depth",
    String(depth || 40),
    "--border",
    String(values.border ?? 1),
    "--points",
    String(points),
    "--spacing",
    String(values.point_spacing ?? 0.08),
    "--min-distance",
    String(values.minimum_point_distance ?? 0.08),
    "--z-distance",
    String(values.z_distance ?? 0),
    "--max-points",
    String(Math.min(points || maximum, maximum)),
    "--layers",
    String(values.layers ?? 8),
    "--layer-spacing",
    String(values.layer_spacing ?? 0.08),
    "--stagger",
    String(values.stagger ?? 2),
    "--texture",
    photoPath,
    "--texture-mode",
    "project",
    "--toning",
    String(values.toning ?? 1.8),
    "--density-floor",
    String(values.density_floor ?? 0.05),
    "--upright",
    "y",
    "--depth-axis",
    "z",
    "--seed",
    String(values.sampling_seed ?? 7),
    "--out",
    outputDir,
  ];
  if (values.invert_texture) args.push("--invert-texture");
  if (values.write_xyz) args.push("--xyz");
  return args;
}
