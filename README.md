<!--
Purpose: Entry point for the active ACM operator website and its local pipelines.
-->

# ACM Pipeline workspace

## 2.5D pipeline — personal research, never part of the web (owner rule 28-09-2026)

`CCM-Web-Workshop/Crystal-Workshop/2.5D-pipeline` is the owner's personal pipeline and is still under construction.
It is not, and will not become, part of the web design or of any website: ccm.is, Crystal Studio and
workshop.ccm.is never include it. It only lives inside the Workshop repository so the owner can keep researching it.

- Keep its source complete on GitHub (`hnodriturbo/Arctic-Crystal-Memories-Pipeline`, branch `master`). Model weights,
  virtual environments, outputs and personal photos stay local and ignored.
- Never import, deploy, link or expose it in a web application. Crystal Studio's `scripts/import-workshop.mjs` and the
  Workshop VPS release both exclude it; keep it that way.
- Its local environments, research branches and data are the owner's research, not a website problem: do not repair,
  delete or reorganise them unless the owner asks.

The active website and pipeline modules live together in [converter](converter/README.md).
The requested name is **Main-Pipelines-Web**; the directory rename is pending
because Windows currently locks the folder through running Blender MCP environments.

- `converter/CCM-Web-Pipeline/` — operator website, including Cockpit Reconstruct.
- `converter/pipeline-converter/` — model conversion and relief reconstruction.
- `converter/image-pipeline/` and `converter/meshy-pipeline/` — existing production stages.
- `converter/2.5D-pipeline/` — preserved research and reference gallery.
- `converter/docs/` and `converter/Learning/` — supporting documentation and courses.
- `deployment/` and `scripts/` — release tooling supporting the operator website.

The obsolete top-level `pipeline/` and `pipeline-old/` folders were removed on
2026-09-13. Their original input collections were preserved in the ignored
`converter/2.5D-pipeline/reference-gallery/legacy-inputs/` folder. Their tracked
source remains available in Git history before the Cockpit Reconstruct work (merged into `master` on 28-09-2026).
The previous repository guide is in `converter/docs/legacy-repository-readme.md`.

Work locally. Do not commit, push or deploy without the owner's instruction.
Keep development servers stopped between checks.
