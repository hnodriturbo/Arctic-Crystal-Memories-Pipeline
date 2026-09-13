<!--
File: blender_addons/acm_scene_composer/README.md
Purpose:
 - Define the first executable ACM Scene Composer boundary and local workflow.
-->

# ACM Scene Composer

Blender 5.1 extension for composing two deliberately different input types:

1. **ACM 2.5D Relief** — a completed textured relief produced after MoGe depth,
   face refinement and depth fusion.
2. **Meshy Full 3D** — a complete Meshy model that remains full 3D.

The extension never silently converts one mode into the other. In particular,
Meshy geometry is not cut or compressed into a relief.

## Current capabilities

- Import GLB, GLTF, OBJ, STL or FBX and tag the source type and path.
- Distinguish monochrome crystal-tone, RGB and geometry-only relief inputs.
- Adopt objects that are already open in Blender.
- Preserve source mesh data under a non-destructive asset root.
- Store the expected human-face count and FaceBuilder completion state.
- Block final export when faces exist but FaceBuilder QA is incomplete.
- Apply root-only position, rotation and uniform height scaling.
- Apply shared shallow/balanced/deep/custom relief-depth profiles against the
  selected crystal depth and per-side safety margin.
- Add editable text and a simple bevelled rectangular frame.
- Validate mesh/material counts and world dimensions.
- Export one textured GLB with ACM provenance in glTF extras.

## Face-refinement boundary

Automatic face-depth refinement belongs before this extension. The native 2.5D
order is:

```text
RGB -> MoGe depth/normals -> face refinement and fusion
    -> bounded micro-depth + crystal-tone texture
    -> RGB/crystal GLB -> ACM Scene Composer
```

FaceBuilder remains a mandatory human review step for every human face. The
Composer records that state and prevents an unfinished asset from being
mistaken for a final export.

## Install locally

Build the extension from this directory with Blender 5.1:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" `
  --command extension build
```

Then use **Edit -> Preferences -> Get Extensions -> Install from Disk** and
select the generated ZIP. The panel appears in the 3D View sidebar under
**ACM Composer**.
