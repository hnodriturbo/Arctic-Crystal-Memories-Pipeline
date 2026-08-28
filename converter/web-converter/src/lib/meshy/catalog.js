/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Catalogue
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/meshy/catalog.js
 * Purpose: Single source of truth for the Meshy pipeline - the modes,
 *          every option they expose, and how a form turns into an API body.
 *
 * Field records deliberately match src/lib/operations.js, so the existing
 * OptionFields component renders this pipeline without knowing about it.
 */

import { blankOptions, usableSpace } from "@/lib/crystal-blanks";
import { IMAGE_FIELDS } from "@/lib/image/catalog";

// Re-exported so the Meshy panel has one import for its whole catalogue.
export { CRYSTAL_BLANKS, CRYSTAL_BLANK_NAMES, usableSpace } from "@/lib/crystal-blanks";

export const PHOTO_TYPES = [".jpg", ".jpeg", ".png"];

// Every format Meshy can emit. GLB drives the in-page viewer, OBJ is what the
// converter pipeline consumes, STL is for anyone printing a test in plastic.
export const MODEL_FORMATS = ["glb", "obj", "fbx", "stl", "usdz", "3mf"];

/*
 * No clean-up group here on purpose.
 *
 * Cleaning a photograph is the image pipeline's job and has its own tab, its
 * own settings and its own results to judge. Duplicating those controls here
 * gave two places to set the same thing and no way to see what the first one
 * produced. Clean the photo there, send it over, and this step takes whatever
 * it is given.
 */
export const MESHY_FIELD_GROUPS = [
  { id: "model", emoji: "🤖", label: "Generation model", hint: "Which Meshy engine builds the geometry." },
  { id: "mesh", emoji: "🕸️", label: "Mesh and topology", hint: "What the surface is made of." },
  { id: "texture", emoji: "🖌️", label: "Texture", hint: "Leave off for engraving - the glass has no colour." },
  { id: "crystal", emoji: "💠", label: "Crystal fit", hint: "Which blank this model is destined for." },
  { id: "output", emoji: "📦", label: "Output", hint: null },
];

