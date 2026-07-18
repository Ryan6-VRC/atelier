Every agent-facing tool across `vrc-unity-tools` / `vrc-blender-tools`, one row each. Rows are
routing, not contracts; behavior lives in `docs/unity-tools.md` / `docs/animator.md` (controllers & clips) /
`docs/blender.md`. The pre-commit hook
`tools/sync_tool_inventory.py` verifies each key against its code declaration site (Unity
`[AgentTool]` classes, Blender operator names ∪ `cli/` stems) and mirrors this file into
`README.md`; it never writes a row itself. The agent landing a tool change updates its row by hand
at merge (the hook skips worktrees).

## vrc-unity-tools

### vrc-unity-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `AgentInspector` | JSON snapshot of a scene object (by hierarchy path or selection) or the whole scene; a generic walk over any component. |
| `RenderAvatar` | Isolated Scene-View render of one avatar subtree, NDMF-preview-resolved (proxy-aware, so MA-reactive bodies render), framed from named world-axis angles to a contact-sheet PNG — operator-eye evidence for fit and clipping after a compose. Two doors over one capture core: `Capture` (the contact sheet) and `CaptureDiff` (pinned-camera differential — changed-pixel count + cluster bbox, exact compare, no tolerance), `verify.md`'s sanctioned differential form. Freshness is forced on every drawn SMR (originals + kept NDMF proxies); OK carries `gate=armed` (certified current) or `gate=exempt` (nothing to certify), while an unsettled preview or attribution drift fails the grab loud — re-grab, and treat byte-identical pixels around a verified edit as stale regardless. |
| `CheckPackage` | Post-import health check: missing (vs. intentionally empty) material/mesh/script refs, plus stale FBX material remaps. |
| `ReportPackage` | Vendor-package report: FBX/mesh inventory, the superset FBX, FX toggles, MA/VRCFury/NDMF presence. |
| `CheckHumanoidRig` | Gate: does the humanoid bind still match the model geometry, or must `MatchHumanoidRig` re-run? |
| `ReportController` | Markdown digest of an `AnimatorController`: parameters, layers with Write Defaults, states, transitions, blend trees, motions by path + GUID (dangling refs flagged empty-vs-broken at any depth, including inside blend trees), VRC behaviours decoded typed. Contract: `animator.md`. |
| `ReportClip` | Binding digest of a clip, or of every `.anim` under a folder: one row per curve (`path \| type \| propertyName \| keys`). Contract: `animator.md`. |
| `CheckAnimator` | PASS/FAIL plus tiered offenders for mechanically-detectable controller rot; the binding-resolution root is auto-detected from a merge site or asserted explicitly. Contract: `animator.md`. |
| `CheckAvatar` | On a placed in-scene avatar root, names the MA scene refs and clip/controller bindings a base rename silently broke, plus dynamics `merge-conflict`s (≥2 physbones/colliders/constraints resolving to one post-merge transform); PASS/CLASSIFY, inspection-only. Each clip-binding break carries its `clipAssetPath` so the caller can route between repathing inline and owning the asset. |
| `CheckSeam` | On a base + placed mergeable, reflects the MA/VRCFury seam mapping and gates world-position coincidence of weighted humanoid bones within tolerance, naming worst-first offenders. Certifies the humanoid skeleton coincides, not accessory placement; inspection-only, the mechanical fit gate to run before any render. |
| `ReportShapeOverlap` | Same-mesh blendshape overlap over the co-active set it assembles — caller-passed ∪ worn-nonzero ∪ MA `ShapeChanger` reaction targets (including shapes at weight 0 at edit time the agent can't see) — reporting each shape's touched-vertex footprint, pairwise containment (intersection over the smaller footprint), and a per-shape reaction/weight resolution table. Locates the double-subtraction a base worn `Shrink_*` and an outfit `ShapeChanger` make over the same vertices, invisible to the render sheet and CheckSeam/CheckAvatar; refuses loud (`MISSING`) when an MA reaction type won't resolve rather than silently dropping it. A report, not a verdict: the agent adjudicates wanted-vs-defect. |
| `ReportGimmick` | Topology digest of a gimmick subtree: contact/physbone/constraint tables, a constraint edge-list spanning both VRC and Unity constraint families (driven/sources, weights, axes), VRCFury authoring inventory, and the mechanically-certain idioms (world anchor, feedback loop, indirection, hold, editor/runtime swap). Complete by construction — a tier-2 census names every component no table interpreted, so `other=0` means empty. |

### vrc-unity-tools · vendor import

| Key | Purpose |
| --- | --- |
| `ImportPackage` | The heavy-import door, two-phase so the result survives a transport timeout: `Import(path)` kicks off the async `.unitypackage` import and returns `PENDING` at a stable RunLog path (`whatIf` validates only); `Verify(path, expectedRoot?)` re-reads that log and walks the on-disk root for a PASS/PENDING/FAIL verdict authoritative over the callback status, routing deep health to `CheckPackage`. |

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
| `CleanController` | Reset an owned avatar's FX to a blank slate: keep named layers (plus base layer 0), empty params/menu, wire the descriptor. For anything richer, decompile, edit, and recompile instead. |
| `RepathClips` | Segment-safe repath of a controller's owned clip bindings; the caller supplies the moves. |
| `OwnControllerClips` | Fork vendor-linked clips to owned copies and retarget the controller's motion slots. |
| `CompileController` | The animator **write substrate**: compiles a declarative YAML document into a persisted `.controller`, plus inline clips, embedded blend trees, and a `VRCExpressionParameters` asset. Atomic, idempotent (stable GUID), `whatIf`-previewable; every build passes the shared graph lint. Schema: [`docs/animator-schema.md`](docs/animator-schema.md). |
| `DecompileController` | The animator **read substrate**, inverse of `CompileController`: walks a built `.controller` back to animator-schema YAML, never mutating it; refuses out-of-vocabulary constructs by name. `Decompile → edit → Compile` is the lossless round-trip. |
| `CompileClips` | The **external-clip write door**: compiles a clips-file YAML (top-level `clips:`, no `layers:`) into standalone, *visible* `.anim` assets a controller references by `ref:` path — where `OwnControllerClips` copies existing clips, this authors them. Emit-only, so deleting a clip from the file *promotes* it to human ownership; refuses to clobber a hand-edited clip (`force` overrides). |
| `NormalizeExpressionClips` | Make expression clips share one binding/key-time set; optionally prune unused curves. |

### vrc-unity-tools · scene utilities

| Key | Purpose |
| --- | --- |
| `RemapMaterials` | Swap materials by asset path across a hierarchy. |
| `ConstrainedDuplicate` | Clone a hierarchy and wire VRC constraints between original and duplicate bones. |

### vrc-unity-tools · publish

| Key | Purpose |
| --- | --- |
| `UploadAvatar` | Batch-upload composed avatars live to VRChat, driving Continuous Avatar Uploader by reflection (optional; absent → REFUSE with the fix). Operator-gated, never autonomous; `whatIf` previews readiness without uploading. |

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
