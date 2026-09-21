/*
 * ═══════════════════════════════════════════════════════════════
 * Render Design Video
 * ═══════════════════════════════════════════════════════════════
 * Path: scripts/render-design-video.mjs
 * Purpose: Turn one Claude Design animation into an MP4, frame by frame.
 *
 * Why a virtual clock rather than a screen recording: the page is advanced by
 * hand, believing that exactly 1/60 of a second passed between frames however
 * long the work actually took. The result is therefore always smooth 60fps,
 * on a loaded VPS as much as on an idle desktop. No recorder can promise that.
 *
 * Spawned by src/lib/claude-design/render-jobs.js, never run by hand, so every
 * input arrives as an explicit flag and nothing is guessed from a file name.
 *
 *   --dir <folder>       folder holding the design
 *   --file <name>        the .html or .dc.html inside it
 *   --out <path>         absolute path of the mp4 to write
 *   --poster <path>      optional jpg written from one second in
 *   --size 1920x1080     frame size
 *   --serve-root <dir>   serve this folder on loopback and load the page from it
 *   --url <address>      load some other address instead (manual override)
 *   --seconds <n>        override the length read from the design
 *   --fps --crf --site-scale --site-gap
 *   --keep-chrome        leave the design's own player bar visible
 *   --json-progress      emit @@{...} progress lines for the console panel
 */

import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { pathToFileURL } from "node:url";

import puppeteer from "puppeteer";

// ========================================
// Arguments
// ========================================

const args = process.argv.slice(2);
const flag = (name, fallback) => {
  const index = args.indexOf("--" + name);
  return index >= 0 ? args[index + 1] : fallback;
};
const has = (name) => args.includes("--" + name);

const SRC_DIR = flag("dir", null);
const SRC_FILE = flag("file", null);
const OUT_PATH = flag("out", null);
const POSTER_PATH = flag("poster", null);
const PAGE_URL = flag("url", null);
const SERVE_ROOT = flag("serve-root", null);
const SIZE = flag("size", "1920x1080");
const FPS = Number(flag("fps", 60));
const CRF = Number(flag("crf", 18));
const SECONDS_OVERRIDE = flag("seconds", null);
const KEEP_CHROME = has("keep-chrome");
const JSON_LOG = has("json-progress");

// The closing scene's www.acm.is sits too small and too close to the artwork
// above it. Corrected at capture time rather than in the HTML, so a fresh
// export out of Claude Design never silently overwrites the fix.
const SITE_SCALE = Number(flag("site-scale", 1.6));
const SITE_GAP = Number(flag("site-gap", 40));

if (!SRC_DIR || !SRC_FILE || !OUT_PATH) {
  console.error("Need --dir, --file and --out.");
  process.exit(1);
}

const [WIDTH, HEIGHT] = SIZE.toLowerCase().split("x").map(Number);
if (!WIDTH || !HEIGHT) {
  console.error(`Could not read a frame size from --size ${SIZE}`);
  process.exit(1);
}

/** One machine-readable line the console panel parses. Silent without the flag. */
function emit(event, data) {
  if (JSON_LOG) console.log("@@" + JSON.stringify({ event, ...data }));
}

// ========================================
// Virtual clock - installed inside the page
// ========================================

// Replaces requestAnimationFrame and setTimeout so nothing advances on its own.
// step(ms) moves time forward and runs whatever was due at that moment.
function installVirtualClock() {
  let now = 0;
  let id = 0;
  const frames = new Map();
  const timers = [];

  window.requestAnimationFrame = (callback) => {
    const handle = ++id;
    frames.set(handle, callback);
    return handle;
  };
  window.cancelAnimationFrame = (handle) => frames.delete(handle);
  window.setTimeout = (fn, ms = 0, ...rest) => {
    const handle = ++id;
    timers.push({ handle, at: now + ms, fn, rest });
    return handle;
  };
  window.clearTimeout = (handle) => {
    const index = timers.findIndex((timer) => timer.handle === handle);
    if (index >= 0) timers.splice(index, 1);
  };
  performance.now = () => now;

  window.__vt = {
    get now() {
      return now;
    },
    step(ms) {
      now += ms;
      for (let index = timers.length - 1; index >= 0; index--) {
        if (timers[index].at <= now) {
          const timer = timers.splice(index, 1)[0];
          try {
            timer.fn(...timer.rest);
          } catch {
            // One broken timer must not stop the rest of the frame.
          }
        }
      }
      const due = [...frames.entries()];
      frames.clear();
      for (const [, callback] of due) {
        try {
          callback(now);
        } catch {
          // Same here - keep stepping.
        }
      }
    },
  };
}