// ── Meshy generation options, shared by the image modes ─────────────────────
const MODEL_FIELDS = [
  {
    name: "ai_model",
    emoji: "🤖",
    label: "AI model",
    group: "model",
    type: "select",
    options: ["latest", "meshy-7", "meshy-6", "meshy-5"],
    default: "latest",
    help: "Chooses the standard geometry engine. Latest currently resolves to Meshy 7; Smart Topology selects Meshy T2 automatically instead.",
    optionHelp: {
      latest: "Tracks Meshy's current recommended model; it currently resolves to Meshy 7.",
      "meshy-7": "Highest-fidelity current geometry and the only model with Ultra mode.",
      "meshy-6": "Previous high-quality model; useful for comparison and supports baked-light removal when texturing.",
      "meshy-5": "Legacy, cheaper generation with less surface detail; avoid it for faces unless comparing older output.",
    },
    showWhen: (values) => values.model_type !== "smart-topology",
  },
  {
    name: "model_type",
    emoji: "🧩",
    label: "Model type",
    group: "model",
    type: "select",
    options: ["standard", "smart-topology"],
    default: "standard",
    help: "Standard preserves maximum surface detail. Smart Topology automatically uses Meshy T2, costs 5 credits, and caps the directly generated mesh at 15,000 faces.",
    optionHelp: {
      standard: "Best choice for crystal engraving because it preserves the densest available surface.",
      "smart-topology": "Cleaner separated parts and lower cost, but the 15,000-face ceiling is usually too coarse for a recognizable portrait.",
    },
  },
  {
    name: "smart_polycount",
    emoji: "🔢",
    label: "Smart Topology face count",
    group: "model",
    type: "number",
    default: 15000,
    min: 100,
    max: 15000,
    step: 500,
    help: "Meshy T2 generates directly at this approximate face count. Higher preserves more form; 15,000 is the API maximum.",
    showWhen: (values) => values.model_type === "smart-topology",
  },
  {
    name: "ultra_mode",
    emoji: "💎",
    label: "Ultra mode",
    group: "model",
    type: "boolean",
    default: true,
    help: "Meshy 7 only. Adds 5 credits and generates finer geometry natively; it improves surfaces, not texture resolution.",
    showWhen: (values) =>
      values.model_type !== "smart-topology" && ["latest", "meshy-7"].includes(values.ai_model),
  },
  {
    name: "image_enhancement",
    emoji: "🪄",
    label: "Meshy image enhancement",
    group: "model",
    type: "boolean",
    default: true,
    help: "Lets Meshy optimize the reference before reconstruction. It is independent of the local image pipeline; turn it off only when exact source appearance matters.",
  },
  {
    name: "remove_lighting",
    emoji: "💡",
    label: "Remove baked lighting",
    group: "model",
    type: "boolean",
    default: true,
    help: "Meshy 6 texture option that removes highlights and shadows from base colour. It does not repair geometry and is omitted for other models.",
    showWhen: (values) => values.ai_model === "meshy-6" && values.should_texture,
  },
  {
    name: "pose_mode",
    emoji: "🧍",
    label: "Force pose",
    group: "model",
    type: "select",
    options: ["", "a-pose", "t-pose"],
    default: "",
    help: "Constrains a full-body character to an A- or T-pose. Leave off for portraits, busts, pets, objects and buildings.",
    optionHelp: {
      "": "No forced pose; correct for portraits, busts, pets and objects.",
      "a-pose": "Full-body character with arms angled down; often preserves shoulder shape more naturally.",
      "t-pose": "Full-body character with arms horizontal; useful for rigging, rarely useful for a crystal portrait.",
    },
  },
  {
    name: "moderation",
    emoji: "🛡️",
    label: "Content moderation",
    group: "model",
    type: "boolean",
    default: true,
    help: "Screens image and prompt content before generation. Keep it on for customer material; a rejected task does not proceed.",
  },
];

const MESH_FIELDS = [
  {
    name: "should_remesh",
    emoji: "🕸️",
    label: "Remesh",
    group: "mesh",
    type: "boolean",
    default: false,
    help: "Rebuilds and decimates the surface. Leave it off for crystal engraving so the converter receives Meshy's raw high-density geometry.",
    showWhen: (values) => values.model_type !== "smart-topology",
  },
  {
    name: "topology",
    emoji: "🔺",
    label: "Topology",
    group: "mesh",
    type: "select",
    options: ["triangle", "quad"],
    default: "triangle",
    help: "Triangle creates a decimated triangle mesh; quad creates a quad-dominant mesh. This applies only when Remesh is enabled.",
    optionHelp: {
      triangle: "Best compatibility with the converter and most 3D tools.",
      quad: "Cleaner edge flow for manual editing, but unnecessary for point-cloud sampling.",
    },
    showWhen: (values) => values.model_type !== "smart-topology" && values.should_remesh,
  },
  {
    name: "target_polycount",
    emoji: "🔢",
    label: "Target polycount",
    group: "mesh",
    type: "number",
    default: 300000,
    min: 100,
    max: 300000,
    step: 10000,
    help: "Approximate face count after remeshing, from 100 to 300,000. Higher preserves more detail but creates larger files and slower conversion.",
    showWhen: (values) =>
      values.model_type !== "smart-topology" && values.should_remesh && !values.decimation_mode,
  },
  {
    name: "decimation_mode",
    emoji: "📉",
    label: "Adaptive decimation",
    group: "mesh",
    type: "select",
    options: ["", "1", "2", "3", "4"],
    default: "",
    help: "Adaptive decimation overrides Target polycount: 1 is ultra, 2 high, 3 medium and 4 low. Leave off to use an exact target.",
    optionHelp: {
      "": "Use the explicit Target polycount value instead.",
      "1": "Ultra adaptive polycount; largest output and highest retained detail.",
      "2": "High adaptive polycount; strong detail with a smaller file.",
      "3": "Medium adaptive polycount; general-purpose compromise.",
      "4": "Low adaptive polycount; smallest file and most lost surface detail.",
    },
    showWhen: (values) => values.model_type !== "smart-topology" && values.should_remesh,
  },
  {
    name: "save_pre_remeshed_model",
    emoji: "💾",
    label: "Keep the pre-remesh model too",
    group: "mesh",
    type: "boolean",
    default: true,
    help: "Also returns the dense GLB from before remeshing, so the reduced result can be compared or bypassed. Applies only when Remesh is on.",
    showWhen: (values) => values.model_type !== "smart-topology" && values.should_remesh,
  },
];

