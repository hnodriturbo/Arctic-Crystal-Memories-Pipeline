/*
 * ═══════════════════════════════════════════════════════════════
 * Prompt Writer
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/meshy/vision.js
 * Purpose: Let OpenAI look at a photo and write the Meshy prompt for it.
 *
 * Meshy takes the photo itself for geometry, but a prompt still steers the
 * parts a single view cannot show - the back of a head, what a cropped torso
 * is wearing - and text-to-3d has nothing but the prompt to work from.
 */

const OPENAI_URL = "https://api.openai.com/v1/responses";

/** Optional feature: without a key the UI hides the button rather than failing. */
export function visionConfigured() {
  return Boolean(process.env.OPENAI_API_KEY);
}

const SYSTEM_PROMPT = [
  "You write prompts for Meshy, an image-to-3D and text-to-3D model generator.",
  "The finished mesh is engraved inside a solid glass crystal, so geometry is everything",
  "and colour is worthless - never describe lighting, background, mood, or photographic style.",
  "",
  "Return JSON only, with exactly these keys:",
  '  "subject"  - two to five words naming the subject, usable as a filename.',
  '  "prompt"   - under 600 characters. Describe the physical form: pose, proportions,',
  "               hair shape and volume, clothing structure and folds, accessories such as",
  "               glasses or jewellery, and what the unseen back and sides most likely look like.",
  '  "texture_prompt" - under 300 characters, colours and materials only. Used only if the',
  "               operator turns texturing on.",
  '  "notes"    - one sentence on anything that will make this photo hard to solve in 3D',
  "               (heavy crop, motion blur, another person overlapping, hands over the face).",
].join("\n");

/** Pull the assistant's text out of a Responses payload, whichever shape it arrives in. */
function extractText(body) {
  if (typeof body?.output_text === "string" && body.output_text.trim()) {
    return body.output_text;
  }

  const parts = [];
  for (const item of body?.output || []) {
    for (const chunk of item?.content || []) {
      if (typeof chunk?.text === "string") parts.push(chunk.text);
    }
  }
  return parts.join("\n").trim();
}

/** Models sometimes fence their JSON; take the first object either way. */
function parseLoosely(text) {
  const stripped = text.replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
  try {
    return JSON.parse(stripped);
  } catch {
    const match = /\{[\s\S]*\}/.exec(stripped);
    if (!match) return null;
    try {
      return JSON.parse(match[0]);
    } catch {
      return null;
    }
  }
}

/**
 * Describe one photo as a Meshy prompt.
 *
 * `image` is a data URI - the same one that goes to Meshy, so the model is
 * looking at exactly the cleaned-up photo the generator will receive.
 */
export async function describePhoto(image, { hint = "" } = {}) {
  if (!visionConfigured()) {
    throw new Error("OPENAI_API_KEY is not set. Add it to .env.local and restart the dev server.");
  }

  const instruction = hint
    ? `Describe this photograph for Meshy. The operator adds: ${hint}`
    : "Describe this photograph for Meshy.";

  const response = await fetch(OPENAI_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: process.env.OPENAI_VISION_MODEL || "gpt-5.6-luna",
      input: [
        { role: "system", content: [{ type: "input_text", text: SYSTEM_PROMPT }] },
        {
          role: "user",
          content: [
            { type: "input_text", text: instruction },
            { type: "input_image", image_url: image },
          ],
        },
      ],
    }),
  });

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = body?.error?.message || `OpenAI returned ${response.status}.`;
    throw new Error(detail);
  }

  const text = extractText(body);
  if (!text) throw new Error("OpenAI returned an empty response.");

  const parsed = parseLoosely(text);
  if (!parsed) {
    // Still useful - hand the raw text over as the prompt rather than failing.
    return { subject: "", prompt: text.slice(0, 600), texture_prompt: "", notes: "" };
  }

  return {
    subject: String(parsed.subject || "").slice(0, 60),
    prompt: String(parsed.prompt || "").slice(0, 600),
    texture_prompt: String(parsed.texture_prompt || "").slice(0, 300),
    notes: String(parsed.notes || "").slice(0, 400),
  };
}
