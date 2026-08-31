/*
 * ═══════════════════════════════════════════════════════════════
 * Relief Pipeline Catalogue
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/relief/catalog.js
 * Purpose: The complete 2.5D chain, every option it takes, and how
 *          the form becomes argv.
 *
 * Same shape as lib/image/catalog.js, so OptionFields renders it without
 * knowing anything about relief. One definition, read by both the form and
 * the API route, so a new script flag is added in exactly one place.
 */

import { blankOptions, templateDimensions, usableSpace } from "@/lib/crystal-blanks";

export const PHOTO_TYPES = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"];

/**
 * Five stages, all always run.
 *
 * Unlike the image chain these are not individually optional: a depth map
 * with no mesh is not a deliverable, and a mesh needs a depth map to exist.
 * They are listed separately so the console shows which one is working and
 * geometry detail never gets confused with the crystal appearance map.
 */
export const RELIEF_STAGES = [
  { id: "depth", script: "depth_map.py", label: "Depth map" },
  { id: "face", script: "face_refine.py", label: "Face-depth refinement" },
  { id: "head", script: "gnm_head_refine.py", label: "Parametric head refinement" },
  { id: "detail", script: "detail_refine.py", label: "Surface micro-depth" },
  { id: "appearance", script: "appearance_refine.py", label: "Crystal appearance detail" },
  { id: "mesh", script: "depth_to_mesh.py", label: "Relief mesh" },
];