/**
 * Hide the design's own player bar and loading marker.
 *
 * The bar carries neither id nor class, so it is identified by shape and
 * position instead: a short box across the bottom of the screen containing a
 * button. Returns false when nothing matched, which is worth reporting - it
 * means the first frame should be checked by eye before the file is used.
 */
function hideChrome() {
  const bar = [...document.querySelectorAll("div")].find((element) => {
    const box = element.getBoundingClientRect();
    return (
      box.height > 20 &&
      box.height < 80 &&
      box.top > innerHeight - 90 &&
      box.width > 300 &&
      element.querySelector("button")
    );
  });
  if (bar) bar.style.display = "none";
  document.getElementById("__bundler_loading")?.remove();
  document.getElementById("__bundler_thumbnail")?.remove();
  return Boolean(bar);
}

/** Remove only the loading marker, for a render that keeps the player bar. */
function hideLoadingOnly() {
  document.getElementById("__bundler_loading")?.remove();
  document.getElementById("__bundler_thumbnail")?.remove();
  return true;
}

/**
 * The rule is written into its own stylesheet with !important, so it survives
 * the page repainting between frames, and the element is tagged with a data
 * attribute rather than styled directly for the same reason.
 */
function installSiteStyle(scale, gap) {
  const style = document.createElement("style");
  style.id = "__acm_site_style";
  style.textContent =
    `[data-acm-site]{font-size:var(--acm-site-fs) !important}` +
    `[data-acm-site-wrap]{margin-top:${gap}px !important}`;
  document.head.appendChild(style);
}

/** The closing scene is not in the DOM at the start, so this is retried until it is. */
function markSiteText(scale) {
  if (document.querySelector("[data-acm-site]")) return true;
  const element = [...document.querySelectorAll("div")].find(
    (node) => node.children.length === 0 && node.textContent.trim().toLowerCase() === "www.acm.is",
  );
  if (!element) return false;
  const original = parseFloat(getComputedStyle(element).fontSize);
  document.documentElement.style.setProperty("--acm-site-fs", (original * scale).toFixed(1) + "px");
  element.setAttribute("data-acm-site", "");
  element.parentElement.setAttribute("data-acm-site-wrap", "");
  return true;
}

// ========================================
// Serving the design to the browser
// ========================================

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".jsx": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".avif": "image/avif",
  ".mp4": "video/mp4",
  ".webm": "video/webm",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".otf": "font/otf",
};

/**
 * A static file server for the design tree, on loopback, for this render only.
 *
 * A `.dc.html` fetches its `.jsx` scenes at runtime and a browser refuses that
 * from `file://`, so the page has to come over http. It is served from here
 * rather than from the application for two reasons: the renderer's browser has
 * no operator session, and an unauthenticated request to the app is redirected
 * to the public sign-in URL - where, on the live host, Cloudflare answers a
 * headless browser with a bot check and the render captures that instead of
 * the design.
 *
 * Bound to 127.0.0.1 on a port the OS picks, closed the moment the render
 * finishes, and it never leaves the machine.
 */
