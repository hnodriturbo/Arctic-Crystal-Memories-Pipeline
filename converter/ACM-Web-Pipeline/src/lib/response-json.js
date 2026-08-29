/*
 * ═══════════════════════════════════════════════════════════════
 * Response JSON
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/response-json.js
 * Purpose: Turn API responses into JSON without exposing raw proxy HTML as a
 *          confusing "Unexpected token '<'" parsing error.
 */

/** Parse one API response and replace proxy/CDN HTML with an actionable error. */
export async function readResponseJson(response) {
  const text = await response.text();
  if (!text.trim()) return {};

  try {
    return JSON.parse(text);
  } catch {
    const looksLikeHtml = /^\s*</.test(text);
    const status = `${response.status}${response.statusText ? ` ${response.statusText}` : ""}`;

    if (response.status === 413) {
      throw new Error(
        "The upload was larger than the website proxy permits. Upload it to R2 instead.",
      );
    }

    throw new Error(
      looksLikeHtml
        ? `Server returned an HTML error page (${status}) instead of JSON.`
        : `Server returned an unreadable response (${status}).`,
    );
  }
}
