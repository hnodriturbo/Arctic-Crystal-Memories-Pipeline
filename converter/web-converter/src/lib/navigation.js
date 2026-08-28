/*
 * ═══════════════════════════════════════════════════════════════
 * Navigation
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/navigation.js
 * Purpose: The sidebar's contents - one clear menu for each of the three
 *          pipelines, followed by a small system-status section.
 *
 * Numbered, but not a wizard. Every pipeline reads from its own folder, so
 * any of them is a valid starting point. The order still communicates the
 * normal handoff: image -> Meshy -> converter.
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
    id: "pipeline-converter",
    step: 3,
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

/** The Meshy mode behind a nav id, or null for the local views. */
export function meshyModeFor(navId) {
  return navId.startsWith("meshy:") ? navId.slice("meshy:".length) : null;
}