function serveDesignTree(root) {
  const server = http.createServer((request, response) => {
    const relative = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname).replace(
      /^\/+/,
      "",
    );
    const absolute = path.resolve(root, relative);

    // Even on loopback: a design that asks for ../../etc/passwd gets nothing.
    const rootWithSeparator = root.endsWith(path.sep) ? root : root + path.sep;
    if (absolute !== root && !absolute.startsWith(rootWithSeparator)) {
      response.writeHead(403).end();
      return;
    }

    let info;
    try {
      info = fs.statSync(absolute);
    } catch {
      response.writeHead(404).end();
      return;
    }
    if (!info.isFile()) {
      response.writeHead(404).end();
      return;
    }

    response.writeHead(200, {
      "Content-Type": MIME[path.extname(absolute).toLowerCase()] || "application/octet-stream",
      "Content-Length": info.size,
      "Cache-Control": "no-store",
    });
    fs.createReadStream(absolute).pipe(response);
  });

  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => resolve({ server, port: server.address().port }));
  });
}

// ========================================
// Preflight
// ========================================

/** Better to stop now with a clear sentence than half way through a render. */
function requireFfmpeg() {
  const probe = spawnSync("ffmpeg", ["-version"], {
    stdio: "ignore",
    shell: process.platform === "win32",
  });
  if (probe.error || probe.status !== 0) {
    console.error("ffmpeg is not on PATH. Install it and run this again.");
    process.exit(1);
  }
}

