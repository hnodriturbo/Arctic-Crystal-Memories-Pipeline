<!--
File: code-snapshot/README.md
Purpose:
 - Identify the exact read-only source snapshot used by the PARE A/B run.
-->

# Read-only PARE run snapshot

- `pipeline/`: launch, raw integration, QA og dependency-listi.
- `upstream/ICON/apps/infer.py`: exact source með front-data export og legacy chumpy shim.
- `upstream/ECON/lib/common/`: exact d-BiNI/fillet source.
- `patches/`: læsileg upstream change summaries.

Fullu upstream afritin eru canonical fyrir endurgerð runsins. Patch-skrárnar eru
skýringaryfirlit. Allar kóðaskrár hér eru Windows read-only og á ekki að þróa
beint áfram inni í frozen run-möppunni.
