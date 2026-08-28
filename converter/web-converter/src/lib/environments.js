/*
 * ═══════════════════════════════════════════════════════════════
 * Environment Probe
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/environments.js
 * Purpose: Ask each Python environment what it actually is, rather than
 *          assuming.
 *
 * The machines this runs on differ in ways that change what the UI should
 * offer: the workstation has CUDA and can do Real-ESRGAN and GFPGAN, the VPS
 * has neither and falls back to lanczos and pillow. Guessing from the
 * hostname would be wrong the first time either box changed, so this asks the
 * interpreter directly and reports what it says.
 */

import { execFile } from "node:child_process";
import { readdir, stat } from "node:fs/promises";
import { homedir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";

import {
  CODE_DIR,
  CONVERTER_ROOT,
  IMAGE_CODE_DIR,
  IMAGE_PYTHON_EXE,
  IMAGE_ROOT,
  MESHY_PYTHON_EXE,
  MESHY_ROOT,
  PYTHON_EXE,
} from "@/lib/paths";
import { interpreterReady } from "@/lib/python";

const run = promisify(execFile);

/*
 * One script, run inside each venv, reporting JSON on stdout.
 *
 * Written as a single string rather than a file on disk because it has to run
 * in an interpreter this app does not own - dropping a probe script into
 * someone else's package folder would be rude and would need cleaning up.
 */
const PROBE = `
import json, sys, platform

def version(name):
    try:
        module = __import__(name)
    except Exception:
        return None
    return getattr(module, "__version__", "installed")

report = {
    "python": platform.python_version(),
    "platform": platform.system(),
    "packages": {},
    "cuda": None,
}

for name in ("numpy", "scipy", "PIL", "ezdxf", "rembg", "onnxruntime", "torch", "cv2", "requests"):
    report["packages"][name] = version(name)

try:
    import torch
    report["cuda"] = {
        "available": torch.cuda.is_available(),
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
except Exception:
    pass

json.dump(report, sys.stdout)
`;

/** Run the probe in one interpreter. Never throws - a dead venv is a result. */
async function probe(executable) {
  if (!interpreterReady(executable)) {
    return { ok: false, error: `No interpreter at ${executable}` };
  }
  try {
    const { stdout } = await run(executable, ["-c", PROBE], { timeout: 30000 });
    return { ok: true, ...JSON.parse(stdout) };
  } catch (error) {
    return { ok: false, error: error.message.slice(0, 200) };
  }
}

/** How many files sit in a folder, and how much they weigh. */
async function folderStats(directory) {
  try {
    const entries = await readdir(directory, { withFileTypes: true });
    let files = 0;
    let bytes = 0;
    for (const entry of entries) {
      if (!entry.isFile() || entry.name.startsWith(".")) continue;
      files += 1;
      bytes += (await stat(path.join(directory, entry.name))).size;
    }
    return { exists: true, files, bytes };
  } catch {
    return { exists: false, files: 0, bytes: 0 };
  }
}

/** rembg caches its models here, and they are large enough to be worth showing. */
async function cachedModels() {
  const directory = process.env.U2NET_HOME || path.join(homedir(), ".u2net");
  try {
    const entries = await readdir(/* turbopackIgnore: true */ directory);
    const models = [];
    for (const name of entries) {
      if (!name.endsWith(".onnx")) continue;
      const info = await stat(path.join(directory, name));
      models.push({ name: name.replace(/\.onnx$/, ""), bytes: info.size });
    }
    return { directory, models: models.sort((a, b) => b.bytes - a.bytes) };
  } catch {
    return { directory, models: [] };
  }
}

/** Everything the environments page shows, gathered in parallel. */
export async function readEnvironments() {
  const [imagePython, meshyPython, converterPython, models, imageIn, imageOut, meshyIn, meshyOut] =
    await Promise.all([
      probe(IMAGE_PYTHON_EXE),
      probe(MESHY_PYTHON_EXE),
      probe(PYTHON_EXE),
      cachedModels(),
      folderStats(path.join(IMAGE_ROOT, "input")),
      folderStats(path.join(IMAGE_ROOT, "output")),
      folderStats(path.join(MESHY_ROOT, "input")),
      folderStats(path.join(MESHY_ROOT, "output")),
    ]);

  return {
    environments: [
      {
        id: "image",
        emoji: "🖼️",
        name: "Image pipeline",
        purpose: "Restores, upscales and cuts out photographs before Meshy sees them.",
        root: IMAGE_ROOT,
        code: IMAGE_CODE_DIR,
        interpreter: IMAGE_PYTHON_EXE,
        probe: imagePython,
        folders: [
          { emoji: "📥", label: "input", ...imageIn },
          { emoji: "📤", label: "output", ...imageOut },
        ],
        // What each engine choice actually resolves to on this machine.
        capabilities: [
          {
            emoji: "✂️",
            label: "Background removal",
            ready: Boolean(imagePython.packages?.rembg),
            detail: imagePython.packages?.rembg
              ? `rembg ${imagePython.packages.rembg} on onnxruntime — full quality, no GPU needed`
              : "rembg is not installed",
          },
          {
            emoji: "🔍",
            label: "AI upscale",
            ready: Boolean(imagePython.cuda?.available),
            detail: imagePython.cuda?.available
              ? `Real-ESRGAN on ${imagePython.cuda.device}`
              : "No CUDA — 'auto' resolves to lanczos, which resamples but invents no detail",
          },
          {
            emoji: "✨",
            label: "Face restoration",
            ready: Boolean(imagePython.cuda?.available),
            detail: imagePython.cuda?.available
              ? "GFPGAN on the GPU"
              : "No CUDA — 'auto' resolves to pillow tone and sharpness adjustment",
          },
        ],
      },
      {
        id: "meshy",
        emoji: "🧊",
        name: "Meshy pipeline",
        purpose: "Stores Meshy jobs and provides isolated diagnostics for the remote API workflow.",
        root: MESHY_ROOT,
        code: path.join(MESHY_ROOT, "code"),
        interpreter: MESHY_PYTHON_EXE,
        probe: meshyPython,
        folders: [
          { emoji: "📥", label: "input", ...meshyIn },
          { emoji: "📦", label: "jobs", ...meshyOut },
        ],
        capabilities: [
          {
            emoji: "🌐",
            label: "API diagnostics",
            ready: Boolean(meshyPython.packages?.requests),
            detail: meshyPython.packages?.requests
              ? `requests ${meshyPython.packages.requests}; generation itself remains in the Node runner`
              : "requests is required for the isolated Meshy diagnostics environment",
          },
          {
            emoji: "🧱",
            label: "Pipeline isolation",
            ready: Boolean(meshyPython.ok),
            detail: "No Torch, CUDA, image models or SciPy are required in this environment.",
          },
        ],
      },
      {
        id: "converter",
        emoji: "💠",
        name: "Point-cloud converter",
        purpose: "Samples a mesh into the dot cloud the SSLE engraver reads.",
        root: CONVERTER_ROOT,
        code: CODE_DIR,
        interpreter: PYTHON_EXE,
        probe: converterPython,
        folders: [
          { emoji: "📥", label: "meshy input", ...meshyIn },
          { emoji: "📦", label: "meshy jobs", ...meshyOut },
        ],
        capabilities: [
          {
            emoji: "📐",
            label: "Mesh sampling",
            ready: Boolean(converterPython.packages?.numpy && converterPython.packages?.scipy),
            detail: converterPython.packages?.numpy
              ? `numpy ${converterPython.packages.numpy}, scipy ${converterPython.packages.scipy}`
              : "numpy and scipy are required",
          },
          {
            emoji: "📄",
            label: "DXF reading",
            ready: Boolean(converterPython.packages?.ezdxf),
            detail: converterPython.packages?.ezdxf
              ? `ezdxf ${converterPython.packages.ezdxf}`
              : "ezdxf is not installed — POINT-only files still parse natively",
          },
        ],
      },
    ],
    models,
  };
}
