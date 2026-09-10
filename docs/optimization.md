# Performance rank and optimization

Primary reader: an agent asked to move a composed avatar's VRChat performance rank, or to hold a rank line while composing. PC only; Android's thresholds live in the same SDK assets but its shader and format constraints are not worked here. `nondestructive.md` owns how the optimizers ride the build; this doc owns what each ranked stat counts, which lever moves it, and what a lever costs.

## The rule: options, not edits

**A rank task ends in a costed option table put to the operator; the edit follows the pick.** Each option names the levers, the stat delta measured on a fresh bake, the slack left under the line, and what changes in how the avatar moves or looks. Levers with no visible or felt cost may be taken without asking — and those are few, because the mature optimizers already take the mechanical zero-change cases automatically. An agent that believes it found a new free lever that d4rk, AAO and VRCFury all missed carries the burden of strong evidence; the default reading is that the lever has a cost not yet seen. Every option must leave every other stat unregressed and every sibling avatar sharing the touched prefab unmoved, so a lever lives as a variant override, never in a shared mergeable prefab, unless the operator says otherwise.

## Measuring

The only number that counts is the SDK's own, read off a fresh preprocess bake — never a pre-bake read (MA, VRCFury and the optimizers all reshape what is counted) and never a subtree count. No owned door emits the vector; the recipe over `execute_code` is `AvatarBake.Begin` (`com.ryan6vrc.agent-tools`, internal — reach it by reflection) on a scene instance, `VRCConstraintManager.Sdk_ManuallyRefreshGroups` over the clone's `VRCConstraintBase` set (without it `constraintsCount` reads low), then `AvatarPerformance.CalculatePerformanceStats(name, clone, stats, mobilePlatform: false)` and `stats.CalculateAllPerformanceRatings(false)`. Read inside the scope, since disposal guts the clone (`AvatarBake`'s own doc). A bake of a large row outruns the MCP response timeout: write the result to a file under `test-output/` inside the snippet and read the file. Bake-mode `ReportComposition` measures triangles the same way (`tris` is `polyCount`; `trisActive` is not a ranked number).

## The line

Canon: `Packages/com.vrchat.base/Runtime/VRCSDK/Dependencies/VRChat/Resources/Validation/Performance/StatsLevels/Windows/{Excellent,Good,Medium,Poor}_Windows.asset`. Above Poor is Very Poor. Echoed here because a budget is planned against the distance to the next rung.

| stat | Excellent | Good | Medium | Poor | moved by |
|---|---|---|---|---|---|
| polyCount | 32000 | 70000 | 70000 | 70000 | §Polygons |
| skinnedMeshCount | 1 | 2 | 8 | 16 | §Renderers and materials |
| meshCount | 4 | 8 | 16 | 24 | §Renderers and materials |
| materialCount | 4 | 8 | 16 | 32 | §Renderers and materials |
| boneCount | 75 | 150 | 256 | 400 | §Bones |
| physBone.componentCount | 4 | 8 | 16 | 32 | §PhysBones |
| physBone.transformCount | 16 | 64 | 128 | 256 | §PhysBones |
| physBone.colliderCount | 4 | 8 | 16 | 32 | §PhysBones |
| physBone.collisionCheckCount | 32 | 128 | 256 | 512 | §PhysBones |
| textureMegabytes | 40 | 75 | 110 | 150 | §Texture memory |
| contactCount | 8 | 16 | 24 | 32 | removal, or §One component, many roles |
| constraintsCount / constraintDepth | 100 / 20 | 250 / 50 | 300 / 80 | 350 / 100 | removal, or §One component, many roles |
| animatorCount | 1 | 4 | 16 | 32 | merge into the FX layer (MA `Merge Animator`, VRCFury `FullController`); the count falls only when the child `Animator` is deleted (MA's `deleteAttachedAnimator`) |
| lightCount | 0 | 0 | 0 | 1 | removal, or §One component, many roles |
| audioSourceCount | 1 | 4 | 8 | 8 | removal, or §One component, many roles |
| particleSystemCount / particleTotalCount / particleMaxMeshPolyCount | 0 / 0 / 0 | 4 / 300 / 1000 | 8 / 1000 / 2000 | 16 / 2500 / 5000 | removal, or §One component, many roles |
| particleTrailsEnabled / particleCollisionEnabled | off | off | on | on | removal |
| trailRendererCount / lineRendererCount | 1 / 1 | 2 / 2 | 4 / 4 | 8 / 8 | removal, or §One component, many roles |
| clothCount / clothMaxVertices | 0 / 0 | 1 / 50 | 1 / 100 | 1 / 200 | removal |
| physicsColliderCount / physicsRigidbodyCount | 0 / 0 | 1 / 1 | 8 / 8 | 8 / 8 | removal |
| raycastCount | 1 | 4 | 8 | 15 | removal |
| aabb extent | 1.25 | 2 | 2.5 / 3 / 2.5 | 2.5 / 3 / 2.5 | renderer bounds (VRCFury `BoundingBoxFix`, MA `Mesh Settings`) |

**Every count is taken over the built avatar with inactive objects included.** An inactive renderer, an inactive physbone, a garment behind a toggle — all count at full weight. The only thing that removes an always-inactive object from the count is an unused-object sweep deleting it at build: d4rk's `DeleteUnusedComponents` (on in the house profile; `DeleteUnusedGameObjects` is a separate default-off pass over unreferenced objects and not what this rides on), or AAO `TraceAndOptimize`'s `removeUnusedObjects` where one is placed. A saving taken by deactivation is conditional on whichever sweep the avatar actually carries. Where a toggle only selects between two states the avatar could ship as separate uploads, ship two configurations: the absent piece leaves the build entirely.

## Polygons

Counted per renderer under the root, inactive included, after every build-time delete. Levers, cheapest in look first:

- **Hidden body under an unconditional garment set.** `mark_coverage` (`blender.md`) measures the covered body polygons and writes the Delete carrier shape; the costume's unconditioned MA `Shape Changer` Delete row removes them at build (`outfits.md` §The garment that covers a region owns the hide). Only an unconditioned Delete buys triangles: a row any toggle can reach NaNimates instead — it hides, at the cost of extra bones and an FX layer, but the vertices stay in the mesh and in `polyCount`. Prove the drop by the built-renderer triangle diff, never by a built blendshape name (`ReportComposition` bake mode; the optimizers rename and bake shapes with the triangles intact).
- **A vendor's own delete shapes** (`*_OFF`, the vendor's delete mark) applied the same way, before authoring any new cut.
- **An always-inactive renderer** leaves through the unused-object sweep, at the conditionality above; a renderer's departure keeps its bones and physbone, so a removed accessory still costs transforms until its chain goes too.
- **Decimation.** Unowned. Blender refuses to *apply* any geometry-changing modifier to a mesh carrying shape keys (Decimate evaluates, the apply fails), so the process is a keyless copy decimated then shapes transferred back, and every downstream index-addressed override (blendshape weights on prefabs, `RemoveMeshByBlendShape`, the coverage carrier) is invalid afterward. A polygon delete is nearly always the cheaper cut.

## PhysBones

Four stats, one counting rule. **Per component the SDK counts the chain's bone list — root plus every descendant, minus each `ignoreTransforms` entry with its whole subtree, minus other physbones' roots when `ignoreOtherPhysBones` is on — and sums over every component, inactive included.** `endpointPosition` adds nothing and removes nothing. The scanner ships precompiled (`VRC.SDK3.Dynamics.PhysBone.dll`), so this is measured, not read: per-component `bones.Count` after `InitTransforms(force: true)` on a baked clone sums to the SDK's `transformCount` exactly. Subtree size is not a budget locator; a chain with an ignore entry counts far less than its subtree.

**The component-versus-transform split is the trap.** AAO `MergePhysBone` reduces `componentCount` and *raises* `transformCount` by one per merge: it roots one component on a merge root — the component's own object under `makeParent`, the shared parent where every one of its children is a source, otherwise a new `PhysBoneRoot-…` — and either way that root joins the chain, so the merged chain is the union plus one. It is the lever for `componentCount` and for nothing else. Its validator rejects sources whose properties differ, and the rejection aborts the whole build behind a "Preprocess Callback Failed" modal that wedges an MCP-driven editor, with the differing property named only in NDMF's error report; the per-property `Override`/`Merge` configs that let it proceed change behaviour (a mirrored `limitRotation` overridden to one side, two collider lists merged into both chains).

Transform levers, graded by what they do to the chain. **Nothing that changes a live chain's bone list is free**: a shorter list moves `maxBoneChainIndex`, the denominator every per-bone curve is normalised over, so every non-flat pull, spring, stiffness, gravity, radius or angle curve on the chain is remapped. A rest-pose or topology read cannot show that cost; only a play-mode comparison of the chain's motion can (`emulator.md`), and until one is made the lever is priced as felt.

- **Destroy a physbone component whose chain nothing visibly moves** (a chain under a removed renderer, a duplicate rig). Free. Destroy, don't deactivate: the SDK counts the inactive component, and a deactivated one sheds only through an unused-object sweep (§The line). On a variant the destroyed component is a real prefab override; a deactivated object is a saving that depends on the sweep staying.
- **Trim a collider list** on a chain that never reaches those colliders: moves `collisionCheckCount` only, free.
- **`ignoreTransforms` at a depth.** Removes the entry and its subtree; a chain of *n* branches at *d* joints yields in steps of *n*, so the trims are discrete and each is measured, never interpolated — a trim that looks like it clears the line can land one over. Felt: the chain is shorter.
- **Retire an unweighted leaf into `endpointPosition`.** The same shortening as ignoring it, plus an unproven claim that the endpoint reproduces the leaf's pull on its parent — the leaf is the target its weighted parent rotates toward, not inert. AAO's Trace and Optimize automates this only where every leaf's local position matches within 1e-5 and no leaf is otherwise animated or grabbed, and it checks no curve, so its result carries the same unpriced remap; where the leaves differ it declines, and averaging them by hand is a different, unsanctioned edit. Never call either visually free.
- **AAO `MergeBone` inside the chain** (merge every second bone). Merges the bone upward into its own parent: destroys the transform, reparents its children world-preserving, remaps skin weights and ignore lists (`MergeBoneProcessor.MapIgnoreTransforms`). One transform per bone; felt, since the chain is shorter; and a merged bone with children changes which bone carries their motion. Outside every chain it moves `boneCount` only. The type is internal — add by reflection, and set `avoidNameConflict` deliberately, since true renames every reparented child.
- **Remove the chain.** Structural; the geometry stays and stops moving.

`colliderCount` is the collider components; `collisionCheckCount` is per collider, the transforms it can affect, so it falls with either factor but only on a chain that references colliders — a trim elsewhere moves it not at all (measured). AAO's Trace and Optimize merges coincident colliders (`MergePhysBoneCollider`: unanimated, same shape and world placement after rounding, same toggle root — moves `colliderCount`, costs no transform) and compatible chains (`AutoMergeCompatiblePhysBone`, via the same `MergePhysBone` mechanism and its one-transform cost per group: same normalised values, no parameter, no grab, one physbone per target, plus a longer refusal list — multi-child Ignore, unanimated, same toggle root, no constraint on the chain, under 100 transforms — so read the pass before predicting it will fire).

## Bones

`boneCount` is the SDK's count of the rig's bones over the built skinned renderers; the scanner is compiled and whether a bone two renderers share counts once is unmeasured — do not plan a bone budget on the assumption that it does. Levers: `prune_bones` (`blender.md`) for zero-weight chains at the source, MA `Merge Armature` for a mergeable's duplicate skeleton (the seam already does this), AAO `MergeBone` outside physbone chains for bones no weight needs. A bone a physbone rides is not free to merge even at zero weight if it has a child: the child reparents and the chain shortens (§PhysBones).

## Renderers and materials

`skinnedMeshCount`, `meshCount` and `materialCount` are the built renderers and their slots after merging. **d4rk merges automatically and declines often; AAO merges exactly what you tell it.** d4rk groups renderers only when, clip by clip, every relevant animated binding on one exists on the other with the same curve keys (blendshape bindings never count; enable and active bindings drop out under NaNimation) — so a renderer the colour clips bind and a bare one never share a group, and the bare one lands wherever path order puts it — and, while `MergeSkinnedMeshesWithNaNimation` is on, only when their default-enabled states match (with NaNimation off that check is skipped whatever `MergeSkinnedMeshesSeparatedByDefaultEnabledState` says). A swap-animated slot (`m_Materials.Array.data[n]` in any clip, or a *conditional* MA `Material Setter`; a constant one is a scene mutation d4rk never sees) keeps that slot's material out of any material merge, while the renderer itself still merges. It merges *materials* into one slot only when their shader source parses (a locked Poiyomi material cannot be read; `own-material` owns the lifecycle) and the properties are compatible; the settings that let it merge across differing properties and textures rewrite shaders and are off in the house profile (§Division of labour). The merge preview foldout shows the resulting groups, not the reasons: renderer-merge refusals are named only in d4rk's build log file under "Skinned mesh merge errors:", and material-merge refusals only in the Material Merge Analyzer window, whose button appears only with `MergeDifferentPropertyMaterials` on. Read the log before reaching for AAO.

Where d4rk declines, AAO `MergeSkinnedMesh` on its own empty container merges the listed renderers before d4rk runs (it discards the target's own mesh, so it cannot sit on a renderer you keep), and AAO `MergeMaterial` atlas-packs listed materials into one, rewriting the UVs into the atlas rect (it wraps out-of-range UVs, so tiling breaks). A merge is load-bearing for colour where the merged renderers must share an animated slot, so a merge is never dropped on rank grounds alone.

Atlasing beyond those two is unowned: it rewrites UVs, so every mask, matcap and texture-driven FX on the material re-authors with it.

## Texture memory

`textureMegabytes` is the compressed size of every texture the built materials reference. Limitex's `TextureCompressor` owns it — complexity-aware resize and recompress per texture, by threshold and never by budget: you cannot aim it at a megabyte figure, only pick a preset and measure. `Preset` alone cascades nothing; `ApplyPreset` writes the fields. AAO `MaxTextureSize` caps resolution by mip-strip (no re-encode) on the subtree of its nearest-ancestor claim; a texture shared across two caps takes the loosest, and a crunched or mip-poor texture is skipped with a warning and ships uncapped. Import settings are inputs to those passes, not what ships.

## One component, many roles

A counted component that no two configurations need live at once can serve every one of them: one light, audio source, particle system, constraint or contact reparented, retargeted or moved by animation to whichever role the current state wants — two glowing sources lit by one light read as two to anyone watching. Count stats only; a physbone is bound to its bones and cannot be shared. The cost is on the animator and parameter side (`menus.md`, `gimmicks.md`), and the boundary is exact: the moment two roles must be live in the same state the lever is gone.

## Division of labour

- **d4rk** is the automatic sweep on the avatar root: mesh and slot merging, the unused-object pass, blendshape baking. It takes the zero-change cases and names what it refuses in its build log. `OptimizeFXLayer` stays off unconditionally — its layer merging can change animator and toggle behaviour. The profile a fresh component gets is the observed lean, not a mandate: off `OptimizeFXLayer`, `WritePropertiesAsStaticValues`, `MergeSameDimensionTextures`, `MergeMainTex`, `MergeDifferentPropertyMaterials`, `MergeSkinnedMeshesWithShaderToggle` (an int, set 0), `CombineApproximateMotionTimeAnimations`, `NaNimationAllow3BoneSkinning`; on `ApplyOnUpload`, `MergeSkinnedMeshes`, `MergeSkinnedMeshesSeparatedByDefaultEnabledState`, `DisablePhysBonesWhenUnused`, `MergeSameRatioBlendShapes`, `DeleteUnusedComponents`; `DeleteUnusedGameObjects`, `UseRingFingerAsFootCollider`, `MergeStaticMeshesAsSkinned` and `MMDCompatibility` are left at their component defaults for the operator to tune — don't write them. Fields sit on the nested `settings` object.
- **AAO** is the surgical set, one component per intent: `MergeSkinnedMesh`, `MergeMaterial`, `MergePhysBone`, `MergeBone`, `RemoveMeshByBlendShape` / `ByMask` / `InBox` / `ByUVTile`, `FreezeBlendShape`, `MaxTextureSize`. Its `TraceAndOptimize` is the whole-avatar automatic pass, not placed by lean; where a lever needs one of its passes (end-bone retirement, identical-chain merge) place it and measure rather than reproduce the pass by hand.
- **Limitex** owns texture memory. **VRCFury**'s `BlendshapeOptimizer` and `DirectTreeOptimizer` are safe to add when absent. **MA** is not an optimizer, but its seam (`Merge Armature`) and reactive deletes are where a mergeable's bone and polygon costs are decided.

Adding a component to an avatar that already carries one of the same kind is never a rank move: the operator placed and configured it, and the `upload-avatar` skill's pre-step adds only what is absent.
