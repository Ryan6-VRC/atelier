Every agent-facing callable across `vrc-unity-tools` / `vrc-blender-tools` / `vrc-skills`, one row
each. Rows are routing, not contracts; behavior lives in `docs/unity.md` / `docs/blender.md` and the
skills themselves. The pre-commit hook `tools/sync_tool_inventory.py` verifies each key against its
code declaration site (Unity `[AgentTool]` classes, Blender operator names ∪ `cli/` stems, skill
frontmatter names) and mirrors this file into `README.md`; it never writes a row itself. The agent
landing a tool change updates its row by hand at merge (the hook skips worktrees).

## vrc-unity-tools

### vrc-unity-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `AgentInspector` | JSON snapshot of a scene object (by hierarchy path or selection) or the whole scene; a generic walk over any component. |
| `RenderAvatar` | Isolated Scene-View render of one avatar subtree, NDMF-preview-resolved (proxy-aware, so MA-reactive bodies render), framed from named world-axis angles to a contact-sheet PNG; operator-eye evidence for fit and clipping after a compose. Grab in a separate call from any edit; an unsettled preview fails the grab loud after kicking the editor to foreground — just re-grab. |
| `CheckPackage` | Post-import health check: missing (vs. intentionally empty) material/mesh/script refs, plus stale FBX material remaps. |
| `ReportPackage` | Vendor-package report: FBX/mesh inventory, the superset FBX, FX toggles, MA/VRCFury/NDMF presence. |
| `CheckHumanoidRig` | Gate: does the humanoid bind still match the model geometry, or must `MatchHumanoidRig` re-run? |
| `ReportController` | Markdown digest of an `AnimatorController`: parameters, layers with Write Defaults, states, transitions, blend trees, motions by path + GUID (dangling refs flagged empty-vs-broken at any depth, including inside blend trees), VRC behaviours decoded typed. |
| `ReportClip` | Binding digest of a clip, or of every `.anim` under a folder: one row per curve (`path \| type \| propertyName \| keys`). |
| `CheckAnimator` | PASS/FAIL plus tiered offenders for mechanically-detectable controller rot; the binding-resolution root is auto-detected from a merge site or asserted explicitly. |
| `CheckAvatar` | On a placed in-scene avatar root, names the MA scene refs and clip/controller bindings a base rename silently broke; PASS/CLASSIFY, inspection-only. Each clip-binding break carries its `clipAssetPath` so the caller can route between repathing inline and owning the asset. |
| `CheckSeam` | On a base + placed mergeable, reflects the MA/VRCFury seam mapping and gates world-position coincidence of weighted humanoid bones: ≤1 → REFUSE (offset-tolerant proxy like hair/earring), ≥2 → PASS within ε (max 0.5mm or 0.2%·Hips→Head) else NOT-PASS with worst-first offenders; non-humanoid bones ride ungated, VRCFury scale/unresolvable-seam → REFUSE. Certifies the humanoid skeleton coincides, not accessory placement; inspection-only, the mechanical fit gate to run before any render. |
| `ReportGimmick` | Topology digest of a gimmick subtree: contact/physbone/constraint tables, a constraint edge-list spanning both VRC and Unity constraint families (driven/sources, weights, axes), VRCFury authoring inventory, and the mechanically-certain idioms (world anchor, feedback loop, indirection, hold, editor/runtime swap). Complete by construction — a tier-2 census names every component no table interpreted, so `other=0` means empty. |

### vrc-unity-tools · transplant kit (vendor → owned)

| Key | Purpose |
| --- | --- |
| `CopyComponents` | Type-driven component copy between hierarchies (a deep VRC tier plus a conservative tier). |
| `MoveComponents` | Move components onto a new holder hierarchy with anchors pinned back; behavior-neutral. |
| `GraftHierarchy` | Copy a named subtree wholesale: structure plus all components, refs remapped. |
| `CopyDescriptor` | Transplant the VRC avatar descriptor, with a fresh PipelineManager. |
| `FixViewpoint` | Recompute `ViewPosition` from a reference rig's viewpoint plus both rigs' Head/eyes. |
| `MatchHumanoidRig` | Conform our humanoid rig to the vendor's bone mapping; `Preflight` previews. |
| `ConformRenderers` | Copy materials by renderer name from a source hierarchy and normalize bounds/anchor. |
| `OwnMaterial` | Own a vendor material: deep-copy it (or branch/augment an already-owned one), fork the named texture slots into the copy's own subfolder, and unlock a locked-Poiyomi copy — every unforked slot stays on its vendor GUID. The skill chooses which slots; the tool's `slots[]` provenance table is the caller's gate. |

### vrc-unity-tools · controllers & clips

