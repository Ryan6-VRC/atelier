# MochiFitter — cross-base outfit refit

MochiFitter (もちふぃった～, BOOTH, by Nine Gates / おもちのびる) warps a garment authored for one base body onto a different one whose topology no scale or bone op bridges. It is a purchased vendor tool and is not redistributable: treat it and each conversion profile as detected dependencies, and fail loud naming what is absent rather than degrading. The **`mochifit`** skill owns the refit process end to end — install, route, drive, own, verify; this doc holds the tool facts it runs on.

**Reach for it only when a transform cannot.** `reproportion` handles topo-preserving base changes through equivalency edges and routes the genuinely non-topo case here — that boundary is declared there. A refit takes minutes and bakes geometry; an equivalency edge does neither.

## What a run needs

Per target base, a **conversion profile**: `avatar_data_<base>.json`, `config_<src>2<dst>.json`, `posediff_*.json`, `pose_basis_*.json`, and the `deformation_*.npz` fields. The tool installs at its native `Assets/OutfitRetargetingSystem/` and discovers available conversions by scanning its own `Editor/` folder, so a relocated tool or a profile installed anywhere else is invisible to it. Most profiles are free or bundled with the avatar they dress.

**Blender is a dependency too, and the tool installs its own per Unity project.** The retarget script runs on a Blender that MochiFitter downloads from Blender's own release server into `<ProjectRoot>/BlenderTools/`, outside `Assets/` — it does not ride in the `.unitypackage`, and no Blender already on the machine satisfies it (`docs/blender.md`'s pipeline build is a different version and is never consulted). Detection is a bare existence check on that path, so **a fresh venue re-incurs the download however many refits the machine has already run** — a few hundred MB over the network, not a click. Until it lands, `Execute Retargeting` renders disabled (measured, ver.64: moving the folder aside flips the check false and the button with it). The window says so itself, in a `Blender Status:` row with a `Download & Install` button beside it; that row also names the version required, which tracks the vendor's release cadence — read it off the tool, never from this file.

**Profiles are directional, and most ship one way only.** `template2<X>` dresses X; `<X>2template` undresses it. Confirm the direction you need exists before promising a conversion. Routing is hub-and-spoke through a neutral `template`, so any base pair is two hops and the tool composes them itself.

**Derive the conversion graph from each config's contents, never from its filename** — `baseAvatarDataPath` is the destination, `clothingAvatarDataPath` the source. Shipped filenames contain typos.

## Traps

**The two avatar fields are not source-and-target in the obvious sense.** Target Avatar is the body being dressed. Source Avatar is the *route*, shown as `X → Y (Template経由)`. Setting the target alone leaves the route pointing somewhere unrelated, and the config field then reflects that wrong route — a run configured this way succeeds and produces the wrong conversion.

**The OMOCHI checkbox is an input-format switch, not a backend swap.** Both checkbox states drive the same tool-managed Blender with the same retarget script; the option only changes the solver's input to a transient `.omochi` (written under the project's `Temp/`, never `Assets/`) and drops the hips-position argument. Either way the output is a plain FBX plus reconstructed prefab with **zero dependencies on the vendor's assets** (measured via `AssetDatabase.GetDependencies`, ver.64) — both survive uninstalling the tool. One measured comparison (Beryl→Nouvelle, ver.64): geometrically equivalent (0.066 mm max baked-mesh deviation, identical bone offsets and blendshape lists), ~5 % faster with the option on. The vendor still marks it experimental; the default is fine and nothing rides on the choice. Manually importing a `.omochi` through the vendor importer is a different, unwelded path (a measured ~3× vertex inflation) — the run itself never takes it.

**A run mutates the vendor folder.** Every fire rewrites `_temp.json` copies of configs and avatar data beside the shipped originals, with paths rewritten to chain the hops — their presence after a run is normal residue, not damage. The trap is a **failed** run's leftovers: the next run consumes them, and nothing distinguishes them from healthy residue — so **delete every `_temp.json` before firing**; they are disposable and regenerated per fire, never an input worth keeping.

**Completion pops a blocking native Win32 modal that stalls the Editor's tool queue** — title `Success`, a single `OK` button (measured, ver.64). Detect completion by watching the output folder for the finalized prefab; the Editor is unreachable until the dialog is dismissed. Two verified dismissal routes: `tools/unity-dialog.ps1` from outside the process (exact title + button per its doctrine), or pre-arm the vendor's own static result-dialog suppression flag on the window type — find it by reflection like every other member; its name is an internal and stays out of tracked files.

**`renderer.bounds` cannot verify placement.** The tool deliberately unifies every renderer to one global bounding box. Bake the skinned mesh and measure real vertex positions against the target body's bones.

## What a refit costs

Output is a **baked** garment plus a reconstructed prefab. Topology, UV layers and materials survive; the original blendshapes survive **except those consumed as the selected shape fields** — each selected source shape drops and the target's variant keys arrive in its place (measured); the armature is replaced with the target's. Selecting those is an input to the solve — a wrong selection is a silent fidelity loss, not an error.

**Bones the target base lacks are dropped.** A source rig carrying individual toe or breast bones, refitted onto a base without them, loses that weighting; the remaining weights renormalize, so nothing collapses and nothing warns. This is a property of the base pair rather than a fixable defect — surface it, don't chase it.

The vendor's own readme warns that animations and complex gimmicks on the outfit frequently need rework afterward. Treat a refit as producing garment geometry, not preserved outfit behavior.

## Verifying one

Rest pose proves nothing here: a refit whose weight transfer failed still renders correctly and disintegrates the moment it is posed. Gate on humanoid-bone world-position coincidence before any render, then sweep poses per `docs/verify.md`. `CheckSeam.CheckBare` is that gate (`unity-tools.md`) — the raw output does carry a `MergeArmature`, but it has no base to resolve against yet, so `CheckSeam.Check` lands on the `mergeTarget` abstain and the bare door is what scores two side-by-side skeletons (measured, on three outputs of two separate runs). Pass it the solver-noise tolerance the `mochifit` skill owns; measured residue on those runs was `maxWithinEps` 0.0011mm, so the skill's 0.01mm gate sits an order of magnitude clear. `Check` scores later, placed on the real base at compose.
