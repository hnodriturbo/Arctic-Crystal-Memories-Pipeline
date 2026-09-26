/*
 * ═══════════════════════════════════════════════════════════════
 * Check Workshop Endpoints
 * ═══════════════════════════════════════════════════════════════
 * Path: scripts/check-workshop-endpoints.mjs
 * Purpose: Sign in as the agent account and touch every read endpoint, so a
 *          pipeline broken by an unrelated change names itself.
 *
 *   node --env-file=<shared>/.env.production scripts/check-workshop-endpoints.mjs
 *   VERIFY_BASE=http://127.0.0.1:3100 node --env-file=.env.local scripts/check-workshop-endpoints.mjs
 *
 * Written while the workshop was moved onto its own hostname, because that
 * kind of change breaks things quietly: the pipeline nobody opened that week
 * is exactly the one that stays broken.
 */
const BASE = process.env.VERIFY_BASE || "http://127.0.0.1:3003";
const jar = new Map();
const cookieHeader = () => [...jar].map(([k, v]) => `${k}=${v}`).join("; ");

function absorb(r) {
  for (const line of r.headers.getSetCookie?.() || []) {
    const [p] = line.split(";");
    const i = p.indexOf("=");
    if (i > 0) jar.set(p.slice(0, i).trim(), p.slice(i + 1).trim());
  }
}

async function call(path, options = {}) {
  const r = await fetch(BASE + path, {
    ...options,
    redirect: "manual",
    headers: { ...(options.headers || {}), cookie: cookieHeader() },
  });
  absorb(r);
  return r;
}

const { csrfToken } = await (await call("/api/auth/csrf")).json();
await call("/api/auth/callback/credentials", {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({
    csrfToken,
    email: process.env.AGENT_EMAIL,
    password: process.env.AGENT_PASSWORD,
    callbackUrl: BASE + "/",
  }).toString(),
});
const session = await (await call("/api/auth/session")).json();
console.log("signed in as:", session?.user?.email || "FAILED", "\n");

// Every read-only endpoint, grouped by the pipeline that owns it. A POST-only
// route is probed with GET purely to prove it is routed, so 405 is a pass.
const CHECKS = [
  ["page", "/", [200]],
  ["page", "/?view=claude-animations", [200]],
  ["page", "/?view=cockpit-reconstruct", [200]],
  ["page", "/?view=convert-export", [200]],
  ["page", "/login", [200, 307, 302]],

  ["image pipeline", "/api/image/state", [200]],
  ["meshy", "/api/meshy/state", [200]],
  ["meshy", "/api/meshy/balance", [200, 502, 503]],
  ["converter", "/api/files", [200]],
  ["converter", "/api/environments", [200]],
  ["cockpit", "/api/reconstruct/scenes", [200]],
  ["r2 browser", "/api/r2/browser?prefix=Cockpit3D-Files/", [200]],
  ["r2 browser", "/api/r2/library", [200]],

  ["claude design", "/api/claude-design/library", [200]],
  ["claude design", "/api/claude-design/sync", [200]],
  ["claude design", "/api/claude-design/zips", [200]],
  ["claude design", "/api/claude-design/render", [200]],

  ["webhook", "/webhooks/meshy", [400, 401, 405]],
];

let failures = 0;
let group = "";
for (const [owner, path, expected] of CHECKS) {
  if (owner !== group) {
    console.log(`-- ${owner}`);
    group = owner;
  }
  let status;
  let note = "";
  try {
    const response = await call(path);
    status = response.status;
    // A page that redirects to /login means the session was not accepted,
    // which is a different failure from the page itself being broken.
    const location = response.headers.get("location");
    if (location && location.includes("/login")) note = " -> redirected to login";
  } catch (error) {
    status = "ERR";
    note = ` ${error.message}`;
  }
  const ok = expected.includes(status) && !note.includes("login");
  if (!ok) failures++;
  console.log(`   ${ok ? "ok  " : "FAIL"} ${String(status).padEnd(4)} ${path}${note}`);
}

console.log(failures ? `\nPIPELINES_FAILED count=${failures}` : "\nALL_PIPELINES_OK");
process.exitCode = failures ? 1 : 0;
