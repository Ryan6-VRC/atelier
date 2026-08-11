Every agent-facing tool across `vrc-unity-tools` / `vrc-blender-tools`, one row each. Rows are routing, not contracts; behavior lives in `docs/unity-tools.md` / `docs/animator.md` (controllers & clips) / `docs/blender.md`. The pre-commit hook `tools/sync_tool_inventory.py` verifies each key against its code declaration site (Unity `[AgentTool]` classes, Blender operator names ∪ `cli/` stems) and mirrors this file into `README.md`; it never writes a row itself. The agent landing a tool change updates its row by hand at merge (the hook skips worktrees).

## vrc-unity-tools

### vrc-unity-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `AgentInspector` | JSON snapshot of a scene object (by hierarchy path or selection) or the whole scene; a generic walk over any component. |
| `RenderAvatar` | Isolated Scene-View render of one avatar subtree, NDMF-preview-resolved, to a contact-sheet PNG. Two doors: `Capture` is **operator-eye evidence only** — a model-read of the sheet is never a fit or clipping verdict — and `CaptureDiff`, the pinned-camera exact differential (`verify.md`'s sanctioned form), the only door whose output settles a decision. |
| `CheckPackage` | Post-import health check: missing (vs. intentionally empty) material/mesh/script refs, plus two FBX material-remap classes (stale vs. unresolved — opposite remedies). |
| `ReportPackage` | Vendor-package report: FBX/mesh inventory, the superset FBX, clip-driven toggle membership, and `nonSdkNs=` — a verbatim non-SDK-namespace census that names no framework and counts the components whose scripts did not resolve. Both of those fields state their own reach rather than claiming coverage. |
| `CheckHumanoidRig` | Two doors. `Run(fbxPath)` gates the humanoid bind against the model geometry (must `MatchHumanoidRig` re-run?); `InspectAvatar(avatarRoot)` is scene-scoped and names the humanoid-vs-skinned divergence — a humanoid bone mapped to a transform nothing skins, or a decoy elsewhere carrying the plain label — because the mapping lives only in the source model's importer and every other artifact reads consistent with the wrong answer. PASS/CLASSIFY/FAIL; "skinned" is instance-or-name, and the name arm is a declared heuristic. |
| `ReportController` | Markdown digest of an `AnimatorController`: parameters, layers with Write Defaults, states, transitions, blend trees, motions by path + GUID (dangling refs flagged empty-vs-broken at any depth, including inside blend trees), VRC behaviours decoded typed. Contract: `animator.md`. |
| `ReportClip` | Binding digest of a clip, or of every `.anim` under a folder: one row per curve (`path \| type \| propertyName \| keys`). Contract: `animator.md`. |
| `ReportConsole` | The Editor console, every line of every entry, with byte-identical entries collapsed by default; the MCP `read_console` tool is denied in its favour. |
| `CheckAnimator` | PASS/FAIL plus tiered offenders for mechanically-detectable controller rot; the binding-resolution root is auto-detected from a merge site or asserted explicitly, and `mergeSites=N (used: <site>)` rides the summary whenever more than one surface on the avatar mounts the controller — basis choice alone has flipped this verdict. Contract: `animator.md`. |
| `CheckAvatar` | On a placed in-scene avatar root, names the MA scene refs and clip/controller bindings a base rename silently broke, `anchor-seam`s (naming the MA anchor a VRCFury-merged binding paths through), plus dynamics `merge-conflict`s (≥2 physbones/colliders/constraints resolving to one post-merge transform); PASS/CLASSIFY, inspection-only. Each clip-binding break carries its `clipAssetPath` so the caller can route between repathing inline and owning the asset. For where a parameter is written and read across those same merged surfaces, `ReportComposition`. |
| `CheckSeam` | Gates world-position coincidence of weighted humanoid bones within tolerance, naming worst-first offenders. `Check` takes a base + placed mergeable and reflects the MA/VRCFury seam mapping; `CheckBare` takes two skeletons with no *resolvable* seam yet (a fresh refit output, an unplaced mergeable), pairs by bone name, and requires an explicit `maxOffsetMm`. Certifies the humanoid skeleton coincides, not accessory placement; inspection-only, the mechanical fit gate to run before any render. |
| `ReportShapeOverlap` | Same-mesh blendshape overlap: per-shape touched-vertex footprints, pairwise containment, and a resolution table (reaction / current weight / resolved-target). Catches the double-subtraction a worn base `Shrink_*` and an outfit `ShapeChanger` stack over the same vertices — invisible to the render sheet and CheckSeam/CheckAvatar. Assembles its own co-active set, but ingests the weight-0 MA `ShapeChanger` reactions only when passed the outfit root; a reaction declared from behind a parked ancestor is annotated `[inactive: …]` for the reader to rule on. A report, not a verdict; `map-outfit-shapes` drives it and owns the disposition. |
| `ReportGimmick` | Topology digest of a gimmick subtree: contact/physbone/raycast/constraint tables, a constraint edge-list spanning both VRC and Unity constraint families (driven/sources, weights, axes), VRCFury authoring inventory, and the mechanically-certain idioms (world anchor, feedback loop, indirection, hold, editor/runtime swap, physbones sharing one target). Complete by construction — a tier-2 census names every component no table interpreted, so `other=0` means empty. A declared `parameter` field is reported but never traced into an animator; that seam is `ReportComposition`'s. |
| `ReportComposition` | Where behaviour comes from on a **composed** avatar: the merge-surface table, per-parameter declaration/writers/readers across every merged surface, and the authored menu-control union (descriptor menu, each FullController's `menus[]`, MA installers and menu items). One door, two modes — plain is the authored census and says so in its cells; `bake:true` measures composed truth off a fresh SDK-preprocess build and diffs it (`kept/renamed/dropped/merged/unattributed`), two-phase so a transport timeout loses nothing, and a bake failure refuses loudly rather than falling back to authored rows. An empty writers cell carries its own scope note, because the writer set for a parameter is open. |

### vrc-unity-tools · vendor import

| Key | Purpose |
| --- | --- |
| `ImportPackage` | The heavy-import door, two-phase so the result survives a transport timeout: `Import(path)` kicks off the async `.unitypackage` import and returns `PENDING` at a stable RunLog path (`whatIf` validates only); `Verify(path, expectedRoot?)` re-reads that log and walks the on-disk root for a PASS/PENDING/FAIL verdict authoritative over the callback status, routing deep health to `CheckPackage`. |
| `ConformImportSettings` | Corrects the import settings that hard-fail a driven upload, folder-scoped and recursive: `RunFolder(folder, whatIf)` over five rows (mip streaming, texture cap, mesh read/write, legacy blendshape normals, audio background load). `.meta`-only, re-runnable, no `force`; the two rows that change what ships name their paths in the summary. |

### vrc-unity-tools · transplant kit (vendor → owned)

| Key | Purpose |
| --- | --- |
| `CopyComponents` | Type-driven component copy between hierarchies (a deep VRC tier plus a conservative tier). |
| `MoveComponents` | Move components onto a new holder hierarchy with anchors pinned back; behavior-neutral. |
| `GraftHierarchy` | Copy a named subtree wholesale: structure plus all components, refs remapped. |
| `CopyDescriptor` | Transplant the VRC avatar descriptor, with a fresh PipelineManager. |
| `FixViewpoint` | Recompute `ViewPosition` from a reference rig's viewpoint plus both rigs' Head/eyes. |
| `MatchHumanoidRig` | Conform our humanoid rig to the vendor's bone mapping; `Preflight` previews. |
| `ConformRenderers` | Copy materials by renderer name from a source hierarchy and normalize bounds/anchor (optional `ownedToSource` override map — direction is the reverse of the transplant kit's). |
| `OwnMaterial` | Own a vendor material: deep-copy it (or branch/augment an already-owned one), fork the named texture slots into the copy's own subfolder, and unlock a locked-Poiyomi copy — every unforked slot stays on its vendor GUID. The skill chooses which slots; the tool's `slots[]` provenance table is the caller's gate. |

### vrc-unity-tools · controllers & clips

| Key | Purpose |
| --- | --- |
| `CleanController` | Reset an owned avatar's FX to a blank slate: keep named layers (plus base layer 0), empty params/menu, wire the descriptor. For anything richer, decompile, edit, and recompile instead. |
| `RepathClips` | Segment-safe repath of a controller's owned clip bindings; the caller supplies the moves. |
| `OwnControllerClips` | Fork vendor-linked clips to owned copies and retarget the controller's motion slots. |
| `CompileController` | The animator **write substrate**: compiles a declarative YAML document into a persisted `.controller`, plus inline clips, embedded blend trees, a `VRCExpressionParameters` asset, and a `VRCExpressionsMenu` when the document declares a `menu:`. Atomic, idempotent (stable GUID), `whatIf`-previewable; every build passes the shared graph lint. Schema: [`docs/animator-schema.md`](docs/animator-schema.md). |
| `DecompileController` | The animator **read substrate**, inverse of `CompileController`: walks a built `.controller` back to animator-schema YAML, never mutating it; refuses out-of-vocabulary constructs by name. `Decompile → edit → Compile` is the lossless round-trip **for the controller graph** — it does not recover a `menu:` block, so recompiling a decompiled document into the folder it came from deletes the menu asset there (loudly; `animator-schema.md` §menu). |
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
| `RenderThumbnail` | Baked posed portrait for an avatar's upload thumbnail — 1200x900 PNG, **edit-mode** default: bakes the **full VRC SDK preprocess chain** (optimizers included), so it shows what actually uploads; `RenderAvatar` never bakes. One deterministic synchronous call. `pose` and optional `expression` are names, and an unknown one enumerates. `png=` feeds `UploadAvatar`. |
| `ReportAvatarRecord` | An uploaded avatar's **live** blueprint record as the server holds it — the scene is not evidence about what is published; this is. Ids, URLs and the account name never enter output. Async: `Run`, then poll `Status()`. Contract: `unity-tools.md` §Publish. |
| `UpdateAvatarRecord` | Edit an already-uploaded avatar's name, description and tags — **metadata only, no bundle, no re-upload**. Fields are null-means-unchanged; `expectCurrentName` is required and chains from `ReportAvatarRecord`. `ReleaseStatus` is deliberately not settable. `whatIf` previews. Contract: `unity-tools.md` §Publish. |
| `RenderThumbnailPlay` | Same thumbnail from **play mode** — hair/cloth **settled** by the real physbone solver, FX toggles/materials **resolved**; same caller vocabulary, shared spine (`RenderThumbnailCore`). A play **session**: `Begin` → `manage_editor play` → `Shoot` (async; poll `Status()`) → `manage_editor stop` → `End`. Names any chain **still moving** at capture. `unity-tools.md` §Thumbnails. |

## vrc-blender-tools

### vrc-blender-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `report_stamps` | Read a `.blend`'s avatarprep provenance: per-armature base/state (plus kind) and each bound mesh's `avatarprep_baked` map; `--shapekeys [SUBSTR]` additionally lists shape-key **names** per mesh, not just counts. The query counterpart of `stamp_base`. |
| `compare_armatures` | Seam check: do two rigs share bone names, parents, positions, base, and state? The merge dry-run. Position verdicts are two-tiered — beyond `--noise-tol` gates the merge, between it and `--tol` is reported noise — because two separately-authored vendor FBXes carry sub-millimetre rounding a single threshold false-FAILs on. `--merge-in` compares across two files. |
| `render_mesh` | Headless contact-sheet render of the scene's render-visible meshes from named world-axis angles (`front,back,left,right,top,bottom` — an unknown one FAILs in-grammar), solid or vertex-color shading; `RenderAvatar`'s Blender sibling. Writes to a pruned temp home by default, or `--out`. |

### vrc-blender-tools · armature & mesh ops

| Key | Purpose |
| --- | --- |
| `apply_pose` | Bake the current pose into the rest pose, shape-key-safe. |
| `merge_armatures` | Union-merge two armatures by bone name behind the compat gate; gates on base and state (`force_stamps` overrides the stamp gate, `whatif` previews), on `compare_armatures`' two-tier position thresholds, and warns when the two rigs' object rotations/origins disagree — there it bakes the world frame and the merged rig matches neither source's vendor orientation. |
| `prune_bones` | Prune zero-weight bone chains, keeping physbone tips (`whatif` previews the removals as rooted chains); refuses when an object rides a doomed bone unless `force`. |
| `bake_shapekey` | Normal-preserving shape-key→Basis bake; records `avatarprep_baked`. Refuses the head mesh by a **name** list (`--head-mesh-names`, default `Body`) standing in for a geometric check — overriding it asserts where the head lives on this rig. |
| `stamp_base` | Stamp `avatarprep_base` (avatar lineage) on an armature; a deliberate agent assertion. |

### vrc-blender-tools · proportions & export

| Key | Purpose |
| --- | --- |
| `apply_proportion_edge` | Apply one declarative proportion edge, validating first and stamping state; `--whatif` validates read-only against the live scene. |
| `import_fbx` | Import an FBX via Blender's current importer (never the legacy one, which reorients bones); stamps new armatures state="unproportioned" and returns a sanity snapshot, including the source file's `unit_scale_factor` (read from the file — the importer normalizes both unit classes into identical scene state). `export_unity_fbx`'s counterpart. |
| `export_unity_fbx` | Export with the Unity/VRChat FBX recipe onto one canonical layout (`FBX_SCALE_ALL`, meter-unit) rather than mimicking the source's unit class; refuses a non-unit scene scale. Clears an armature's object rotation unapplied only when that rotation leaves the up axis fixed; one that moves the up axis is the source's own up-axis conversion and is preserved — clearing it exports the rig tipped onto its face. Names which per armature (`--keep-object-rotation` skips the gate). `--armature` scopes an owned re-export to one rig (selection-only, no texture embed). Canon for all of this is `fbx_export.py`'s orientation docstring; orientation also has a second switch Unity-side — see `blender.md`. |
