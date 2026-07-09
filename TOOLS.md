# The system tool index

Every agent-facing callable across `vrc-unity-tools` / `vrc-blender-tools` / `vrc-skills`, one row each.
Rows are hand-authored; `tools/sync_tool_inventory.py` (the meta-repo pre-commit hook) verifies the keys
against the code declaration sites — Unity `[AgentTool]` classes, Blender operator names ∪ `cli/` stems,
skill frontmatter names — and mirrors this file into `README.md`, but never writes a row itself. The
agent landing a tool change adds/updates its row by hand (the hook skips worktrees, so this happens at
merge). Rows are routing, not contracts — behavior lives in `docs/unity.md` / `docs/blender.md` and the
skills themselves.

## vrc-unity-tools

### vrc-unity-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `AgentInspector` | JSON snapshot of a scene object (by hierarchy path or selection) or the whole scene — generic walk, any component. |
| `RenderAvatar` | Isolated Scene-View render of one avatar subtree (NDMF preview-resolved), silhouette-framed from named world-axis angles, headlight-lit, to an OS-temp contact-sheet PNG — the visual backstop for compose de-conflict/fit. Grab in a separate call from any edit — a same-call grab is the pre-edit proxy. |
| `CheckPackage` | Post-import health check: MISSING (vs. intentionally empty) material/mesh/script refs + stale FBX remaps. |
| `ReportPackage` | Vendor-package report: FBX/mesh inventory, superset FBX, FX toggles, MA/VRCFury/NDMF presence. |
| `CheckHumanoidRig` | Gate: does the humanoid bind still match the model geometry, or must `MatchHumanoidRig` re-run? |
| `ReportController` | Markdown digest of an `AnimatorController` — params/layers+WD/states/transitions/blend-trees, motions by path+GUID, typed VRC behaviour decode. |
| `ReportClip` | Markdown binding digest of a clip (or every `.anim` under a folder) — one row per curve (`path \| type \| propertyName \| keys`). |
| `CheckAnimator` | PASS/FAIL + tiered offenders for mechanically-detectable controller rot (root basis auto-detected from a merge site, or asserted). |
| `CheckAvatar` | PASS/CLASSIFY: on a placed in-scene avatar root, names the MA-scene-ref + clip/controller-binding refs a base rename silently broke (clip-binding carries `clipAssetPath` for the abort-and-own vs. inline route). Inspection-only. |
| `ReportGimmick` | Markdown topology digest of a gimmick subtree — contacts/physbones/constraints tables + constraint edge-list (TargetTransform indirection, weights, axes), VRCFury authoring inventory, and mechanically-certain idioms (world anchor, feedback loop, indirection, hold, editor/runtime swap). |

### vrc-unity-tools · transplant kit (vendor → owned)

| Key | Purpose |
| --- | --- |
| `CopyComponents` | Type-driven component copy between hierarchies (deep VRC tier + conservative tier). |
| `MoveComponents` | Move components onto a new holder hierarchy, anchors pinned back (behavior-neutral). |
| `GraftHierarchy` | Copy a named subtree wholesale — structure + all components, refs remapped. |
| `CopyDescriptor` | Transplant the VRC avatar descriptor (+ fresh PipelineManager). |
| `FixViewpoint` | Recompute `ViewPosition` from a reference rig's viewpoint + both rigs' Head/eyes. |
| `MatchHumanoidRig` | Conform our humanoid rig to the vendor's bone mapping (`Preflight` previews). |
| `ConformRenderers` | Copy materials by renderer name from a source hierarchy + normalize bounds/anchor. |

### vrc-unity-tools · controllers & clips