/** Scene length straight out of the design, so a redesign needs no edit here. */
function durationOf(file) {
  try {
    const html = fs.readFileSync(file, "utf8");
    const match = html.match(/OM_SCENES\s*=\s*'(\[.*?\])'/s);
    if (!match) return null;
    const scenes = JSON.parse(match[1].replace(/\\"/g, '"'));
    const total = scenes.reduce((sum, scene) => sum + Number(scene.dur || 0), 0);
    return total > 0 ? total : null;
  } catch {
    return null;
  }
}

// ========================================
// Render
// ========================================

async function render() {
  const source = path.join(SRC_DIR, SRC_FILE);
  if (!fs.existsSync(source)) {
    console.error(`Design not found: ${source}`);
    process.exit(1);
  }

  const seconds = SECONDS_OVERRIDE ? Number(SECONDS_OVERRIDE) : durationOf(source) ?? 98;
  const frames = Math.round(seconds * FPS);

  console.log(`${path.basename(OUT_PATH)}  ${WIDTH}x${HEIGHT}  ${seconds}s  ${frames} frames @ ${FPS}fps`);
  emit("start", {
    out: path.basename(OUT_PATH),
    width: WIDTH,
    height: HEIGHT,
    seconds,
    frames,
    fps: FPS,
  });

  // Started before the browser so the page has somewhere to load from, and
  // torn down in the same finally block that closes it.
  let designServer = null;
  let servedUrl = null;
  if (SERVE_ROOT && !PAGE_URL) {
    const { server, port } = await serveDesignTree(path.resolve(SERVE_ROOT));
    designServer = server;
    const relative = path.relative(path.resolve(SERVE_ROOT), source).split(path.sep);
    servedUrl = `http://127.0.0.1:${port}/${relative.map(encodeURIComponent).join("/")}`;
    console.log(`  serving ${SERVE_ROOT} on 127.0.0.1:${port}`);
  }

  const browser = await puppeteer.launch({
    headless: true,
    args: [
      "--allow-file-access-from-files", // without this the page cannot see its assets folder
      "--hide-scrollbars",
      "--force-device-scale-factor=1", // otherwise everything scales on a HiDPI screen
      "--disable-dev-shm-usage",
      "--no-sandbox", // the VPS runs this as an unprivileged service user
    ],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: WIDTH, height: HEIGHT });
    await page.evaluateOnNewDocument(installVirtualClock);

    // http when a root is being served, because that is the only way a
    // .dc.html can fetch the .jsx scenes it is built from. file:// otherwise,
    // which is enough for a self-contained .html.
    const target = PAGE_URL || servedUrl || pathToFileURL(source).href;
    await page.goto(target, { waitUntil: "domcontentloaded", timeout: 60000 });

    // Real time, before the clock is taken over, so the page can unpack itself.
    await new Promise((resolve) => setTimeout(resolve, 3000));
    await page.evaluate(() => {
      for (let index = 0; index < 10; index++) window.__vt.step(1000 / 60);
    });

    const hidden = KEEP_CHROME ? await page.evaluate(hideLoadingOnly) : await page.evaluate(hideChrome);
    if (!hidden) {
      console.log("  !! could not find the player bar - check the first frame before using this file");
    }

    await page.evaluate(installSiteStyle, SITE_SCALE, SITE_GAP);
    let siteMarked = await page.evaluate(markSiteText, SITE_SCALE);

    // ffmpeg reads the JPEG frames straight off stdin. No temporary files, and
    // far quicker than writing several thousand images to disk and reading
    // them back again.
    fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
    const encoder = spawn(
      "ffmpeg",
      [
        "-y",
        "-f", "image2pipe",
        "-framerate", String(FPS),
        "-i", "pipe:0",
        "-c:v", "libx264",
        "-crf", String(CRF),
        "-preset", "slow",
        "-pix_fmt", "yuv420p", // required by Facebook and Instagram
        "-movflags", "+faststart", // playback can start before the file finishes arriving
        "-an",
        OUT_PATH,
      ],
      { stdio: ["pipe", "ignore", "pipe"] },
    );

    let encoderError = "";
    encoder.stderr.on("data", (chunk) => {
      encoderError += chunk;
      if (encoderError.length > 4000) encoderError = encoderError.slice(-2000);
    });
    const encoded = new Promise((resolve, reject) => {
      encoder.on("close", (code) =>
        code === 0 ? resolve() : reject(new Error(`ffmpeg exited with code ${code}\n${encoderError}`)),
      );
    });

    const session = await page.createCDPSession();
    const step = 1000 / FPS;
    const startedAt = Date.now();

    for (let index = 0; index < frames; index++) {
      await page.evaluate((ms) => window.__vt.step(ms), step);
      const { data } = await session.send("Page.captureScreenshot", { format: "jpeg", quality: 100 });

      // One second in, past the fade-up, is a far better thumbnail than frame zero.
      if (POSTER_PATH && index === FPS) {
        fs.mkdirSync(path.dirname(POSTER_PATH), { recursive: true });
        fs.writeFileSync(POSTER_PATH, Buffer.from(data, "base64"));
      }

      if (!encoder.stdin.write(Buffer.from(data, "base64"))) {
        await new Promise((resolve) => encoder.stdin.once("drain", resolve));
      }

      // The closing scene arrives late, so this keeps looking once a second.
      if (!siteMarked && index % FPS === 0) {
        siteMarked = await page.evaluate(markSiteText, SITE_SCALE);
      }

      if (index > 0 && index % FPS === 0) {
        const etaSec = ((Date.now() - startedAt) / index) * (frames - index) / 1000;
        emit("progress", {
          frame: index,
          frames,
          pct: Number(((index / frames) * 100).toFixed(1)),
          etaSec: Math.round(etaSec),
        });
        if (!JSON_LOG && index % (FPS * 10) === 0) {
          console.log(`  ${((index / frames) * 100).toFixed(0)}%  ~${(etaSec / 60).toFixed(1)} min left`);
        }
      }
    }

    encoder.stdin.end();
    await encoded;
    await page.close();

    if (!siteMarked) console.log("  !! never found www.acm.is - the closing scene is unchanged");

    const megabytes = (fs.statSync(OUT_PATH).size / 1048576).toFixed(1);
    const minutes = ((Date.now() - startedAt) / 1000 / 60).toFixed(1);
    console.log(`  finished: ${megabytes} MB in ${minutes} min`);
    emit("done", { out: path.basename(OUT_PATH), path: OUT_PATH, mb: Number(megabytes) });
  } finally {
    await browser.close();
    designServer?.close();
  }
}

requireFfmpeg();
await render();
