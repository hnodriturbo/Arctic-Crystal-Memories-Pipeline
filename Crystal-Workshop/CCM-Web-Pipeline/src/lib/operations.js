/*
 * ═══════════════════════════════════════════════════════════════
 * Operation Catalogue
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/operations.js
 * Purpose: Single source of truth for every converter script, the
 *          files it accepts, and the options it exposes.
 *
 * The UI renders its forms from this catalogue and the API builds its
 * command line from it, so a new script flag only ever needs adding here.
 */

import { blankOptions } from "@/lib/crystal-blanks";

// One definition, shared with the Meshy pipeline, mirroring printer_dxf.py.
export const CRYSTAL_TEMPLATES = blankOptions({ includeNone: false });

export const IMAGE_TYPES = [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"];
export const MODEL_TYPES = [
  ".blend",
  ".dxf",
  ".obj",
  ".stl",
  ".ply",
  ".glb",
  ".gltf",
  ".fbx",
  ".dae",
  ".usd",
  ".usda",
  ".usdc",
  ".usdz",
];

/** Shared form and CLI definition for the dedicated reconstruction workspace. */
export const RECONSTRUCT = {
  script: "cockpit_reconstruct.py",
  accepts: [".dxf", ".cad"],
  fields: [
    {name:"pose_override",label:"Override saved Cockpit pose",type:"boolean",group:"pose",flag:"--pose-override",default:false,help:"Normally read from the paired scene. Enable only to enter the absolute rotation and position used when the DXF was exported; these replace the saved values, not add to them."},
    ...["rotation","position"].flatMap(kind => [..."xyz"].map(axis => ({name:`pose_${kind}_${axis}`,label:`${kind === "rotation" ? "Rotation" : "Position"} ${axis.toUpperCase()} (${kind === "rotation" ? "degrees" : "mm"})`,type:"number",group:"pose",flag:`--pose-${kind}-${axis}`,default:0,min:kind === "rotation" ? -360 : -10000,max:kind === "rotation" ? 360 : 10000,step:0.0001,showWhen:values => values.pose_override,help:"Absolute Cockpit Layer Specs value for the exported model. Rotation is undone for texture projection and restored afterward. Center at origin removes the final translation; disable centering to preserve scene position."}))),
    { name: "sample_rate", label: "Sample every Nth point", type: "number", group: "density", flag: "--sample-rate", default: 1, min: 1, max: 10000, step: 1, help: "Keep 1 to use every source point. Showroom preparation always uses all points. The output grid separately controls surface resolution." },
    { name: "stl_limit", label: "Surface vertex budget", type: "number", group: "density", flag: "--stl-limit", default: 500000, min: 100, max: 500000, step: 1000, help: "A hard limit before triangulation. Approved showroom budget: 500,000 surface vertices." },
    { name: "limit", label: "First points only (0 = all)", type: "number", group: "density", flag: "--limit", default: 0, min: 0, max: 5000000, step: 1000, help: "Use 5,000 for a quick diagnostic. A partial scan can crop the subject." },
    { name: "stl_method", label: "Surface method", type: "select", group: "density", flag: "--stl-method", options: [{ value: "smooth", label: "Continuous relief · recommended" }, { value: "delaunay", label: "Raw triangles · comparison" }, { value: "convex", label: "Closed outer hull · Convex" }], default: "smooth", help: "Continuous relief collapses laser layers and avoids triangles across empty background." },
    { name: "grid_resolution", label: "Relief resolution", type: "number", group: "density", flag: "--grid-resolution", default: 768, min: 64, max: 768, step: 1, help: "Grid samples along the longer edge. 768 is the approved showroom default." },
    { name: "smoothing", label: "Depth smoothing", type: "number", group: "density", flag: "--smoothing", default: 2.25, min: 0, max: 5, step: 0.05, help: "Removes laser-layer roughness. Higher values can soften facial detail." },
    { name: "gap", label: "Close silhouette gaps", type: "number", group: "density", flag: "--gap", default: 7.5, min: 0, max: 8, step: 0.5, help: "Close small contour breaks, then interpolate enclosed dark areas. 0 leaves holes." },
    { name: "surface_percentile", label: "Front layer percentile", type: "number", group: "density", flag: "--surface-percentile", default: 85, min: 0, max: 100, step: 1, help: "85 estimates the front surface while rejecting isolated outermost dots." },
    { name: "front", label: "Front of relief", type: "select", group: "density", flag: "--front", options: ["positive", "negative"], default: "positive", help: "Positive Z is toward the viewer. Try negative if the surface faces backward." },
    { name: "repair_lower", label: "Repair lower-body ridges (experimental)", type: "boolean", group: "density", flag: "--repair-lower", default: false, help: "Reduces narrow protrusions in the bottom 42%. Upper geometry stays unchanged." },
    { name: "lower_repair_strength", label: "Lower-body repair strength", type: "number", group: "density", flag: "--lower-repair-strength", default: 1, min: 1, max: 3, step: 0.5, help: "Higher values pull wider ridges toward the surrounding surface; review hand detail." },
    { name: "color_mode", label: "Photo detail", type: "select", group: "output", flag: "--color-mode", options: [{ value: "texture", label: "Full photo texture · recommended" }, { value: "vertex", label: "Vertex colors · comparison" }], default: "texture", help: "A photo texture keeps fine details without requiring more triangles." },
    { name: "texture_from", label: "Paired scene or photograph", type: "file", group: "output", flag: "--texture-from", accepts: [".cockpit", ".jpg", ".jpeg", ".png", ".webp"], default: "", help: "Optional. Without a photo the surface stays light grey." },
    { name: "texture_plane", label: "Photo projection plane", type: "select", group: "output", flag: "--texture-plane", options: ["auto", "xy", "xz", "yz"], default: "xy", help: "XY matches the original relief preset. Auto requires a recognized scene direction." },
    { name: "flip_u", help: "Reverse the photo left to right without changing the mesh. Normally leave off for the original Cockpit texture.", label: "Mirror photo horizontally", type: "boolean", group: "output", flag: "--flip-u", default: false },
    { name: "flip_v", help: "Reverse the photo top to bottom without changing geometry. Leave off unless the source orientation requires correction.", label: "Mirror photo vertically", type: "boolean", group: "output", flag: "--flip-v", default: false },
    { name: "dedupe", help: "Remove identical coordinates before reconstruction. The approved preset leaves this off to preserve the original point distribution.", label: "Remove duplicate points", type: "boolean", group: "density", flag: "--dedupe", default: false },
    { name: "center", help: "Translate the finished surface to its bounding-box centre. Disable to preserve the original Cockpit position in millimetres.", label: "Center surface at origin", type: "boolean", group: "density", flag: "--center", default: true },
  ],
};
const ZERO_VALUE_FIELDS = new Set(["points", "max_points", "layer_spacing", "seed"]);

// Field groups, rendered as labelled sections so a long form stays readable.
export const FIELD_GROUPS = [
  { id: "model", emoji: "📐", label: "Model dimensions", hint: "Declare source units and size the result in millimetres." },
  { id: "size", emoji: "💠", label: "Crystal size", hint: "Aspect ratio is always preserved." },
  { id: "slice", emoji: "✂️", label: "Slice model", hint: "Keep geometry between optional millimetre boundaries on one axis." },
  { id: "density", emoji: "⚪", label: "Dot density", hint: "How many laser dots, and how close together." },
  { id: "layers", emoji: "🥞", label: "Depth layers", hint: "Snap depth onto planes the laser focuses on." },
  { id: "texture", emoji: "🖌️", label: "Texture toning", hint: "Drive dot density from image brightness." },
  { id: "orient", emoji: "🧭", label: "Orientation", hint: "Which way the subject sits in the glass." },
  { id: "output", emoji: "📦", label: "Output", hint: null },
];

const SIZE_FIELDS = [
  {
    name: "template",
    emoji: "💠",
    label: "Crystal blank",
    group: "size",
    type: "select",
    flag: "--template",
    options: CRYSTAL_TEMPLATES,
    default: "60x80x40",
    help: "Width x height x depth in mm.",
  },
  {
    name: "width",
    emoji: "↔️",
    label: "Custom width (mm)",
    group: "size",
    type: "number",
    flag: "--width",
    default: 0,
    min: 0,
    step: 5,
    help: "0 keeps the blank above.",
  },
  {
    name: "height",
    emoji: "↕️",
    label: "Custom height (mm)",
    group: "size",
    type: "number",
    flag: "--height",
    default: 0,
    min: 0,
    step: 5,
  },
  {
    name: "depth",
    emoji: "🧊",
    label: "Custom depth (mm)",
    group: "size",
    type: "number",
    flag: "--depth",
    default: 0,
    min: 0,
    step: 5,
    help: "Usually the limit for a full 3D subject. Raise it to get the model bigger.",
  },
  {
    name: "border",
    emoji: "🖼️",
    label: "Crystal margin (mm)",
    group: "size",
    type: "number",
    flag: "--border",
    default: 1,
    min: 0.1,
    step: 0.1,
    help:
      "Unengraved margin on every side. The standard is 1 mm; enter any value down to 0.1 mm.",
  },
];

const ORIENT_FIELDS = [
  {
    name: "upright",
    emoji: "⬆️",
    label: "Keep upright",
    group: "orient",
    type: "select",
    flag: "--upright",
    options: ["", "auto", "x", "y", "z"],
    default: "",
    help: "Pins a source axis to crystal height so a tall subject is not laid on its side.",
  },
  {
    name: "depth_axis",
    emoji: "👁️",
    label: "Axis facing the viewer",
    group: "orient",
    type: "select",
    flag: "--depth-axis",
    options: ["", "x", "y", "z"],
    default: "",
    help: "Two mappings often tie on size but show completely different sides.",
  },
  {
    name: "auto_orient",
    emoji: "🧭",
    label: "Auto-orient for biggest fit",
    group: "orient",
    type: "boolean",
    flag: "--auto-orient",
    default: false,
    help: "Maximises size, but may rotate the subject. Leave off when using Keep upright.",
  },
  {
    name: "swap_yz",
    emoji: "🔁",
    label: "Swap Y and Z",
    group: "orient",
    type: "boolean",
    flag: "--swap-yz",
    default: false,
    help: "For Z-up sources such as CAD exports.",
  },
  {
    name: "flip",
    emoji: "🪞",
    label: "Mirror axes",
    group: "orient",
    type: "text",
    flag: "--flip",
    default: "",
    placeholder: "x, z, xz",
  },
];

const LAYER_FIELDS = [
  {
    name: "layers",
    emoji: "🥞",
    label: "Fixed plane count (alternative)",
    group: "layers",
    type: "number",
    flag: "--layers",
    default: 0,
    min: 0,
    max: 1000,
    step: 1,
    help:
      "Alternative to layer spacing. 0 lets the millimetre spacing below decide the number of depth planes.",
  },
  {
    name: "layer_spacing",
    emoji: "📏",
    label: "Layer spacing (mm)",
    group: "layers",
    type: "number",
    flag: "--layer-spacing",
    default: 0.09,
    min: 0,
    step: 0.01,
    help:
      "Cockpit3D layer-spacing equivalent. 0.09 mm is the owner-approved layer-spacing baseline and overrides the fixed plane count.",
  },
  {
    name: "stagger",
    emoji: "🔀",
    label: "Stagger",
    group: "layers",
    type: "number",
    flag: "--stagger",
    default: 1,
    min: 1,
    max: 8,
    step: 1,
    help: "Offsets alternate layers so dots do not stack into visible columns.",
  },
];

export const OPERATIONS = {
  convert_model: {
    label: "Convert, resize, and slice a 3D model",
    blurb:
      "Reads common Blender-compatible 3D files, reports their geometry, sizes them in millimetres, optionally slices them, and writes every selected format. Multiple formats are also packaged as ZIP.",
    script: "convert_model.py",
    accepts: MODEL_TYPES,
    fields: [
      {name:"photo_density",label:"Photo brightness controls DXF points (experimental)",type:"boolean",group:"density",flag:"--photo-density",default:false,help:"Experimental portrait sampling, not a validated machine preset. Use the UV photograph to place more points in bright regions and no points in black regions. Requires one image texture; bake multiple materials in Blender first."},
      {
        name: "formats",
        emoji: "📦",
        label: "Output formats",
        group: "output",
        type: "multiselect",
        flag: "--formats",
        options: ["dxf", "glb", "gltf", "obj", "stl", "ply", "fbx", "usd", "usdz"],
        default: ["dxf", "glb"],
        help: "DXF uses ACM's SSLE POINT-cloud writer. Two or more selections also produce one ZIP.",
      },
      {
        name: "input_unit",
        emoji: "📏",
        label: "Source coordinate unit",
        group: "model",
        type: "select",
        flag: "--input-unit",
        options: [
          { value: "mm", label: "Millimetres (mm)" },
          { value: "cm", label: "Centimetres (cm)" },
          { value: "m", label: "Metres (m)" },
          { value: "in", label: "Inches (in)" },
        ],
        default: "mm",
        help: "Coordinates are converted to millimetres before sizing or slicing.",
      },
      {
        name: "fit_width",
        emoji: "↔️",
        label: "Maximum model width (mm)",
        group: "model",
        type: "number",
        flag: "--fit-width",
        default: 0,
        min: 0,
        step: 1,
        help: "0 keeps the converted source width. Multiple limits preserve aspect ratio and use the tightest fit.",
      },
      {
        name: "fit_height",
        emoji: "↕️",
        label: "Maximum model height (mm)",
        group: "model",
        type: "number",
        flag: "--fit-height",
        default: 0,
        min: 0,
        step: 1,
      },
      {
        name: "fit_depth",
        emoji: "🧊",
        label: "Maximum model depth (mm)",
        group: "model",
        type: "number",
        flag: "--fit-depth",
        default: 0,
        min: 0,
        step: 1,
      },
      {
        name: "placement",
        emoji: "🎯",
        label: "Placement before slicing",
        group: "model",
        type: "select",
        flag: "--placement",
        options: [
          { value: "center", label: "Center at origin" },
          { value: "ground", label: "Center X/Y and place bottom at Z=0" },
          { value: "keep", label: "Keep imported coordinates" },
        ],
        default: "center",
      },
      {
        name: "slice_axis",
        emoji: "✂️",
        label: "Slice axis",
        group: "slice",
        type: "select",
        flag: "--slice-axis",
        options: [
          { value: "none", label: "Do not slice" },
          { value: "x", label: "X · width" },
          { value: "y", label: "Y · height" },
          { value: "z", label: "Z · depth" },
        ],
        default: "none",
      },
      {
        name: "slice_min",
        emoji: "◀️",
        label: "Keep from coordinate (mm)",
        group: "slice",
        type: "number",
        flag: "--slice-min",
        default: "",
        step: 0.1,
        passZero: true,
        help: "Blank leaves this side open. Coordinates are measured after unit conversion, fitting, and placement.",
      },
      {
        name: "slice_max",
        emoji: "▶️",
        label: "Keep through coordinate (mm)",
        group: "slice",
        type: "number",
        flag: "--slice-max",
        default: "",
        step: 0.1,
        passZero: true,
      },
      {
        name: "fill_cuts",
        emoji: "🧱",
        label: "Cap cut surfaces",
        group: "slice",
        type: "boolean",
        flag: "--fill-cuts",
        default: true,
        help: "Fills closed cut loops when the source topology allows it.",
      },
      ...SIZE_FIELDS,
      {
        name: "points",
        emoji: "⚪",
        label: "DXF sampling target (0 = spacing)",
        group: "density",
        type: "number",
        flag: "--points",
        default: 0,
        min: 0,
        max: 5000000,
        step: 50000,
        help: "Only used when DXF is selected.",
      },
      {
        name: "spacing",
        emoji: "📏",
        label: "DXF point spacing (mm)",
        group: "density",
        type: "number",
        flag: "--spacing",
        default: 0.08,
        min: 0.01,
        max: 1,
        step: 0.01,
      },
      {
        name: "min_distance",
        emoji: "⚠️",
        label: "DXF minimum dot distance (mm)",
        group: "density",
        type: "number",
        flag: "--min-distance",
        default: 0.08,
        min: 0.01,
        max: 1,
        step: 0.01,
      },
      {
        name: "z_distance",
        emoji: "📐",
        label: "DXF depth-dot spacing (mm)",
        group: "density",
        type: "number",
        flag: "--z-distance",
        default: 0,
        min: 0,
        max: 1,
        step: 0.01,
      },
      {
        name: "max_points",
        emoji: "🛑",
        label: "DXF final point cap",
        group: "density",
        type: "number",
        flag: "--max-points",
        default: 500000,
        min: 1,
        max: 5000000,
        step: 50000,
      },
      ...LAYER_FIELDS,
      {
        name: "seed",
        emoji: "🎲",
        label: "DXF sampling seed",
        group: "output",
        type: "number",
        flag: "--seed",
        default: 7,
        min: 0,
        step: 1,
        passZero: true,
      },
    ],
  },

  mesh_to_pointcloud: {
    label: "3D model to printable DXF",
    blurb:
      "Samples an OBJ or triangle-mesh DXF into the evenly spaced POINT cloud the SSLE engraver reads, fitted to a crystal blank.",
    script: "mesh_to_pointcloud.py",
    accepts: [".obj", ".dxf"],
    fields: [
      ...SIZE_FIELDS,
      {
        name: "points",
        emoji: "⚪",
        label: "Sampling target (0 = spacing)",
        group: "density",
        type: "number",
        flag: "--points",
        default: 0,
        min: 0,
        max: 5000000,
        step: 50000,
        help:
          "Optional sampling target before thinning. Keep 0 for Cockpit3D-style density controlled by point spacing.",
      },
      {
        name: "spacing",
        emoji: "📏",
        label: "Point spacing (XY, mm)",
        group: "density",
        type: "number",
        flag: "--spacing",
        default: 0.08,
        min: 0.01,
        max: 1,
        step: 0.01,
        help:
          "Main Cockpit3D-style density control. 0.08 mm is the reference baseline; smaller values create more dots.",
      },
      {
        name: "min_distance",
        emoji: "⚠️",
        label: "Minimum dot distance (mm)",
        group: "density",
        type: "number",
        flag: "--min-distance",
        default: 0.08,
        min: 0.01,
        max: 1,
        step: 0.01,
        help:
          "Safety floor between XY dots. Start at the 0.08 mm Cockpit3D reference and validate any smaller distance on the green-beam machine.",
      },
      {
        name: "z_distance",
        emoji: "📐",
        label: "Depth dot spacing before layers (mm)",
        group: "density",
        type: "number",
        flag: "--z-distance",
        default: 0,
        min: 0,
        max: 1,
        step: 0.01,
        help:
          "Grid-thinning distance along Z before points are snapped to final layers. 0 reuses XY point spacing; this is not layer spacing.",
      },
      {
        name: "max_points",
        emoji: "🛑",
        label: "Final point cap",
        group: "density",
        type: "number",
        flag: "--max-points",
        default: 500000,
        min: 0,
        max: 5000000,
        step: 50000,
        help:
          "Cockpit3D reference guardrail. 500,000 limits oversized clouds after spacing and layers; 0 removes the cap.",
      },
      ...LAYER_FIELDS,
      {
        name: "texture",
        emoji: "🖼️",
        label: "Texture image",
        group: "texture",
        type: "file",
        flag: "--texture",
        accepts: IMAGE_TYPES,
        default: "",
        help: "Bright areas get denser dots. This is what makes glass read as a photograph.",
      },
      {
        name: "texture_mode",
        emoji: "🗺️",
        label: "Lookup mode",
        group: "texture",
        type: "select",
        flag: "--texture-mode",
        options: [
          { value: "uv", label: "Mesh UV coordinates" },
          { value: "project", label: "Front projection" },
        ],
        default: "uv",
        help:
          "UV means the mesh's 2D texture coordinates, not an ultraviolet laser. It is unrelated to UV versus green-beam engraving.",
      },
      {
        name: "toning",
        emoji: "◐",
        label: "Toning",
        group: "texture",
        type: "number",
        flag: "--toning",
        default: 1.8,
        min: 0.2,
        max: 5,
        step: 0.1,
        help: "Gamma on brightness. Cockpit3D's own default is 1.8; higher deepens shadows.",
      },
      {
        name: "density_floor",
        emoji: "🌑",
        label: "Density floor",
        group: "texture",
        type: "number",
        flag: "--density-floor",
        default: 0.05,
        min: 0,
        max: 1,
        step: 0.05,
        help: "Keeps the darkest areas sparse rather than completely empty.",
      },
      {
        name: "invert_texture",
        emoji: "🔃",
        label: "Invert brightness",
        group: "texture",
        type: "boolean",
        flag: "--invert-texture",
        default: false,
        help: "Treat dark as dense instead of light.",
      },
      ...ORIENT_FIELDS,
      {
        name: "seed",
        emoji: "🎲",
        label: "Seed",
        group: "output",
        type: "number",
        flag: "--seed",
        default: 7,
        min: 0,
        step: 1,
        help:
          "The seed fixes pseudo-random surface sampling. The same input, settings and seed reproduce the same cloud; changing any of them can change the dots.",
      },
      {
        name: "xyz",
        emoji: "📄",
        label: "Also write XYZ preview",
        group: "output",
        type: "boolean",
        flag: "--xyz",
        default: true,
      },
    ],
  },

  rebuild_pointcloud: {
    label: "Repair or re-tune a point DXF",
    blurb:
      "Re-emits an existing POINT cloud in the exact format the printer accepts. Use it when a Cockpit3D export will not load, or to change size, dot spacing and depth layers without going back to the model.",
    script: "rebuild_pointcloud.py",
    accepts: [".dxf"],
    fields: [
      {
        name: "resize",
        emoji: "📐",
        label: "Refit into a crystal blank",
        group: "size",
        type: "boolean",
        flag: "--resize",
        default: false,
        help: "Leave off for a pure format repair that moves no coordinate.",
      },
      ...SIZE_FIELDS,
      {
        name: "scale",
        emoji: "🔎",
        label: "Plain scale factor",
        group: "size",
        type: "number",
        flag: "--scale",
        default: 1,
        min: 0.01,
        step: 0.1,
        help: "Multiplier about the centre, when refitting is too much.",
      },
      {
        name: "spacing",
        emoji: "📏",
        label: "Re-space dots (mm)",
        group: "density",
        type: "number",
        flag: "--spacing",
        default: 0,
        min: 0,
        max: 1,
        step: 0.01,
        help: "0 keeps every point. Cannot add detail the source does not already have.",
      },
      {
        name: "z_distance",
        emoji: "📐",
        label: "Depth dot spacing before layers (mm)",
        group: "density",
        type: "number",
        flag: "--z-distance",
        default: 0,
        min: 0,
        max: 1,
        step: 0.01,
        help:
          "Grid-thinning distance along Z before final layer snapping. 0 reuses XY spacing; it is separate from layer spacing.",
      },
      {
        name: "limit",
        emoji: "🔢",
        label: "Point cap",
        group: "density",
        type: "number",
        flag: "--limit",
        default: 500000,
        min: 0,
        step: 50000,
        help: "500,000 is the Cockpit3D reference guardrail. Set 0 only when no cap is wanted.",
      },
      ...LAYER_FIELDS,
      ...ORIENT_FIELDS,
      {
        name: "xyz",
        emoji: "📄",
        label: "Also write XYZ preview",
        group: "output",
        type: "boolean",
        flag: "--xyz",
        default: true,
      },
    ],
  },

  purify_dxf: {
    label: "Point DXF to standards-compliant DXF",
    blurb:
      "Rebuilds a bare Cockpit3D POINT export as a full AC1015 file with tables, blocks and real handles, so any CAD tool opens it.",
    script: "purify_dxf.py",
    accepts: [".dxf"],
    fields: [],
  },

  convert_dxf: {
    label: "Point DXF to mesh or cloud",
    blurb:
      "Turns a POINT-cloud DXF back into XYZ, PLY, OBJ or STL. The reverse direction, for viewing and 3D printing.",
    script: "convert_dxf.py",
    accepts: [".dxf"],
    fields: [
      {
        name: "formats",
        emoji: "📦",
        label: "Output formats",
        group: "output",
        type: "multiselect",
        flag: "--formats",
        options: ["xyz", "ply", "obj", "stl"],
        default: ["xyz", "stl"],
      },
      {
        name: "limit",
        emoji: "🔢",
        label: "Point limit",
        group: "density",
        type: "number",
        flag: "--limit",
        default: 0,
        min: 0,
        step: 10000,
        help: "0 keeps every point.",
      },
      {
        name: "scale",
        emoji: "🔎",
        label: "Scale factor",
        group: "size",
        type: "number",
        flag: "--scale",
        default: 1,
        min: 0.001,
        step: 0.1,
      },
      {
        name: "center",
        emoji: "🎯",
        label: "Center at origin",
        group: "size",
        type: "boolean",
        flag: "--center",
        default: false,
      },
      {
        name: "dedupe",
        emoji: "🧹",
        label: "Remove duplicates",
        group: "density",
        type: "boolean",
        flag: "--dedupe",
        default: false,
      },
    ],
  },

  convert_cad: {
    label: "Cockpit3D CAD to mesh or cloud",
    blurb: "Reads the proprietary CIRasterizer text format and exports XYZ, PLY, OBJ or STL.",
    script: "convert_cad.py",
    accepts: [".cad"],
    fields: [
      {
        name: "formats",
        emoji: "📦",
        label: "Output formats",
        group: "output",
        type: "multiselect",
        flag: "--formats",
        options: ["xyz", "ply", "obj", "stl"],
        default: ["xyz", "stl"],
      },
      {
        name: "sample_rate",
        emoji: "🎚️",
        label: "Sample every Nth point",
        group: "density",
        type: "number",
        flag: "--sample-rate",
        default: 1,
        min: 1,
        step: 1,
      },
      {
        name: "center",
        emoji: "🎯",
        label: "Center at origin",
        group: "size",
        type: "boolean",
        flag: "--center",
        default: false,
      },
    ],
  },

  inspect_file: {
    label: "Inspect a file",
    blurb: "Reports what a file actually contains before you convert it. Changes nothing on disk.",
    script: "inspect_file.py",
    accepts: [".dxf", ".cad", ".obj", ".xyz", ".ply", ".stl", ".cockpit"],
    fields: [],
  },
};

/** Turn a chosen operation plus the user's form values into argv for the Python script. */
export function buildArguments(operationKey, values, absoluteInputPath, resolveFile) {
  const operation = OPERATIONS[operationKey];
  if (!operation) return null;

  const args = ["--file", absoluteInputPath];

  for (const field of operation.fields) {
    const value = values?.[field.name];

    if (field.type === "boolean") {
      if (value) args.push(field.flag);
      continue;
    }
    if (field.type === "multiselect") {
      const chosen = Array.isArray(value) ? value.filter(Boolean) : [];
      if (chosen.length) args.push(field.flag, ...chosen);
      continue;
    }
    if (value === "" || value === null || value === undefined) continue;

    if (field.type === "file") {
      // A picked file is stored relative to input/; the API turns it absolute.
      const resolved = resolveFile ? resolveFile(value) : value;
      if (resolved) args.push(field.flag, resolved);
      continue;
    }
    // Zero means "leave the script's own default alone" for every number except
    // the point budget, where zero is a real instruction to use spacing instead.
    if (
      field.type === "number" &&
      Number(value) === 0 &&
      !ZERO_VALUE_FIELDS.has(field.name) &&
      !field.passZero
    ) continue;

    args.push(field.flag, String(value));
  }

  return args;
}

/** Default form state for one operation, used when the picker changes. */
export function defaultValues(operationKey) {
  const operation = OPERATIONS[operationKey];
  if (!operation) return {};
  return Object.fromEntries(operation.fields.map((field) => [field.name, field.default]));
}

/** Groups actually present on an operation, in canonical order. */
export function groupsFor(operationKey) {
  const operation = OPERATIONS[operationKey];
  if (!operation) return [];
  const present = new Set(operation.fields.map((field) => field.group || "output"));
  return FIELD_GROUPS.filter((group) => present.has(group.id));
}
