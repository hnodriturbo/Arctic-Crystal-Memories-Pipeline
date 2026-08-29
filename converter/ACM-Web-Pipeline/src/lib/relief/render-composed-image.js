/*
 * ═══════════════════════════════════════════════════════════════
 * Composed Crystal Image Renderer
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/relief/render-composed-image.js
 * Purpose: Bake the Leið A crop, Cockpit blank shape and optional text into
 *          the PNG consumed by the local 2.5D pipeline.
 */

const OUTPUT_SIZE = 1600;
const VISUAL_BEVEL_SCALE = 0.64;

function addChamferedRect(context, x, y, width, height, cut) {
  context.beginPath();
  context.moveTo(x + cut, y);
  context.lineTo(x + width - cut, y);
  context.lineTo(x + width, y + cut);
  context.lineTo(x + width, y + height - cut);
  context.lineTo(x + width - cut, y + height);
  context.lineTo(x + cut, y + height);
  context.lineTo(x, y + height - cut);
  context.lineTo(x, y + cut);
  context.closePath();
}

function proceduralPoints(blank) {
  if (blank.family === "diamond") {
    return [[0.1, 0], [0.9, 0], [1, 0.1], [1, 0.9], [0.9, 1], [0.1, 1], [0, 0.9], [0, 0.1]];
  }
  const name = blank.name.toLowerCase();
  if (name.includes("notched")) {
    return [[0.07, 0], [0.93, 0], [1, 0.07], [1, 0.88], [0.88, 1], [0.12, 1], [0, 0.88], [0, 0.07]];
  }
  if (name.includes("urn")) return [[0.08, 0], [0.92, 0], [1, 0.08], [0.96, 1], [0.04, 1], [0, 0.08]];
  return null;
}

function addBlankPath(context, blank, frame, chamfer) {
  const points = blank.maskPoints?.length >= 3 ? blank.maskPoints : proceduralPoints(blank);
  if (points) {
    context.beginPath();
    points.forEach(([x, y], index) => {
      const canvasX = frame.x + x * frame.width;
      const canvasY = frame.y + y * frame.height;
      if (index === 0) context.moveTo(canvasX, canvasY);
      else context.lineTo(canvasX, canvasY);
    });
    context.closePath();
  } else if (blank.family === "ornament") {
    context.beginPath();
    context.ellipse(
      frame.x + frame.width / 2,
      frame.y + frame.height / 2,
      frame.width / 2,
      frame.height / 2,
      0,
      0,
      Math.PI * 2,
    );
    context.closePath();
  } else {
    addChamferedRect(context, frame.x, frame.y, frame.width, frame.height, chamfer);
  }
}

function crystalFrame(blank) {
  const ratio = blank.width / blank.height;
  const maximum = OUTPUT_SIZE * 0.82;
  const width = ratio >= 1 ? maximum : maximum * ratio;
  const height = ratio >= 1 ? maximum / ratio : maximum;
  return { x: (OUTPUT_SIZE - width) / 2, y: (OUTPUT_SIZE - height) / 2, width, height };
}

function toBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("PNG export failed."))), "image/png");
  });
}

export async function renderComposedImage({ croppedCanvas, blank, textValue, showBackground }) {
  const canvas = document.createElement("canvas");
  canvas.width = OUTPUT_SIZE;
  canvas.height = OUTPUT_SIZE;
  const context = canvas.getContext("2d");
  const frame = crystalFrame(blank);
  const fallbackBevel = Math.min(...(blank.border || [3, 3, 3]).filter((value) => value > 0)) || 3;
  const bevelMm = blank.bevel || fallbackBevel;
  const bevel = Math.max(16, (frame.width / blank.width) * bevelMm * VISUAL_BEVEL_SCALE);
  const border = blank.border || [bevelMm, bevelMm, bevelMm];
  const insetX = Math.max(12, frame.width * (border[0] / blank.width) * VISUAL_BEVEL_SCALE);
  const insetY = Math.max(12, frame.height * (border[1] / blank.height) * VISUAL_BEVEL_SCALE);

  const ambient = context.createLinearGradient(0, 0, OUTPUT_SIZE, OUTPUT_SIZE);
  ambient.addColorStop(0, "#00324d");
  ambient.addColorStop(0.48, "#07090c");
  ambient.addColorStop(1, "#6a3400");
  context.fillStyle = ambient;
  context.fillRect(0, 0, OUTPUT_SIZE, OUTPUT_SIZE);

  const edge = context.createLinearGradient(frame.x, frame.y, frame.x + frame.width, frame.y + frame.height);
  edge.addColorStop(0, "#85867f");
  edge.addColorStop(0.17, "#292a27");
  edge.addColorStop(0.62, "#101210");
  edge.addColorStop(0.8, "#c4c6ca");
  edge.addColorStop(1, "#555650");
  context.fillStyle = edge;
  addBlankPath(context, blank, frame, bevel);
  context.fill();

  const face = {
    x: frame.x + insetX,
    y: frame.y + insetY,
    width: Math.max(1, frame.width - insetX * 2),
    height: Math.max(1, frame.height - insetY * 2),
  };
  context.save();
  addBlankPath(context, blank, face, Math.max(10, bevel * 0.34));
  context.clip();
  context.fillStyle = showBackground ? "#15151a" : "rgba(0,0,0,0)";
  context.fillRect(face.x, face.y, face.width, face.height);
  context.filter = "grayscale(1) contrast(1.08)";
  context.drawImage(croppedCanvas, face.x, face.y, face.width, face.height);
  context.restore();

  if (textValue.trim()) {
    context.save();
    context.textAlign = "center";
    context.textBaseline = "bottom";
    context.font = `600 ${Math.round(OUTPUT_SIZE * 0.032)}px sans-serif`;
    context.lineJoin = "round";
    context.lineWidth = 7;
    context.strokeStyle = "#080808";
    context.fillStyle = "#ffffff";
    context.strokeText(textValue.trim(), face.x + face.width / 2, face.y + face.height - 40, face.width * 0.88);
    context.fillText(textValue.trim(), face.x + face.width / 2, face.y + face.height - 40, face.width * 0.88);
    context.restore();
  }
  return toBlob(canvas);
}
