# K9 Crystal Pipeline — Instructions

> **This file is now a summary pointer.**
> Full project documentation, folder structure, component reference, pipeline stages,
> and development rules are in [`code-agents.md`](code-agents.md).
> A full backup of the original instructions is in `INSTRUCTIONS_backup.md`.

---

## Quick Reference

| Topic                                              | Where to look                                                                     |
| -------------------------------------------------- | --------------------------------------------------------------------------------- |
| Full project overview, folder structure, all rules | [`code-agents.md`](code-agents.md)                                                |
| Web app (Next.js) specific rules                   | [`web/INSTRUCTIONS.md`](web/INSTRUCTIONS.md) and [`web/AGENTS.md`](web/AGENTS.md) |
| Pipeline usage guide                               | [`pipeline/pipeline-guide.md`](pipeline/pipeline-guide.md)                        |
| Pipeline setup                                     | [`pipeline/pipeline-setup.md`](pipeline/pipeline-setup.md)                        |
| Pipeline-converter usage                           | [`pipeline-converter/INSTRUCTIONS.md`](pipeline-converter/INSTRUCTIONS.md)        |
| Business plan context                              | Original backup in `INSTRUCTIONS_backup.md` sections 11–16                        |

---

## One-Line Summary

Local image-preparation pipeline (upscale / enhance / remove background) with a Next.js operator UI.
Cockpit3D handles 3D conversion. `pipeline-converter/` reads Cockpit3D exports — not yet wired into the web UI.