const TEXTURE_FIELDS = [
  {
    name: "should_texture",
    emoji: "🖌️",
    label: "Generate texture",
    group: "texture",
    type: "boolean",
    default: false,
    help: "Adds a colour-texture pass (normally 10 credits). Crystal engraving reads geometry only, so leave this off unless you also need a rendered model.",
  },
  {
    name: "texture_resolution",
    emoji: "🖼️",
    label: "Texture resolution",
    group: "texture",
    type: "select",
    options: ["2k", "4k", "8k"],
    default: "2k",
    help: "Controls base-colour texture size. 2K and 4K cost the same; 8K adds 5 credits and substantially increases downloads.",
    optionHelp: {
      "2k": "2048×2048; enough for review and the smallest download.",
      "4k": "4096×4096; more render detail at the same texture credit cost.",
      "8k": "8192×8192; maximum texture detail, 5 extra credits and much larger files.",
    },
    showWhen: (values) => values.should_texture,
  },
  {
    name: "enable_pbr",
    emoji: "🧴",
    label: "PBR maps",
    group: "texture",
    type: "boolean",
    default: false,
    help: "Adds metallic, roughness and normal maps (and emission where supported). These improve rendered materials but have no effect in engraved glass.",
    showWhen: (values) => values.should_texture,
  },
  {
    name: "texture_prompt",
    emoji: "🎨",
    label: "Texture prompt",
    group: "texture",
    type: "text",
    default: "",
    placeholder: "warm skin tones, grey wool coat",
    help: "Up to 600 characters describing colours and materials. It guides only the texture pass and does not change the generated shape.",
    showWhen: (values) => values.should_texture,
  },
];

const CRYSTAL_FIELDS = [
  {
    name: "crystal_template",
    emoji: "💠",
    label: "Crystal blank",
    group: "crystal",
    type: "select",
    options: blankOptions({ noneLabel: "none — decide later in the converter" }),
    default: "60x80x40",
    help: "Recorded on the job and pre-selected when you hand the model to the converter.",
  },
  {
    name: "custom_height",
    emoji: "↕️",
    label: "Custom height (mm)",
    group: "crystal",
    type: "number",
    default: 0,
    min: 0,
    max: 400,
    step: 5,
    help: "Overrides only the target height used for optional Meshy resizing and carried into the converter. Set 0 to use the selected blank.",
  },
  {
    name: "custom_width",
    emoji: "↔️",
    label: "Custom width (mm)",
    group: "crystal",
    type: "number",
    default: 0,
    min: 0,
    max: 400,
    step: 5,
    help: "Overrides only the width carried into the converter. Set 0 to use the selected crystal blank's usable width.",
  },
  {
    name: "custom_depth",
    emoji: "🧊",
    label: "Custom depth (mm)",
    group: "crystal",
    type: "number",
    default: 0,
    min: 0,
    max: 400,
    step: 5,
    help: "Carried over to the converter. Depth is what usually limits a full 3D subject.",
  },
  {
    name: "scale_to_crystal",
    emoji: "📐",
    label: "Scale the model to that size",
    group: "crystal",
    type: "boolean",
    default: false,
    help: "+5 credits for a Meshy remesh that resizes the export to real millimetres. Off is fine - the converter refits it anyway - but it makes the downloaded file measure correctly in Blender or a slicer.",
  },
];

