/*
 * ═══════════════════════════════════════════════════════════════
 * Direct R2 Upload
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/upload-to-r2.js
 * Purpose: Send a file from the browser straight into the bucket.
 *
 * Two requests: ask this server to sign a URL, then PUT the bytes to R2
 * without them passing through the server at all. That second request is
 * cross-origin, which is the whole reason the bucket needs a CORS policy
 * allowing PUT from https://pipeline.acm.is.
 *
 * XMLHttpRequest rather than fetch, only because fetch still has no upload
 * progress event and a 300 MB model deserves a progress bar.
 */

import { readResponseJson } from "@/lib/response-json";

/** Ask the server for a signed URL, then PUT the file to it. */
export async function uploadToR2(file, { prefix = "uploads", onProgress } = {}) {
  const signResponse = await fetch("/api/r2/presign", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fileName: file.name, prefix }),
  });

  const signed = await readResponseJson(signResponse);
  if (!signResponse.ok) throw new Error(signed.error || "Could not sign the upload");

  await new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("PUT", signed.url, true);

    // Must match the type the signature was made for, or R2 rejects it.
    request.setRequestHeader("Content-Type", signed.contentType);

    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(event.loaded / event.total);
    };

    request.onload = () =>
      request.status >= 200 && request.status < 300
        ? resolve()
        : reject(
            new Error(
              request.status === 0
                ? "The bucket refused the request. Check its CORS policy allows PUT from this origin."
                : `R2 returned ${request.status}`,
            ),
          );

    request.onerror = () =>
      reject(new Error("Upload failed. Check the bucket's CORS policy allows PUT from this origin."));

    request.send(file);
  });

  return signed;
}
