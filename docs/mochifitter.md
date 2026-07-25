# MochiFitter — cross-base outfit refit

MochiFitter (もちふぃった～, BOOTH, by Nine Gates / おもちのびる) warps a garment authored for one base body onto a different one whose topology no scale or bone op bridges. It is a purchased vendor tool and is not redistributable: treat it and each conversion profile as detected dependencies, and fail loud naming what is absent rather than degrading.

**Reach for it only when a transform cannot.** `reproportion` handles topo-preserving base changes through equivalency edges and routes the genuinely non-topo case here — that boundary is declared there. A refit takes minutes and bakes geometry; an equivalency edge does neither.

## What a run needs

Per target base, a **conversion profile**: `avatar_data_<base>.json`, `config_<src>2<dst>.json`, `posediff_*.json`, `pose_basis_*.json`, and the `deformation_*.npz` fields. The tool discovers available conversions by scanning its own `Editor/` folder, so a profile installed anywhere else is invisible to it. Most profiles are free or bundled with the avatar they dress.

**Profiles are directional, and most ship one way only.** `template2<X>` dresses X; `<X>2template` undresses it. Confirm the direction you need exists before promising a conversion. Routing is hub-and-spoke through a neutral `template`, so any base pair is two hops and the tool composes them itself.

**Derive the conversion graph from each config's contents, never from its filename** — `baseAvatarDataPath` is the destination, `clothingAvatarDataPath` the source. Shipped filenames contain typos.

## Traps

**The two avatar fields are not source-and-target in the obvious sense.** Target Avatar is the body being dressed. Source Avatar is the *route*, shown as `X → Y (Template経由)`. Setting the target alone leaves the route pointing somewhere unrelated, and the config field then reflects that wrong route — a run configured this way succeeds and produces the wrong conversion.

**Two backends sit behind one checkbox.** The default drives a bundled Blender and yields a portable FBX; the OMOCHI-format option drives a native solver and yields an asset that only resolves while the vendor's importer is installed. The second is marked experimental by the vendor. Prefer the default: its output survives uninstalling the tool, and no relative-cost claim between the two has been measured.

**A run mutates the vendor folder.** It writes `_temp.json` copies of configs and avatar data beside the shipped originals, with paths rewritten to chain the hops. A failed run leaves them for the next one to consume, so check that folder is clean before starting rather than diagnosing after.

**Completion pops a blocking modal that stalls the Editor's tool queue.** Detect completion by watching the output folder for the finalized prefab; the Editor is unreachable until the dialog is dismissed.

**`renderer.bounds` cannot verify placement.** The tool deliberately unifies every renderer to one global bounding box. Bake the skinned mesh and measure real vertex positions against the target body's bones.

## What a refit costs

Output is a **baked** garment plus a reconstructed prefab. Topology, UV layers, materials and the original blendshapes survive; the armature is replaced with the target's, and shape-variant keys are added for the variants selected. Selecting those is an input to the solve — a wrong selection is a silent fidelity loss, not an error.

**Bones the target base lacks are dropped.** A source rig carrying individual toe or breast bones, refitted onto a base without them, loses that weighting; the remaining weights renormalize, so nothing collapses and nothing warns. This is a property of the base pair rather than a fixable defect — surface it, don't chase it.

The vendor's own readme warns that animations and complex gimmicks on the outfit frequently need rework afterward. Treat a refit as producing garment geometry, not preserved outfit behavior.

## Verifying one

Rest pose proves nothing here: a refit whose weight transfer failed still renders correctly and disintegrates the moment it is posed. Gate on humanoid-bone world-position coincidence (`CheckSeam`) before any render, then sweep poses per `docs/verify.md`.