const OUTPUT_FIELDS = [
  {
    name: "target_formats",
    emoji: "📦",
    label: "Download formats",
    group: "output",
    type: "multiselect",
    options: MODEL_FORMATS,
    default: ["glb", "obj"],
    help: "Chooses which files Meshy generates and this server downloads. GLB is mandatory for the local review gate; OBJ enables direct converter handoff.",
    optionHelp: {
      glb: "Compact all-in-one model used by the in-page 3D viewer.",
      obj: "Wavefront mesh read directly by the pipeline converter; required for Meshy-to-DXF handoff.",
      fbx: "Common interchange format for DCC tools such as Blender and Maya.",
      stl: "Triangle-only geometry for slicers and plastic test prints; no texture information.",
      usdz: "Apple AR model package for iPhone/iPad preview.",
      "3mf": "Modern 3D manufacturing package; generated only when explicitly selected.",
    },
  },
  {
    name: "alpha_thumbnail",
    emoji: "🫧",
    label: "Transparent thumbnail",
    group: "output",
    type: "boolean",
    default: true,
    help: "Requests a transparent preview image when Meshy supports it. This affects only the thumbnail, never the model geometry.",
  },
  {
    name: "multi_view_thumbnails",
    emoji: "🔄",
    label: "Four-view thumbnails",
    group: "output",
    type: "boolean",
    default: true,
    help: "Requests front, right, back and left review renders. They are the quickest way to spot missing or collapsed geometry before conversion.",
  },
  {
    name: "origin_at",
    emoji: "🎯",
    label: "Origin",
    group: "output",
    type: "select",
    options: ["center", "bottom"],
    default: "center",
    help: "Centre is what the point-cloud sampler expects - it fits a model about its own middle.",
    optionHelp: {
      center: "Places the model origin at its centre; recommended for the converter's symmetric fitting.",
      bottom: "Places the origin at the bottom; useful when opening the model on a floor plane in Blender or a slicer.",
    },
  },
];

const GENERATION_FIELDS = [
  ...MODEL_FIELDS,
  ...MESH_FIELDS,
  ...TEXTURE_FIELDS,
  ...CRYSTAL_FIELDS,
  ...OUTPUT_FIELDS,
];

// ── Meshy's 2D generators ───────────────────────────────────────────────────
// These produce a picture, not a mesh. They earn their place because a
// generated image can be fed straight back into image-to-3d, and because
// generate_multi_view turns one prompt into the three angles that
// multi-image-to-3d wants.
// Meshy's own reference-image cap. The API reference and the workspace UI
// both say 5; anything above it comes back as a 400, so this is the ceiling
// the form enforces rather than letting a request fail at the far end.
export const IMAGE_TO_IMAGE_MAX_REFERENCES = 5;

export const IMAGE_GEN_MODELS = {
  "nano-banana": 3,
  "nano-banana-2": 6,
  "nano-banana-pro": 9,
  "gpt-image-2": 9,
};

const IMAGE_GEN_FIELDS = [
  {
    name: "ai_model",
    emoji: "🤖",
    label: "Image model",
    group: "model",
    type: "select",
    options: Object.keys(IMAGE_GEN_MODELS),
    default: "nano-banana-2",
    help: "Selects the 2D generator. Price is per returned image: 3, 6 or 9 credits here; Image to Image charges 12 for GPT Image 2.",
    optionHelp: {
      "nano-banana": "Standard 3-credit model; fastest and cheapest for rough references.",
      "nano-banana-2": "Balanced 6-credit model with stronger instruction following.",
      "nano-banana-pro": "Higher-quality 9-credit model; strongest Meshy option for preserving likeness.",
      "gpt-image-2": "High-fidelity 9-credit text generation or 12-credit reference-image edit.",
    },
  },
  {
    name: "aspect_ratio",
    emoji: "🖼️",
    label: "Aspect ratio",
    group: "output",
    type: "select",
    options: ["1:1", "16:9", "9:16", "4:3", "3:4"],
    default: "1:1",
    help: "Sets image framing when Multi-view is off. GPT Image 2 supports 1:1, 16:9, 9:16, 3:2 and 2:3; the Meshy image models use 4:3 and 3:4 instead.",
  },
  {
    name: "generate_multi_view",
    emoji: "🔄",
    label: "Generate multiple views",
    group: "output",
    type: "boolean",
    default: false,
    help: "Returns three consistent angles and charges for three images. They can be reviewed individually; combining them into one mesh requires Multi-Image to 3D access.",
  },
  {
    name: "remove_background",
    emoji: "✂️",
    label: "Transparent background",
    group: "output",
    type: "boolean",
    default: true,
    help: "Returns an RGBA PNG with transparency. This is usually the cleanest direct input for Image to 3D.",
  },
];

