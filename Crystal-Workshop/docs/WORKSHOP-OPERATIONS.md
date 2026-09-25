<!-- Purpose: Current operator and agent handoff for Crystal Workshop and the R2 showroom library. -->
# Crystal Workshop operations

The primary public hostname is **https://workshop.ccm.is**. Nginx proxies the
authenticated Next.js interface to port 3003. The older pipeline hostname still
serves compatibility traffic. Workshop owns its own HTTPS certificate and is
the canonical Auth.js origin. Crystal Vision is a separate customer image area
in ACM-Web-Main; do not reuse that name here.

## Files and storage

- Local application: `CCM-Web-Workshop/Crystal-Workshop/ACM-Web-Pipeline`.
- Reconstruction engine: `Crystal-Workshop/pipeline-converter/code/cockpit_reconstruct.py`.
- Cockpit Reconstruct is a separate navigation chapter. Its engine still shares
  the converter Python environment; it has not been moved to an independent engine folder.
- Company source collection: workspace-root `Cockpit3D-Files/[number]-[name]/`.
- Private Pipeline bucket: `acm-pipeline-eu`, with the same `Cockpit3D-Files/` prefix.
- Finished GLBs: `Cockpit3D-Files/[number]-[name]/<unique>.glb`.
- New saved models use `[number]-[name]-v001.glb`; uploads through the Blender
  button use `[number]-[name]-edited-v002.glb`. Both read the highest existing
  version in the selected folder before allocating the next name. Conditional
  R2 writes prevent overwriting a concurrent save. Existing model keys are not
  renamed, because published showroom records may refer to them. Temporary job
  IDs remain internal. Use the scene browser upload rather than generic presign
  for Blender GLBs so this naming rule is always applied.
- Windows task `ACM-Bookkeeping-Expense-R2-Sync` runs once daily at **15:00**.
  `CCM-Web-Workshop/scripts/run-daily-r2-sync.ps1` runs the separate Expenses and
  Cockpit backups even when one fails. Never propagate local deletions to R2.

The old `converter` path must not be recreated. Archived cache backups were
preserved during renaming and are not runtime inputs.

## Create a showroom model on the website

Versioned Reconstruct outputs now reserve a number in R2
`Cockpit3D-Files/<scene>/.versions/vNNN.json` before conversion. Downloads and
R2 saves therefore use exactly `<scene>-vNNN.glb` and `<scene>-vNNN.jpg` (or
the actual original PNG/JPEG extension). Blender uploads use
`<scene>-edited-vNNN.glb` in the same sequence. Aborted/download-only jobs can
leave number gaps; never recycle reservations. Repeated Save accepts identical
SHA-256 content and rejects replacement content. The report and GLB extras
record the exact original photograph name/hash/member. Existing hash-named
originals and legacy published keys remain valid and are not renamed.

Original photographs: Windows scene backup first runs `extract_scene_original.py`
for numbered folders. It extracts only the single textured SolidEntity's named
member, byte-for-byte, to `original-<16 SHA256 characters>.jpg` (or the original
PNG/JPEG extension). Existing originals remain unchanged. Cockpit Reconstruct
also extracts that original into its temporary result folder; Save to R2 uploads
the verified photograph alongside the GLB in the selected source scene folder.
Existing showroom mappings are independent; uploading a photo alone does not
automatically publish it or change a previously curated exhibit.

1. Save the correct Cockpit scene, then export its corresponding portrait DXF.
   Keep scene and export together in a numbered folder. Remove unrelated text
   in Cockpit before export; a front text layer is not part of the photo surface.
2. Back up the folder to R2. The Windows daily task does this, or run
   `node --env-file=.env.local scripts/sync-scene-files.mjs` from ACM-Web-Pipeline.
3. Open Cockpit Reconstruct on Workshop. Refresh the R2 folder browser and
   explicitly select the matching DXF/CAD and saved `.cockpit` file.
4. Reconstruct using the approved preset: every source point, no point limit,
   no deduplication, smooth surface, resolution 768, smoothing 2.25, gap 7.5,
   front percentile 85, vertex budget 500000, XY texture projection.
5. Review the result, then use **Vista á R2 Cloudflare**. A unique object key
   preserves previous attempts. This saves an available model, not a public exhibit.
6. On `https://www.acm.is/is/showroom`, open the normal Admin panel and refresh
   the Workshop R2 library. Prepare a private preview, enter bilingual titles
   and crystal dimensions, and explicitly choose whether customers may see it.

GLB estimates are for display, not final SSLE manufacturing files. Every DXF
point informs the surface, but grid reconstruction does not create one mesh
vertex for each laser point. Preserve the production DXF and original scene.

## Geometry and pairing rules

Read the exact texture member named by the single textured SolidEntity in the
freshly saved Cockpit XML. Read its Euler X/Y/Z and position, undo the pose for
photo projection and restore it on the reconstructed geometry. DXF scale is
already baked into exported coordinates; do not apply that scale twice.
Never match photographs by a similar filename or combine different DXF exports.

`pipeline-converter/code/showroom-preset.json` is the approved default source.
Boundary relaxation is capped at 0.2 mm; the embedded photo uses an unlit GLB
material. Preserve the approved Group Photo asset.

