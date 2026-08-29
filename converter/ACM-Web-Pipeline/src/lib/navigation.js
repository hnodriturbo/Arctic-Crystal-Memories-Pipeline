/*
 * ═══════════════════════════════════════════════════════════════
 * Navigation
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/navigation.js
 * Purpose: The sidebar's contents - one clear menu for each of the four
 *          pipelines, followed by a small system-status section.
 *
 * Numbered, but not a wizard. Every pipeline reads from its own folder, so
 * any of them is a valid starting point. The order still communicates the
 * normal handoff: image -> Meshy or 2.5D -> converter. Steps 2 and 3 are
 * alternatives, not a sequence: Meshy solves a full 3D subject, the 2.5D
 * pipeline builds a relief, and a job goes through one of them, not both.
 *
 * Locked entries stay listed on purpose. A greyed row with a reason answers
 * "can this do X?" far better than an absence does, and unlocking one is a
 * matter of deleting its `locked` line.
 */

export const SECTIONS = [
  {
    id: "image-pipeline",
    step: 1,
    label: "Image pipeline",
    hint: "Photograph in · prepared PNG out",
    items: [
      {
        id: "library",
        emoji: "📚",
        label: "Inputs and library",
        blurb: "Upload source photographs and see the files available to the image and Meshy pipelines.",
        icon: "photo",
      },
      {
        id: "image",
        emoji: "🪄",
        label: "Prepare images",
        blurb: "Restore, upscale and remove the background, then send the chosen result directly to Meshy.",
        icon: "wand",
      },
    ],
  },
  {
    id: "meshy-pipeline",
    step: 2,
    label: "Meshy pipeline",
    hint: "Images or text in · 2D/3D assets out",
    items: [
      {
        id: "meshy:image_to_3d",
        emoji: "🧊",
        label: "Image to 3D",
        blurb: "Upload a separate Meshy image or use an image-pipeline result to generate a 3D mesh.",
        icon: "cube",
      },
      {
        id: "meshy:multi_image_to_3d",
        emoji: "🎞️",
        label: "Multi-Image to 3D",
        blurb: "Use several angles of the same subject to generate one more complete mesh.",
        icon: "cubes",
        locked: "Not included in the current Meshy subscription.",
      },
      {
        id: "meshy:text_to_3d",
        emoji: "💬",
        label: "Text to 3D",
        blurb: "Generate a mesh directly from a written description.",
        icon: "text",
      },
      {
        id: "meshy:text_to_image",
        emoji: "🎨",
        label: "Text to Image",
        blurb: "No usable photograph? Have Meshy draw the reference instead.",
        icon: "sparkle",
      },
      {
        id: "meshy:image_to_image",
        emoji: "🖼️",
        label: "Image to Image",
        blurb: "Reference photos plus a prompt — re-light, re-frame, or clean up.",
        icon: "layers",
      },
      {
        id: "review",
        emoji: "👁️",
        label: "Jobs and review",
        blurb: "Review every Meshy result, download its files, or hand an OBJ directly to the converter.",
        icon: "eye",
      },
    ],
  },
  {
    id: "2.5D-pipeline",
    step: 3,
    label: "2.5D pipeline",
    hint: "Leið A → 2.5D → Leið B",
    items: [
      {
        id: "composer",
        emoji: "🖼️",
        label: "Leið A · Prepare photo",
        blurb:
          "Crop and compose the customer photograph inside a local Cockpit3D blank, then send the finished PNG straight into 2.5D.",
        icon: "photo",
      },
      {
        id: "relief",
        emoji: "🏔️",
        label: "2.5D · AutoConvertTo3D",
        blurb:
          "Turn a photograph into a depth map and a relief mesh, and see it inside real glass before it goes anywhere.",
        icon: "cube",
      },
      {
        id: "viewer",
        emoji: "🔮",
        label: "Leið B · GLB viewer",
        blurb:
          "Drop in a GLB, a point-cloud DXF or a plain photograph and look at it inside a blank. The prototype for the acm.is viewer.",
        icon: "eye",
      },
    ],
  },
  {
    id: "pipeline-converter",
    step: 4,
    label: "Pipeline converter",
    hint: "3D/CAD in · DXF, OBJ and point clouds out",
    items: [
      {
        id: "converter",
        emoji: "💠",
        label: "Convert and export",
        blurb: "Create printer DXF from Meshy OBJ, convert CAD/DXF to OBJ, or inspect and repair point clouds.",
        icon: "dots",
      },
    ],
  },
  {
    id: "system",
    label: "System",
    hint: "What this machine can actually do",
    items: [
      {
        id: "environments",
        emoji: "🐍",
        label: "Python environments",
        blurb: "Which engines are installed, and what 'auto' resolves to here.",
        icon: "wrench",
      },
    ],
  },
];

/** Flat lookup, since the shell addresses items by id. */
export const NAV_ITEMS = Object.fromEntries(
  SECTIONS.flatMap((section) => section.items.map((item) => [item.id, { ...item, section }])),
);

/**
 * URL state stays separate from internal component ids. The public slugs are
 * readable, stable and safe to bookmark, while internal ids can keep the
 * punctuation used by Meshy mode selection.
 */
export const DEFAULT_NAV_ID = "library";
export const NAVIGATION_QUERY_PARAM = "view";

const NAV_SLUGS = {
  library: "inputs-library",
  image: "prepare-images",
  "meshy:image_to_3d": "meshy-image-to-3d",
  "meshy:multi_image_to_3d": "meshy-multi-image-to-3d",
  "meshy:text_to_3d": "meshy-text-to-3d",
  "meshy:text_to_image": "meshy-text-to-image",
  "meshy:image_to_image": "meshy-image-to-image",
  review: "meshy-review",
  composer: "crystal-composer",
  relief: "autoconvert-to-3d",
  viewer: "crystal-glb-viewer",
  converter: "convert-export",
  environments: "python-environments",
};

const NAV_IDS_BY_SLUG = Object.fromEntries(
  Object.entries(NAV_SLUGS).map(([navId, slug]) => [slug, navId]),
);

/** Return the canonical public URL slug for an internal navigation id. */
export function navSlugFor(navId) {
  return NAV_SLUGS[navId] || NAV_SLUGS[DEFAULT_NAV_ID];
}

/**
 * Resolve a public slug safely. Existing internal ids remain accepted as
 * temporary backwards-compatible links, but the shell canonicalizes them.
 */
export function navIdForSlug(slug) {
  if (typeof slug !== "string") return DEFAULT_NAV_ID;
  return NAV_IDS_BY_SLUG[slug] || (NAV_ITEMS[slug] ? slug : DEFAULT_NAV_ID);
}

/** The Meshy mode behind a nav id, or null for the local views. */
export function meshyModeFor(navId) {
  return navId.startsWith("meshy:") ? navId.slice("meshy:".length) : null;
}