export const RELIEF_FIELD_GROUPS = [
  { id: "depth", emoji: "🧠", label: "Depth model", hint: "The one stage with a model in it." },
  {
    id: "face",
    emoji: "🙂",
    label: "Face refinement",
    hint: "468-point face fitting plus a real low-frequency head shape before meshing.",
  },
  {
    id: "detail",
    emoji: "🪶",
    label: "Surface detail",
    hint: "Controlled normals-to-depth detail for faces, fur, cloth and objects.",
  },
  {
    id: "appearance",
    emoji: "✨",
    label: "Crystal appearance",
    hint: "Beard, hair, wrinkle and skin detail kept separate from physical depth.",
  },
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
    options: ["moge-2", "depth-pro", "depth-anything", "marigold"],
    default: "moge-2",
    help: "MoGe-2 ViT-L at level 9 is the production default and also supplies normals.",
    optionHelp: {
      "moge-2": "Production default. ViT-L level 9 gave the strongest complete-scene depth in ACM tests.",
      "depth-pro": "Apple metric-depth challenger with sharp boundaries.",
      "depth-anything": "Feed-forward, seconds on GPU. The right default for almost every photograph.",
      marigold: "Diffusion-based and much slower, but resolves soft cheek and brow relief a portrait lives on.",
    },
  },
  {
    name: "moge_model",
    emoji: "📦",
    label: "MoGe checkpoint",
    group: "depth",
    type: "select",
    options: ["vitl", "vitb"],
    default: "vitl",
    help: "ViT-L is the production-quality checkpoint; ViT-B is retained for previews and comparisons.",
    showWhen: (values) => values.engine === "moge-2",
  },
  {
    name: "moge_resolution_level",
    emoji: "🔬",
    label: "MoGe detail level",
    group: "depth",
    type: "number",
    default: 9,
    min: 0,
    max: 9,
    step: 1,
    help: "9/9 is the production default. Level 5 is preview-only.",
    showWhen: (values) => values.engine === "moge-2",
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

  // ── Mandatory face refinement ────────────────────────────────────────────
  {
    name: "known_face_count",
    emoji: "🙂",
    label: "Known face count",
    group: "face",
    type: "number",
    default: 0,
    min: 0,
    max: 50,
    step: 1,
    help: "0 means auto-detect. A positive value makes a missed or extra face a hard failure.",
  },
  {
    name: "face_score_threshold",
    emoji: "🎯",
    label: "Detection confidence",
    group: "face",
    type: "number",
    default: 0.65,
    min: 0.1,
    max: 0.99,
    step: 0.01,
    help: "YuNet confidence floor. 0.65 rejected a false hair detection in the two-person tester.",
  },
  {
    name: "face_strength",
    emoji: "🗿",
    label: "Refinement strength",
    group: "face",
    type: "number",
    default: 0.85,
    min: 0,
    max: 1.5,
    step: 0.05,
    help: "How strongly face-crop shape and detail replace the global face depth.",
  },
  {
    name: "face_shape_mix",
    emoji: "🧬",
    label: "Shape versus detail",
    group: "face",
    type: "number",
    default: 0.45,
    min: 0,
    max: 1,
    step: 0.05,
    help: "0 keeps only local facial detail; 1 also replaces broad facial shape.",
  },
  {
    name: "face_crop_expansion",
    emoji: "🔍",
    label: "Face crop expansion",
    group: "face",
    type: "number",
    default: 0.35,
    min: 0,
    max: 1.5,
    step: 0.05,
    help: "Includes brow, jaw, ears and hair context around each YuNet face box.",
  },
  {
    name: "head_span",
    emoji: "🗿",
    label: "Head-shape depth",
    group: "face",
    type: "number",
    default: 0.34,
    min: 0.1,
    max: 0.6,
    step: 0.02,
    help: "GNM skull/forehead/cheek/nose/chin span before it is scaled to the chosen crystal depth.",
  },
  {
    name: "front_headroom",
    emoji: "↗️",
    label: "Front anatomy headroom",
    group: "face",
    type: "number",
    default: 0.12,
    min: 0,
    max: 0.4,
    step: 0.01,
    help: "Reserves depth in front of the source so noses, lips and brows are not clipped by the nearest envelope wall.",
  },
  {
    name: "back_headroom",
    emoji: "↙️",
    label: "Back anatomy headroom",
    group: "face",
    type: "number",
    default: 0.12,
    min: 0,
    max: 0.4,
    step: 0.01,
    help: "Reserves depth behind the source so the skull, cheek turn and neck can move away from the viewer.",
  },
  {
    name: "head_feather",
    emoji: "🫧",
    label: "Head blend feather",
    group: "face",
    type: "number",
    default: 24,
    min: 4,
    max: 80,
    step: 2,
    help: "Blends the fitted head into MoGe hair, neck, and body depth without a visible ring.",
  },
  {
    name: "head_silhouette_taper",
    emoji: "✂️",
    label: "Cut-out edge taper",
    group: "face",
    type: "number",
    default: 12,
    min: 0,
    max: 40,
    step: 1,
    help: "Eases the outer cut-out to the back plane so side views do not become horizontal spikes.",
  },

  // ── Generic surface detail from MoGe normals ────────────────────────────
  {
    name: "detail_strength",
    emoji: "🪶",
    label: "Micro-depth strength",
    group: "detail",
    type: "number",
    default: 0.018,
    min: 0,
    max: 0.1,
    step: 0.002,
    help: "Small by design: adds surface orientation without turning hair, wrinkles or make-up into deep grooves.",
  },
  {
    name: "detail_fine_sigma",
    emoji: "🔬",
    label: "Smallest detail scale",
    group: "detail",
    type: "number",
    default: 1.2,
    min: 0.2,
    max: 8,
    step: 0.2,
    help: "Suppresses pixel-sized noise below this Gaussian radius.",
  },
  {
    name: "detail_coarse_sigma",
    emoji: "🌊",
    label: "Largest detail scale",
    group: "detail",
    type: "number",
    default: 24,
    min: 4,
    max: 96,
    step: 2,
    help: "Keeps this stage out of broad head/body depth, which remains MoGe and face refinement territory.",
  },

  // ── Photograph-derived crystal appearance, never physical depth ─────────
  {
    name: "appearance_local_contrast",
    emoji: "◐",
    label: "Local tonal contrast",
    group: "appearance",
    type: "number",
    default: 0.55,
    min: 0,
    max: 3,
    step: 0.05,
    help: "Recovers local face contrast without converting make-up or shadows into geometry.",
  },
  {
    name: "appearance_detail_strength",
    emoji: "🧔",
    label: "Hair and skin detail",
    group: "appearance",
    type: "number",
    default: 1.35,
    min: 0,
    max: 5,
    step: 0.05,
    help: "Preserves fine beard, hair, eyelid, wrinkle and skin detail in the monochrome preview.",
  },
  {
    name: "appearance_toning",
    emoji: "💡",
    label: "Crystal toning",
    group: "appearance",
    type: "number",
    default: 1.8,
    min: 0.2,
    max: 5,
    step: 0.1,
    help: "Preview transfer curve. 1.8 matches the Cockpit3D reference; laser calibration comes later.",
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
    name: "relief_depth_profile",
    emoji: "📏",
    label: "Relief depth profile",
    group: "size",
    type: "select",
    options: ["shallow", "balanced", "deep", "custom"],
    default: "balanced",
    help: "Crystal-bounded test profiles. Balanced is the default; deep is deliberately stronger for side-view comparison.",
    optionHelp: {
      shallow: "Up to 8 mm or 20% of usable crystal depth.",
      balanced: "Up to 16 mm or 40% of usable crystal depth.",
      deep: "Up to 24 mm or 60% of usable crystal depth.",
      custom: "Use the exact millimetre value below.",
    },
  },
  {
    name: "relief_depth",
    emoji: "🧊",
    label: "Relief depth (mm)",
    group: "size",
    type: "number",
    default: 16,
    min: 0,
    step: 1,
    help: "Exact custom depth. Used only when the profile above is custom.",
    showWhen: (values) => values.relief_depth_profile === "custom",
  },

  // ── Mesh ──────────────────────────────────────────────────────────────────
  {
    name: "auto_grid",
    emoji: "📦",
    label: "Crystal-sized mesh",
    group: "mesh",
    type: "boolean",
    default: true,
    help: "Scale mesh density to the physical crystal, capped at 512 vertices on the long edge to prevent oversized GLBs.",
  },
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
    help: "Manual override. 512 is the production cap; 0 keeps full image resolution and can create very large files.",
    showWhen: (values) => !values.auto_grid,
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
    name: "auto_depth_flow_fillet",
    emoji: "📐",
    label: "Automatic depth-flow formula",
    group: "mesh",
    type: "boolean",
    default: true,
    help:
      "Scale edge and boundary bending from the fitted size: clamp(sqrt(width × height) × (0.01 / 77.8), 0.01 mm, 7 mm). A 78 mm square resolves to 0.01 mm.",
  },
  {
    name: "edge_fillet_mm",
    emoji: "〰️",
    label: "Depth-flow fillet (mm)",
    group: "mesh",
    type: "number",
    default: 0.01,
    min: 0,
    max: 8,
    step: 0.01,
    help:
      "Merges every depth bend into a continuous S-shaped flow. Sharp transitions receive the strongest smoothing while micro-detail is restored afterwards.",
    showWhen: (values) => values.auto_depth_flow_fillet === false,
  },
  {
    name: "boundary_fillet_mm",
    emoji: "↪️",
    label: "Frame/silhouette bend (mm)",
    group: "mesh",
    type: "number",
    default: 0.01,
    min: 0,
    max: 8,
    step: 0.01,
    help:
      "Bends cut-out and image-frame edges back gradually instead of ending the relief in a 90-degree wall.",
    showWhen: (values) => values.auto_depth_flow_fillet === false,
  },
  {
    name: "depth_step_threshold_mm",
    emoji: "📐",
    label: "Sharp-depth threshold (mm)",
    group: "mesh",
    type: "number",
    default: 0.65,
    min: 0.05,
    max: 4,
    step: 0.01,
    help: "A low-frequency depth deviation at or above this value receives the full physical fillet.",
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
    options: ["texture", "luma", "rgb", "none"],
    default: "texture",
    help: "texture embeds the full photograph for visual approval; it does not alter the relief geometry.",
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
export function buildDepthArgs(values, inputPath, outputPath, auxiliaryOutput) {
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
  } else if (values.engine === "moge-2") {
    args.push("--moge-model", values.moge_model || "vitl");
    args.push("--moge-resolution-level", String(values.moge_resolution_level ?? 9));
    if (auxiliaryOutput) args.push("--aux-output", auxiliaryOutput);
  } else if (values.engine === "depth-anything") {
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

/** argv for generic, conservative normals-to-microdepth fusion. */
export function buildDetailRefinementArgs(
  values,
  depthPath,
  normalPath,
  maskPath,
  outputPath,
  auxiliaryOutput,
) {
  const args = [
    "--depth",
    depthPath,
    "--normal",
    normalPath,
    "--output",
    outputPath,
    "--aux-output",
    auxiliaryOutput,
    "--strength",
    String(values.detail_strength ?? 0.018),
    "--fine-sigma",
    String(values.detail_fine_sigma ?? 1.2),
    "--coarse-sigma",
    String(values.detail_coarse_sigma ?? 24),
  ];
  if (maskPath) args.push("--mask", maskPath);
  return args;
}

/** argv for mandatory multi-face depth refinement. */
export function buildFaceRefinementArgs(
  values,
  photoPath,
  depthPath,
  outputPath,
  auxiliaryOutput,
) {
  const args = [
    "--input",
    photoPath,
    "--depth",
    depthPath,
    "--output",
    outputPath,
    "--aux-output",
    auxiliaryOutput,
    "--device",
    values.device || "auto",
    "--moge-model",
    "vitl",
    "--moge-resolution-level",
    "9",
    "--score-threshold",
    String(values.face_score_threshold ?? 0.65),
    "--crop-expansion",
    String(values.face_crop_expansion ?? 0.35),
    "--strength",
    String(values.face_strength ?? 0.85),
    "--shape-mix",
    String(values.face_shape_mix ?? 0.45),
  ];
  if (Number(values.known_face_count) > 0) {
    args.push("--known-face-count", String(values.known_face_count));
  }
  return args;
}

/** argv for automatic 468-point Google GNM Head fitting and low-frequency fusion. */
export function buildHeadRefinementArgs(
  values,
  photoPath,
  depthPath,
  faceMetadataPath,
  outputPath,
  auxiliaryOutput,
) {
  return [
    "--photo",
    photoPath,
    "--depth",
    depthPath,
    "--faces",
    faceMetadataPath,
    "--output",
    outputPath,
    "--qa-dir",
    auxiliaryOutput,
    "--device",
    values.device || "auto",
    "--head-span",
    String(values.head_span ?? 0.34),
    "--front-headroom",
    String(values.front_headroom ?? 0.12),
    "--back-headroom",
    String(values.back_headroom ?? 0.12),
    "--feather",
    String(values.head_feather ?? 24),
    "--silhouette-taper",
    String(values.head_silhouette_taper ?? 12),
  ];
}

/** argv for photograph-derived crystal appearance, explicitly separate from depth. */
export function buildAppearanceRefinementArgs(values, photoPath, outputPath, auxiliaryOutput) {
  return [
    "--input",
    photoPath,
    "--output",
    outputPath,
    "--aux-output",
    auxiliaryOutput,
    "--local-contrast",
    String(values.appearance_local_contrast ?? 0.55),
    "--detail-strength",
    String(values.appearance_detail_strength ?? 1.35),
    "--toning",
    String(values.appearance_toning ?? 1.8),
  ];
}

/** Resolve shallow/balanced/deep profiles against the selected crystal's usable depth. */
export function resolvedReliefDepth(values) {
  const profile = values.relief_depth_profile || "balanced";
  if (profile === "custom") return Math.max(0, Number(values.relief_depth) || 0);
  const usable = usableSpace(values.template || "60x80x40", { border: values.border ?? 1 });
  const available = Math.max(0.1, Number(usable?.depth) || 38);
  const profiles = {
    shallow: Math.min(8, available * 0.2),
    balanced: Math.min(16, available * 0.4),
    deep: Math.min(24, available * 0.6),
  };
  return Number(profiles[profile] ?? profiles.balanced).toFixed(3).replace(/\.0+$/, "");
}

/** Use roughly 0.12 mm vertex spacing, but keep GLB/OBJ files predictably bounded. */
export function resolvedMeshGrid(values) {
  if (!values.auto_grid) return Math.max(0, Math.min(2048, Number(values.grid) || 0));
  const space = usableSpace(values.template || "60x80x40", { border: values.border ?? 1 });
  const longEdge = Math.max(Number(space?.width) || 58, Number(space?.height) || 78);
  return Math.max(192, Math.min(512, Math.ceil(longEdge / 0.12)));
}

/** argv for depth_to_mesh.py. The production call includes OBJ as the handoff. */
export function buildMeshArgs(
  values,
  depthPath,
  photoPath,
  glbPath,
  objPath,
  texturePath = null,
) {
  const args = [
    "--depth",
    depthPath,
    "--photo",
    photoPath,
    "--output",
    glbPath,
    "--template",
    templateDimensions(values.template || "60x80x40"),
    "--border",
    String(values.border ?? 1),
    "--relief-depth",
    String(resolvedReliefDepth(values)),
    "--grid",
    String(resolvedMeshGrid(values)),
    "--alpha-threshold",
    String(values.alpha_threshold ?? 0.5),
    "--edge-fillet-mm",
    String(values.auto_depth_flow_fillet === false ? values.edge_fillet_mm ?? 0.01 : -1),
    "--boundary-fillet-mm",
    String(values.auto_depth_flow_fillet === false ? values.boundary_fillet_mm ?? 0.01 : -1),
    "--depth-step-threshold-mm",
    String(values.depth_step_threshold_mm ?? 0.65),
    "--vertex-color",
    values.vertex_color || "luma",
  ];

  if (objPath) args.push("--obj", objPath);
  if (texturePath) args.push("--texture-image", texturePath);
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
  const [width, height, depth] = templateDimensions(values.template || "60x80x40").split("x").map(Number);
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