/**
 * Every mode, in the order the sidebar lists them.
 *
 * `section` groups the rail, `produces` tells the runner whether to download
 * model files or images, and `photoCount` is how many inputs the mode takes.
 */
export const MESHY_MODES = {
  text_to_image: {
    label: "Text to Image",
    section: "2D",
    blurb:
      "A prompt becomes a reference picture. Useful when there is no usable photograph, or to build the extra angles a single portrait cannot give.",
    kind: "text-to-image",
    produces: "image",
    photoCount: 0,
    fields: [
      {
        name: "prompt",
        emoji: "💬",
        label: "Prompt",
        group: "model",
        type: "text",
        default: "",
        placeholder: "an elderly woman in a wool coat, three-quarter view, plain background",
        help: "Plain, concrete description. Say the view you want.",
      },
      {
        name: "pose_mode",
        emoji: "🧍",
        label: "Force pose",
        group: "model",
        type: "select",
        options: ["", "a-pose", "t-pose"],
        default: "",
        help: "Full-body characters only.",
      },
      ...IMAGE_GEN_FIELDS,
    ],
  },

  image_to_image: {
    label: "Image to Image",
    section: "2D",
    blurb:
      "One to five reference photographs plus a prompt. Turn multi-view on and one portrait becomes the three angles Several photos to 3D needs.",
    kind: "image-to-image",
    produces: "image",
    photoCount: IMAGE_TO_IMAGE_MAX_REFERENCES,
    fields: [
      {
        name: "prompt",
        emoji: "💬",
        label: "Prompt",
        group: "model",
        type: "text",
        default: "",
        placeholder: "same person, plain grey background, even lighting",
        help: "Describe the change you want, not the photograph you already have.",
      },
      ...IMAGE_GEN_FIELDS.map((field) =>
        field.name === "ai_model"
          ? { ...field, help: "3 to 12 credits an image. gpt-image-2 costs 12 here." }
          : field,
      ),
    ],
  },

  image_to_3d: {
    label: "Image to 3D",
    section: "3D",
    blurb:
      "One photograph becomes a full 3D model. Clean the photo locally, send it to Meshy, download the mesh.",
    kind: "image-to-3d",
    produces: "model",
    photoCount: 1,
    fields: GENERATION_FIELDS,
  },

  multi_image_to_3d: {
    label: "Multi-Image to 3D",
    section: "3D",
    blurb:
      "Two to four photographs of the same subject from different angles. Meshy solves a back it can actually see instead of inventing one.",
    kind: "multi-image-to-3d",
    produces: "model",
    photoCount: 4,
    // Not on this account's Meshy plan. Kept rather than deleted so the code
    // is ready the day the plan changes - drop this flag and it works.
    locked: "Not included in this Meshy subscription.",
    fields: GENERATION_FIELDS,
  },

  text_to_3d: {
    label: "Text to 3D",
    section: "3D",
    blurb:
      "No photograph at all - describe the subject and Meshy builds it. Two API calls: an untextured preview, then an optional texture pass.",
    kind: "text-to-3d",
    produces: "model",
    photoCount: 0,
    fields: [
      {
        name: "prompt",
        emoji: "💬",
        label: "Prompt",
        group: "model",
        type: "text",
        default: "",
        placeholder: "Hallgrimskirkja, Reykjavik, seen from the front",
        help: "Max 600 characters. Concrete nouns beat adjectives.",
      },
      ...MODEL_FIELDS.filter(
        (field) => !["image_enhancement", "remove_lighting", "moderation"].includes(field.name),
      ),
      { ...MODEL_FIELDS.find((field) => field.name === "moderation") },
      ...MESH_FIELDS,
      ...TEXTURE_FIELDS,
      ...CRYSTAL_FIELDS,
      ...OUTPUT_FIELDS,
    ],
  },
};