| Key | Purpose |
| --- | --- |
| `CleanController` | Trim a controller to named layers, prune its params to kept-layer references, wire clean FX/params/menu. |
| `RepathClips` | Segment-safe repath of a controller's owned clip bindings (caller supplies the moves). |
| `OwnControllerClips` | Fork vendor-linked clips to owned copies + retarget the controller's motion slots. |
| `CompileController` | The animator **write substrate**: compile a declarative YAML document into a persisted `.controller` (+ inline clips, embedded blend trees, `VRCExpressionParameters`). parse→validate→emit→`ControllerRules` lint→atomic persist; idempotent (stable GUID), `whatIf`-previewable. Schema: [`docs/animator-schema.md`](docs/animator-schema.md). |
| `DecompileController` | The animator **read substrate**, inverse of `CompileController`: reachability-walk a built `.controller` back to animator-schema YAML. A READ tool (self-logs to Snapshot, never mutates); named refusals for out-of-vocabulary constructs; `whatIf`. `Decompile→edit→Compile` is the lossless round-trip oracle. Schema: [`docs/animator-schema.md`](docs/animator-schema.md). |
| `NormalizeExpressionClips` | Make expression clips share one binding/key-time set; optionally prune unused curves. |

### vrc-unity-tools · scene utilities

| Key | Purpose |
| --- | --- |
| `RemapMaterials` | Swap materials by asset path across a hierarchy. |
| `ConstrainedDuplicate` | Clone a hierarchy + wire VRC constraints between original/duplicate bones. |

## vrc-blender-tools

### vrc-blender-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `report_stamps` | Read a `.blend`'s avatarprep provenance — per-armature base/state (+ kind) and a per-armature grouping of each bound mesh's `avatarprep_baked` map (+ an `unbound` bucket). The query counterpart of `stamp_base`. |
| `compare_armatures` | Seam check: do two rigs share bone names/parents/positions, base, and state? (The merge dry-run.) |
| `render_mesh` | Headless contact-sheet render of the scene's render-visible meshes from named world-axis angles — solid or vertexcolor shading — to an OS-temp PNG. `RenderAvatar`'s Blender sibling. |

### vrc-blender-tools · armature & mesh ops

| Key | Purpose |
| --- | --- |
| `apply_pose` | Bake current pose into the rest pose (shape-key-safe). |
| `merge_armatures` | Union-merge two armatures by bone name behind the compat gate; gates on base + state (`force_stamps` overrides the stamp gate, `whatif` previews). |
| `prune_bones` | Prune zero-weight bone chains (keeps physbone tips + attachment bones). |
| `bake_shapekey` | Normal-preserving shape-key→Basis bake (refuses the head mesh); records `avatarprep_baked`. |
| `stamp_base` | Stamp `avatarprep_base` (avatar lineage) on an armature — a deliberate agent assertion. |

### vrc-blender-tools · proportions & export

| Key | Purpose |
| --- | --- |
| `apply_proportion_edge` | Apply one declarative proportion edge (validates first; stamps state). `--whatif` validates read-only against the live scene without mutating. |
| `import_fbx` | Import an FBX into the scene via Blender's current importer (never the legacy one — it reorients bones); stamps new armatures state="unproportioned"; returns a sanity snapshot. `export_unity_fbx`'s counterpart. |
| `export_unity_fbx` | Export with the Unity/VRChat FBX recipe (`--armature` scopes an owned re-export to one rig: selection-only, no texture embed). |

## vrc-skills

| Key | Purpose |
| --- | --- |
| `import-vendor-asset` | Bring a vendor avatar/outfit/hair/accessory into AvatarProject. |
| `own-base` | Build our owned, uploadable copy of a vendor base body. |
| `own-mergeable` | Build our owned copy of a mergeable's geometry (outfit/hair/accessory) — extract, reproportion, seam — so it composes like a vendor one. |
| `compose-mergeable` | Place a seam-authored outfit/hair/accessory onto an avatar base (verify seam, de-conflict meshes, shape coherence). |
| `map-outfit-shapes` | Reason out how a body's blendshapes couple to its clothing/outfit meshes (the shape↔mesh map, across FX/MA/VRCFury idioms), then act on it — de-conflict overlapping clothing (base-under-outfit or multi-outfit merge) + release coupled shapes, feed toggle closures and morph-coherence reads. |
| `author-menu` | Generate expression-menu controls/params/wiring on a composed avatar (MA-first); place or front a gimmick's menu. |
| `reproportion` | Reshape proportions and reconcile the Unity side. |
| `showcase-record` | Film a work session (ffmpeg screen capture) and cut it into a short showcase video; manifest-driven `start`/`check`/`stop`/`beats`/`cut`/`teaser`. |