| Key | Purpose |
| --- | --- |
| `CleanController` | Reset an owned avatar's FX to a blank slate: keep named layers (plus base layer 0), empty params/menu, wire the descriptor. Blank-slate only; for anything richer, decompile, edit, and recompile instead. |
| `RepathClips` | Segment-safe repath of a controller's owned clip bindings; the caller supplies the moves. |
| `OwnControllerClips` | Fork vendor-linked clips to owned copies and retarget the controller's motion slots. |
| `CompileController` | The animator **write substrate**: compiles a declarative YAML document into a persisted `.controller`, plus inline clips, embedded blend trees, and a `VRCExpressionParameters` asset. Atomic, idempotent (stable GUID), `whatIf`-previewable; every build passes the shared graph lint. Schema: [`docs/animator-schema.md`](docs/animator-schema.md). |
| `DecompileController` | The animator **read substrate**, inverse of `CompileController`: walks a built `.controller` back to animator-schema YAML, never mutating it; refuses out-of-vocabulary constructs by name. `Decompile → edit → Compile` is the lossless round-trip. Schema: [`docs/animator-schema.md`](docs/animator-schema.md). |
| `CompileClips` | The **external-clip write door**: compiles a clips-file YAML (top-level `clips:`, no `layers:`) into standalone, *visible* `.anim` assets — one per clip, GUID-stable in place — that a controller then references by `ref:` path. Sole *authoring* writer of external clips (emits clip content from a clips-file YAML — distinct from `OwnControllerClips`, which copies existing clips); emit-only (never prunes, so deleting a clip from the file *promotes* it to human ownership), batch-atomic, and refuses to clobber a hand-edited clip (`force` overrides that and a read-only outDir). Schema: [`docs/animator-schema.md`](docs/animator-schema.md). |
| `NormalizeExpressionClips` | Make expression clips share one binding/key-time set; optionally prune unused curves. |

### vrc-unity-tools · scene utilities

| Key | Purpose |
| --- | --- |
| `RemapMaterials` | Swap materials by asset path across a hierarchy. |
| `ConstrainedDuplicate` | Clone a hierarchy and wire VRC constraints between original and duplicate bones. |

## vrc-blender-tools

### vrc-blender-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `report_stamps` | Read a `.blend`'s avatarprep provenance: per-armature base/state (plus kind) and each bound mesh's `avatarprep_baked` map. The query counterpart of `stamp_base`. |
| `compare_armatures` | Seam check: do two rigs share bone names, parents, positions, base, and state? The merge dry-run. |
| `render_mesh` | Headless contact-sheet render of the scene's render-visible meshes from named world-axis angles, solid or vertex-color shading; `RenderAvatar`'s Blender sibling. |

### vrc-blender-tools · armature & mesh ops

| Key | Purpose |
| --- | --- |
| `apply_pose` | Bake the current pose into the rest pose, shape-key-safe. |
| `merge_armatures` | Union-merge two armatures by bone name behind the compat gate; gates on base and state (`force_stamps` overrides the stamp gate, `whatif` previews). |
| `prune_bones` | Prune zero-weight bone chains, keeping physbone tips and attachment bones. |
| `bake_shapekey` | Normal-preserving shape-key→Basis bake (refuses the head mesh); records `avatarprep_baked`. |
| `stamp_base` | Stamp `avatarprep_base` (avatar lineage) on an armature; a deliberate agent assertion. |

### vrc-blender-tools · proportions & export

| Key | Purpose |
| --- | --- |
| `apply_proportion_edge` | Apply one declarative proportion edge, validating first and stamping state; `--whatif` validates read-only against the live scene. |
| `import_fbx` | Import an FBX via Blender's current importer (never the legacy one, which reorients bones); stamps new armatures state="unproportioned" and returns a sanity snapshot. `export_unity_fbx`'s counterpart. |
| `export_unity_fbx` | Export with the Unity/VRChat FBX recipe; `--armature` scopes an owned re-export to one rig (selection-only, no texture embed). |

## vrc-skills

| Key | Purpose |
| --- | --- |
| `import-vendor-asset` | Bring a vendor avatar, outfit, hair, or accessory into the Unity project. |
| `own-base` | Build our owned, uploadable copy of a vendor base body. |
| `own-mergeable` | Build our owned copy of a mergeable's geometry (outfit, hair, accessory): extract, reproportion, seam, so it composes like a vendor one. |
| `own-material` | Build our owned, editable copy of a vendor material or texture — recolor, repaint, emission mask, shader convert; materialize the owned copy before any write under `Vendor/`. |
| `compose-mergeable` | Place a seam-authored outfit, hair, or accessory onto an avatar base: verify the seam, de-conflict meshes, check shape coherence. |
| `map-outfit-shapes` | Map how a body's blendshapes couple to its clothing meshes across FX/MA/VRCFury idioms, then act on it: de-conflict overlapping clothing, release coupled shapes, feed toggle closures and morph-coherence reads. |
| `author-menu` | Author expression-menu controls, params, and wiring on a composed avatar (MA-first); place or front a gimmick's menu. |
| `reproportion` | Reshape proportions and reconcile the Unity side. |
| `showcase-record` | Film a work session (ffmpeg screen capture) and cut it into a short showcase video. |
| `fitting-session` | Wear-test the workshop itself: dispatch worker agents on real vendor-asset tasks, grade independently, distill the sharp edges into a cross-run ledger + fixup kickoffs. |