/** Default form state for one mode, used when the mode picker changes. */
export function defaultMeshyValues(modeKey) {
  const mode = MESHY_MODES[modeKey];
  if (!mode) return {};
  return Object.fromEntries(mode.fields.map((field) => [field.name, field.default]));
}

/** Groups actually present on a mode, in canonical order. */
export function meshyGroupsFor(modeKey) {
  const mode = MESHY_MODES[modeKey];
  if (!mode) return [];
  const present = new Set(mode.fields.map((field) => field.group || "output"));
  return MESHY_FIELD_GROUPS.filter((group) => present.has(group.id));
}

/**
 * Fields with API-valid option lists for the current form state.
 *
 * Meshy exposes different image aspect ratios by model, and Meshy 5 cannot
 * produce 4K/8K textures. Keeping those invalid choices out of the select is
 * clearer than letting a paid request fail remotely.
 */
export function meshyFieldsFor(modeKey, values = {}) {
  const fields = MESHY_MODES[modeKey]?.fields || [];
  return fields.map((field) => {
    if (field.name === "aspect_ratio") {
      return {
        ...field,
        options:
          values.ai_model === "gpt-image-2"
            ? ["1:1", "16:9", "9:16", "3:2", "2:3"]
            : ["1:1", "16:9", "9:16", "4:3", "3:4"],
      };
    }
    if (field.name === "texture_resolution" && values.ai_model === "meshy-5") {
      return { ...field, options: ["2k"] };
    }
    return field;
  });
}

/**
 * What this job will cost, from Meshy's published table.
 *
 * An estimate, not a quote - Meshy reports the real figure as
 * consumed_credits once the task finishes, and that is what the job records.
 */
export function estimateCredits(modeKey, values = {}) {
  const mode = MESHY_MODES[modeKey];

  // The 2D generators price per image off a flat per-model rate, and
  // gpt-image-2 costs three more on image-to-image than on text-to-image.
  if (mode?.produces === "image") {
    const perImage =
      IMAGE_GEN_MODELS[values.ai_model] ??
      IMAGE_GEN_MODELS["nano-banana-2"];
    const surcharge = modeKey === "image_to_image" && values.ai_model === "gpt-image-2" ? 3 : 0;
    // Multi-view returns three angles and is billed as three images.
    return (perImage + surcharge) * (values.generate_multi_view ? 3 : 1);
  }

  const smart = values.model_type === "smart-topology";
  const legacy = !smart && values.ai_model === "meshy-5";
  const textured = Boolean(values.should_texture);
  const eightK = textured && values.texture_resolution === "8k";

  let credits = smart ? 5 : legacy ? 5 : 20;

  // Image modes include texture in their single task. Text to 3D charges a
  // separate refine pass, so it must not first be counted as a textured image
  // task and then counted again.
  if (textured) {
    if (modeKey === "text_to_3d") credits += eightK ? 15 : 10;
    else if (smart) credits = eightK ? 20 : 15;
    else if (legacy) credits = 15;
    else credits = eightK ? 35 : 30;
  }

  // Ultra is meshy-7 only and adds a flat 5.
  if (
    !smart &&
    values.ultra_mode &&
    ["latest", "meshy-7"].includes(values.ai_model)
  ) {
    credits += 5;
  }
  // The optional resize is its own remesh task.
  if (values.scale_to_crystal) credits += 5;

  return credits;
}

