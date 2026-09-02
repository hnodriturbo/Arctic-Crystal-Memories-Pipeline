<!--
File: code-snapshot/README.md
Purpose:
 - Identify the exact local code snapshot used for the frozen ICON front d-BiNI run.
-->

# Read-only code snapshot

Þessi mappa varðveitir nákvæmar kóðaskrár sem voru notaðar fyrir valda
`front-surface-adaptive-fillet` niðurstöðu. Afritin eru merkt read-only í Windows.

## Innihald

- `pipeline/`: run, integration og Blender QA scripts ásamt föstum dependency-lista.
- `upstream/ICON/apps/infer.py`: official ICON inference með opt-in raw front-data export.
- `upstream/ECON/lib/common/BNI.py`: d-BiNI configuration fyrir continuous surface og fillet.
- `upstream/ECON/lib/common/BNI_utils.py`: opt-in stretched-face policy og adaptive depth fillet.
- `patches/`: læsileg breytingaryfirlit fyrir upstream ICON og ECON.

Fullu upstream skrárnar í `upstream/` eru canonical exact snapshot. Patch-skrárnar eru
skýringaryfirlit og á ekki að nota einar sér sem sönnun fyrir fullri endurgerð runsins.

Ekki breyta þessum afritum þegar pipeline þróast áfram. Ný tilraun á að fá nýja
run-möppu og nýtt snapshot.
