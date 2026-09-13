<!--
Purpose: Entry point for the active ACM operator website and its local pipelines.
-->

# ACM Pipeline workspace

The active website and pipeline modules live together in [converter](converter/README.md).
The requested name is **Main-Pipelines-Web**; the directory rename is pending
because Windows currently locks the folder through running Blender MCP environments.

- `converter/ACM-Web-Pipeline/` — operator website, including Cockpit Reconstruct.
- `converter/pipeline-converter/` — model conversion and relief reconstruction.
- `converter/image-pipeline/` and `converter/meshy-pipeline/` — existing production stages.
- `converter/2.5D-pipeline/` — preserved research and reference gallery.
- `converter/docs/` and `converter/Learning/` — supporting documentation and courses.
- `deployment/` and `scripts/` — release tooling supporting the operator website.

The obsolete top-level `pipeline/` and `pipeline-old/` folders were removed on
2026-09-13. Their original input collections were preserved in the ignored
`converter/2.5D-pipeline/reference-gallery/legacy-inputs/` folder. Their tracked
source remains available in local Git history before branch `feature/cockpit-reconstruct`.
The previous repository guide is in `converter/docs/legacy-repository-readme.md`.

Work locally. Do not commit, push or deploy without the owner's instruction.
Keep development servers stopped between checks.