/** Drop keys Meshy would reject as empty, so the request body stays minimal. */
function compact(payload) {
  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => {
      if (value === "" || value === null || value === undefined) return false;
      if (Array.isArray(value) && value.length === 0) return false;
      return true;
    }),
  );
}

/**
 * Turn the form into a Meshy create-task body.
 *
 * Texture keys are omitted entirely when texturing is off - Meshy rejects a
 * texture_prompt alongside should_texture:false rather than ignoring it.
 */
export function buildMeshyPayload(modeKey, values = {}, images = []) {
  // ── The 2D generators take an entirely different body ─────────────────────
  if (MESHY_MODES[modeKey]?.produces === "image") {
    const multiView = Boolean(values.generate_multi_view);
    const body = {
      ai_model: values.ai_model,
      prompt: String(values.prompt || "").slice(0, 600),
      remove_background: Boolean(values.remove_background),
      // Meshy rejects the two together rather than picking one.
      ...(multiView ? { generate_multi_view: true } : { aspect_ratio: values.aspect_ratio }),
    };

    if (modeKey === "image_to_image") {
      return compact({ ...body, reference_image_urls: images });
    }
    return compact({ ...body, pose_mode: values.pose_mode });
  }

  const textured = Boolean(values.should_texture);
  const targetFormats = [...new Set(["glb", ...(values.target_formats || [])])];
  const smart = values.model_type === "smart-topology";
  const standardModel = values.ai_model || "latest";
  const ultra =
    !smart && Boolean(values.ultra_mode) && ["latest", "meshy-7"].includes(standardModel);

  const base = {
    ai_model: smart ? "meshy-t2" : standardModel,
    model_type: smart ? "smart-topology" : "standard",
    ...(smart
      ? { target_polycount: Math.min(15000, Math.max(100, Number(values.smart_polycount) || 15000)) }
      : {
          ultra_mode: ultra,
          should_remesh: Boolean(values.should_remesh),
          ...(values.should_remesh
            ? { save_pre_remeshed_model: Boolean(values.save_pre_remeshed_model) }
            : {}),
        }),
    moderation: Boolean(values.moderation),
    should_texture: textured,
    target_formats: targetFormats,
    alpha_thumbnail: Boolean(values.alpha_thumbnail),
    origin_at: values.origin_at,
  };

  if (!smart && values.should_remesh) {
    base.topology = values.topology;
    if (values.decimation_mode) base.decimation_mode = Number(values.decimation_mode);
    else base.target_polycount = Number(values.target_polycount);
  }

  if (textured) {
    base.texture_resolution = values.texture_resolution;
    base.enable_pbr = Boolean(values.enable_pbr);
    if (values.texture_prompt) base.texture_prompt = values.texture_prompt.slice(0, 600);
  }

  if (modeKey === "text_to_3d") {
    // Preview builds geometry only; texturing is a second refine call.
    return compact({
      ...base,
      mode: "preview",
      prompt: String(values.prompt || "").slice(0, 600),
      pose_mode: values.pose_mode,
      should_texture: undefined,
      texture_resolution: undefined,
      enable_pbr: undefined,
      texture_prompt: undefined,
    });
  }

  const imageKeys = {
    ...(!smart && ["latest", "meshy-7", "meshy-6"].includes(standardModel)
      ? { image_enhancement: Boolean(values.image_enhancement) }
      : {}),
    ...(!smart && standardModel === "meshy-6" && textured
      ? { remove_lighting: Boolean(values.remove_lighting) }
      : {}),
    pose_mode: values.pose_mode,
    multi_view_thumbnails: Boolean(values.multi_view_thumbnails),
  };

  if (modeKey === "multi_image_to_3d") {
    return compact({ ...base, ...imageKeys, image_urls: images });
  }
  return compact({ ...base, ...imageKeys, image_url: images[0] });
}