Layer Specs width/height/depth describe the **portrait**, not the crystal.
Jón Þór uses crystal 80 × 100 × 60 mm; Pabbi og barn uses 70 × 100 × 50 mm.
Both use 5 mm bevel and linked 5 mm margin. The 2026-09-13 VPS-created exports
were reviewed as private previews and then published under the owner's request
to add these two models. Admin retains publication/hide controls for each entry.

## Environment and deployment

VPS root stays `/home/hreidar/apps/ccm-workshop` to preserve service identity.
`current/Crystal-Workshop/ACM-Web-Pipeline` links its environment to
`shared/.env.production`. Shared Python environments and job workspaces survive
immutable releases. Keep `AUTH_URL=https://workshop.ccm.is` and private R2 keys
server-only. Main has its own copy of `R2_PIPELINE_*` beside other bucket settings
in local, production-template and VPS `.env` files.

Use the existing reviewed-local deployment scripts and their rollback checks.
Do not commit or push without a new explicit instruction. Keep local preview
servers stopped; temporary verification servers must be stopped after checking.
Run the Python reconstruction tests and Next.js build before activation.

The Blender GLB upload button uses the same-origin `/api/reconstruct/upload`
endpoint (up to 64 MB), validates the GLB and saves it to R2. Temporary streamed
bytes are removed after success or failure. This needs no bucket CORS changes.
Server-side reconstruction saves also work without CORS. Do not widen CORS
rules without the owner's permission; preserve existing origins and rules.

For the showroom UI, public/private model registry, mobile interaction and the
optional intro draft, read `ACM-Web-Main/docs/Guides/CRYSTAL_SHOWROOM.md`.

## R2-first operator workflow — September 13 update

1. Save the Cockpit scene and matching DXF in the same numbered company folder.
2. Run **ACM - Update R2** on the Windows desktop. It starts the existing combined
   Expenses/Cockpit task, without changing its daily 15:00 schedule. Refresh Scene
   library after upload completes. The VPS does not remotely control Windows.
3. In Cockpit Reconstruct, select the scene first, then its export. Load the pair.
   Imported files use input/tmp/<UUID>; the scene texture and pose are re-read.
4. Keep the approved full-point preset. The expanded full-width **2.5D Model Preview**
   shows the result. Choose Download GLB, Save to R2, or Send to converter.
5. Edit geometry/UVs in Blender if needed. In the converter R2 browser, open the
   original numbered scene folder and upload the edited GLB (up to 64 MB through
   the same-origin endpoint). Select Use in converter; no manual VPS paths needed.
6. Inspect physical millimetre dimensions, select the correct crystal template,
   set density/spacing and export POINT DXF. Existing model formats and converter
   defaults remain supported; format-specific capabilities still apply.
7. Import the DXF into Cockpit and save a scene there when a native .cockpit file
   is required. Sampling a mesh does not recover the original laser point positions.

New GLBs are written alongside their source scene, using unique names. Legacy
Cockpit3D-Files/cockpit-reconstruct keys remain readable by the showroom; existing
exhibits are not moved or replaced. Saving a GLB does not publish a customer exhibit.
After Save to R2, Download GLB uses a short-lived direct Cloudflare download.

**R2 File Browser** lists scenes, earlier source versions, Meshy jobs, converter
jobs, uploads and archive. The same component supplies converter input selection.
Credentials remain server-side. Downloads do not require bucket CORS changes.
The scene library is for explicit source pairing; the general browser handles files.

New imported inputs, reconstruction outputs and model-converter outputs are
isolated in marked tmp directories. Only marked UUID directories older than seven
 days are removed, opportunistically when creating another workspace of that type.
Unmarked and historical folders are preserved. Save unsaved results to R2 before
expiry. Old legacy converter tools retain their existing output behavior.

Pose overrides are **absolute export-pose replacements**, not added transforms.
Enter Cockpit rotation X/Y/Z in degrees and position X/Y/Z in mm. The inverse pose
is used for projection and the pose is restored afterward; the DXF's baked scale
is not multiplied again. The Center option removes final translation; turn it off
when scene position must remain. Overrides require smooth/texture/XY mode. Every
advanced input links to its explanation at the page bottom.

Navigation uses pushState/popstate; Back/Forward restore the selected workspace.
The running reconstruction remains mounted across workspace changes. Reloading
still starts a fresh form: a view URL is not a permanent link to an unsaved job.
The desktop sidebar can collapse; mobile keeps its slide-out navigation.

Verification: npm build (webpack), test-r2-workflow.mjs, test-showroom-upload.mjs,
Python test_cockpit_reconstruct.py, test_scene_pose_override.py and
 test_convert_model.py. Use normal signed-in browser sessions for integration QA;
never manufacture authentication sessions for tests.

## Owner-approved point-cloud baseline

Point spacing: **0.08 mm**. Layer spacing: **0.09 mm**. These are the main
point-cloud settings specified by the owner on 2026-09-13. Keep both in the UI
and Python defaults; do not conflate point spacing with layer spacing.
Photo-driven density remains separate and experimental.
