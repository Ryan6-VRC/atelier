Every agent-facing tool across `vrc-unity-tools` / `vrc-blender-tools`, one row each. Rows are routing, not contracts; behavior lives in `docs/unity-tools.md` / `docs/animator.md` (controllers & clips) / `docs/blender.md`. **Sections group by what you are doing, not by which package ships the tool** — `agent-tools` and `avatar-tools` rows sit side by side under several headings — so take a tool's kit, and the literal call to paste, from its row in those docs rather than from the heading above it here. `tools/sync_tool_inventory.py` checks each key against its declaration site at pre-commit and mirrors this file into `README.md`, but never writes a row itself: the agent landing a tool change updates its row by hand at merge.

## vrc-unity-tools

### vrc-unity-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `AgentInspector` | JSON snapshot of a scene object (by hierarchy path or selection) or the whole scene; a generic walk over any component. |
| `RenderAvatar` | Isolated Scene-View render of one avatar subtree, NDMF-preview-resolved, to a contact-sheet PNG. `RenderAvatar.Run` is **operator-eye evidence only**; `RenderAvatar.CaptureDiff` is the pinned-camera exact differential, the only pixel door whose output settles a decision (`verify.md`); a measured clearance settles clipping (`ReportClearance`). |
| `CheckPackage` | Post-import health check: missing (vs. intentionally empty) material/mesh/script refs, plus two FBX material-remap classes (stale vs. unresolved — opposite remedies). |
| `ReportPackage` | Vendor-package report: FBX/mesh inventory, the superset FBX, clip-driven toggle membership, and a non-SDK-namespace census. Four fields state their own reach rather than claiming coverage — read each before trusting it. |
| `CheckHumanoidRig` | Two doors. `CheckHumanoidRig.Run(fbxPath)` gates the humanoid bind against the model geometry (must `MatchHumanoidRig` re-run?); `CheckHumanoidRig.InspectAvatar(avatarRoot)` is scene-scoped and names the humanoid-vs-skinned divergence. PASS/CLASSIFY/FAIL. Contract: `unity-tools.md`. |
| `ReportController` | Markdown digest of an `AnimatorController`: parameters, layers with Write Defaults, states, transitions, blend trees, motions by path + GUID (dangling refs flagged empty-vs-broken at any depth, including inside blend trees), VRC behaviours decoded typed. Contract: `animator.md`. |
| `ReportClip` | Binding digest of a clip, or of every `.anim` under a folder: one row per curve (`path \| type \| propertyName \| keys`). Contract: `animator.md`. |
| `ReportConsole` | The Editor console, every line of every entry, with byte-identical entries collapsed by default; the MCP `read_console` tool is denied in its favour. |
| `CheckAnimator` | PASS/FAIL plus tiered offenders for mechanically-detectable controller rot; the binding-resolution root is auto-detected from a merge site or asserted explicitly, and basis choice alone has flipped this verdict. Contract: `animator.md`. |
| `CheckAvatar` | On a placed in-scene avatar root, names the MA scene refs and clip/controller bindings a base rename silently broke, plus anchor seams and dynamics merge conflicts. Each clip-binding break carries the asset path the caller routes on. For parameters across those same merged surfaces, `ReportComposition`. Contract: `unity-tools.md`. |
| `CheckSeam` | The mechanical fit gate to run before any render: world-position coincidence of weighted humanoid bones, certifying the humanoid skeleton and not accessory placement. `CheckSeam.Run` reflects a placed mergeable's seam mapping; `CheckSeam.CheckBare` takes two skeletons with no *resolvable* seam yet and requires an explicit `maxOffsetMm`. Contract: `unity-tools.md`. |
| `ReportShapeOverlap` | Same-mesh blendshape overlap — the locator for the double-subtraction a worn base `Shrink_*` and an outfit `ShapeChanger` stack over the same vertices, invisible to every other gate here. **Pass `outfitRoot`** or the weight-0 MA reactions never ingest. A report, not a verdict; `map-outfit-shapes` owns the disposition. Contract: `unity-tools.md`. |
| `ReportClearance` | Rest-pose clearance between a body mesh and the physbone chains around it: per joint the gap to the body against the chain's own radius, the gap to every referenced collider (`restContactCm=`), chains already inside the body (`insideBodyCm=`), angle limits with lateral lock flagged, capsule `endToEnd` beside authored `height`, collider coverage per chain, and the bones weighting body vs garment near each chain. Reads the NDMF proxy where one exists and says which surface it read. A report, not a verdict; `fix-clipping` owns the disposition. Contract: `unity-tools.md`. |
| `ReportPenetration` | Garment vertices inside a body mesh at the current pose, edit or play: count, tested, max depth. Counts only within 5 cm of the body surface. Contract: `unity-tools.md`. |
| `ReportGimmick` | Topology digest of a gimmick subtree: contact/physbone/raycast/constraint tables and the mechanically-certain idioms, complete by construction. A declared `parameter` is never traced into an animator; that seam is `ReportComposition`'s. Contract: `unity-tools.md`. |
| `ReportPrefab` | A prefab instance or variant read as its chain, one block per level: objects and components added and removed, property overrides tiered so framework churn is counted rather than read. `ReportPrefab.Run` takes a scene handle (outermost root) or a `.prefab` path; `ReportPrefab.Dependents` is the reverse read, everything under `Assets/` that contains the asset. Contract: `unity-tools.md`. |
| `ReportComposition` | Where behaviour comes from on a **composed** avatar: the merge-surface table, per-parameter declaration/writers/readers across every merged surface, and the authored menu-control union. Plain is authored; `bake:true` measures composed truth, **two-phase** (`ReportComposition.Run` → `ReportComposition.Verify`) — a timed-out call is re-read, never re-run. Contract: `unity-tools.md`. |

### vrc-unity-tools · vendor import

| Key | Purpose |
| --- | --- |
| `ImportPackage` | The heavy-import door, **two-phase** so the result survives a transport timeout: `ImportPackage.Run(path)` kicks off the async import, `ImportPackage.Verify(path, expectedRoot)` re-reads the log — re-read rather than re-import. Contract: `unity-tools.md`. |
| `ConformImportSettings` | Corrects the five import settings that hard-fail a driven upload: `ConformImportSettings.Run(scope, whatIf)`, the scope an asset folder (recursive) or a placed avatar root, where `whatIf` previews the SDK panel's own importer errors pre-build. `.meta`-only, re-runnable, no `force`. Contract: `unity-tools.md`. |

### vrc-unity-tools · transplant kit (vendor → owned)

| Key | Purpose |
| --- | --- |
| `CopyComponents` | Type-driven component copy between hierarchies (a deep VRC tier plus a conservative tier). |
| `MoveComponents` | Move components onto a new holder hierarchy with anchors pinned back; behavior-neutral. |
| `GraftHierarchy` | Copy a named subtree wholesale: structure plus all components, refs remapped. |
| `CopyDescriptor` | Transplant the VRC avatar descriptor, with a fresh PipelineManager. |
| `FixViewpoint` | Recompute `ViewPosition` from a reference rig's viewpoint plus both rigs' Head/eyes; explicit eye `Transform`s override an unmapped-eye humanoid rig, per side, reported as `eyeSrc=`. Contract: `unity-tools.md`. |
| `MatchHumanoidRig` | Conform our humanoid rig to the vendor's bone mapping; `MatchHumanoidRig.Preflight` previews. |
| `ConformRenderers` | Copy materials by renderer name from a source hierarchy and normalize bounds/anchor (optional `ownedToSource` override map — direction is the reverse of the transplant kit's). |
| `OwnMaterial` | Own a vendor material: deep-copy it (or branch/augment an already-owned one), fork the named texture slots into the copy's own subfolder, and unlock a locked-Poiyomi copy — every unforked slot stays on its vendor GUID. The skill chooses which slots. Contract: `unity-tools.md`. |

### vrc-unity-tools · controllers & clips

| Key | Purpose |
| --- | --- |
| `CleanController` | Reset an owned avatar's FX to a blank slate: keep named layers (plus base layer 0), empty params/menu, wire the descriptor. For anything richer, decompile, edit, and recompile instead. |
| `RepathClips` | Segment-safe repath of a controller's owned clip bindings; the caller supplies the moves. |
| `OwnControllerClips` | Fork vendor-linked clips to owned copies and retarget the controller's motion slots. |
| `CompileController` | The animator **write substrate**: compiles a declarative YAML document into a persisted `.controller` plus its inline clips and generated params/menu assets. Atomic, idempotent, `whatIf`-previewable. Schema: [`docs/animator-schema.md`](docs/animator-schema.md). |
| `DecompileController` | The animator **read substrate**, inverse of `CompileController`: walks a built `.controller` back to animator-schema YAML, never mutating it. `Decompile → edit → Compile` is the lossless round-trip **for the controller graph** — not for a `menu:` block, whose asset a recompile in place deletes (`animator-schema.md` §menu). Contract: `animator.md`. |
| `CompileClips` | The **external-clip write door**: compiles a clips-file YAML into standalone, *visible* `.anim` assets a controller references by `ref:` path — where `OwnControllerClips` copies existing clips, this authors them. Emit-only; refuses to clobber a hand-edited clip. Contract: `animator.md`. |
| `NormalizeExpressionClips` | Make expression clips share one binding/key-time set; optionally prune unused curves. |

### vrc-unity-tools · scene utilities

| Key | Purpose |
| --- | --- |
| `RemapMaterials` | Swap materials by asset path across a hierarchy. |
| `ConstrainedDuplicate` | Clone a hierarchy and wire VRC constraints between original and duplicate bones. |
| `GrabPhysBone` | Simulate player manipulation of a physbone in play mode: `GrabPhysBone.Run`/`GrabPhysBone.Reach` grab, `GrabPhysBone.Move`, `GrabPhysBone.Release`, `GrabPhysBone.Advance` steps an exact frame count, `GrabPhysBone.Held` reports state. A held grab pauses the venue. Contract: `unity-tools.md`. |
| `WriteDynamics` | Write a caller-authored VRC dynamics table onto a prefab or scene root: nodes (optionally with a physbone or collider), physbone root moves, physbone field sets, constraint source tables. Validates the whole table before any write; `whatIf` previews; in play it rewrites field sets and constraint weights live. Contract: `unity-tools.md`. |
| `DrivePhysBones` | Pose bones in play mode and sample every physbone chain under a root: tip travel from rest, jitter, per-pose `ReportPenetration` counts and `RenderAvatar` frames. Async: `DrivePhysBones.Run`, then poll `DrivePhysBones.Status()`. Contract: `unity-tools.md`. |

### vrc-unity-tools · publish

| Key | Purpose |
| --- | --- |
| `UploadAvatar` | Batch-upload composed avatars live to VRChat, driving Continuous Avatar Uploader by reflection (optional; absent → REFUSE with the fix). Operator-gated, never autonomous; `whatIf` previews readiness without uploading. |
| `RenderThumbnail` | Baked posed portrait for an avatar's upload thumbnail, **edit-mode** default: bakes the **full VRC SDK preprocess chain**, optimizers included, so it shows what actually uploads — `RenderAvatar` never bakes. One deterministic synchronous call; its PNG feeds `UpdateAvatarRecord`, since `UploadAvatar` takes no image. |
| `ReportAvatarRecord` | An uploaded avatar's **live** blueprint record as the server holds it — the scene is not evidence about what is published; this is. Ids, URLs and the account name never enter output. Async: `ReportAvatarRecord.Run`, then poll `ReportAvatarRecord.Status()`. Contract: `unity-tools.md` §Publish. |
| `UpdateAvatarRecord` | Edit an already-uploaded avatar's name, description, tags and **thumbnail** — no bundle, no re-upload. Fields are null-means-unchanged; `expectCurrentName` is required and chains from `ReportAvatarRecord`. An image is a **second write that can fail alone**, and no later read can confirm it. `ReleaseStatus` is deliberately not settable. Contract: `unity-tools.md` §Publish. |
| `RenderThumbnailPlay` | The same thumbnail from **play mode** — hair/cloth **settled** by the real physbone solver, FX toggles/materials **resolved**. A play **session**, not a call: `RenderThumbnailPlay.Run` → `manage_editor play` → `RenderThumbnailPlay.Shoot` (async, polled with `RenderThumbnailPlay.Status()`) → `manage_editor stop` → `RenderThumbnailPlay.End`. `unity-tools.md` §Thumbnails. |

## vrc-blender-tools

### vrc-blender-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `report_stamps` | Read a `.blend`'s avatarprep provenance: per-armature base/state and each bound mesh's baked-morph map, marking linked data so a linked fit reference reads as one; `--shapekeys [SUBSTR]` additionally lists shape-key **names** per mesh. The query counterpart of `stamp_base`. |
| `compare_armatures` | Seam check: do two rigs share bone names, parents, positions, base, and state? The merge dry-run; `--merge-in` compares across two files. Behavior: `blender.md`. |
| `render_mesh` | Headless contact-sheet render of the scene's render-visible meshes from named world-axis angles (`front,back,left,right,top,bottom` — an unknown one FAILs in-grammar), solid or vertex-color shading; `RenderAvatar`'s Blender sibling. Writes to a pruned temp home by default, or `--out`. |

### vrc-blender-tools · armature & mesh ops

| Key | Purpose |
| --- | --- |
| `apply_pose` | Bake the current pose into the rest pose, shape-key-safe. |
| `merge_armatures` | Union-merge two armatures by bone name behind `compare_armatures`' compat gate — structural, positional, and stamp tiers, with a split override (`force` clears structural offenders, `force_stamps` stamp ones, neither the other) and a `whatif` preview. Behavior: `blender.md`. |
| `prune_bones` | Prune zero-weight bone chains, keeping physbone tips (`whatif` previews the removals as rooted chains); refuses when an object rides a doomed bone unless `force`. |
| `bake_shapekey` | Normal-preserving shape-key→Basis bake; records `avatarprep_baked`. Refuses the head mesh by a **name** list (`--head-mesh-names`, default `Body`) standing in for a geometric check — overriding it asserts where the head lives on this rig. |
| `transfer_shapekeys` | Seat a garment cut against one body configuration onto the body it now wears, by a masked Surface Deform of the body's own keys, and optionally leave those keys on the garment. `--authored KEY=VALUE` names the cut; `--keys` is the optional add; `--scan KEY` reads an unknown authored value off a gap table; `--whatif` measures only. Behavior: `blender.md`. |
| `mark_coverage` | Mark the body triangles an explicit garment set hides — rays from the skin in a cone, blocked only by garment faces on the skin's own bones — and emit the Modular Avatar Delete carrier shape key at polygon granularity. `--whatif` reports; the real run writes the key into the base blend the linked body resolves to, refusing a changed body. Behavior: `blender.md`. |
| `stamp_base` | Stamp `avatarprep_base` (avatar lineage) on an armature; a deliberate agent assertion. |
| `rename_objects` | Rename scene objects as a **set**, so a swap (`Face=Body Body=Body_Base`) is legal rather than a silent `Body.001`; emits the `{ourName: sourceName}` map a by-name material copy consumes. Object names only. Behavior: `blender.md`. |

### vrc-blender-tools · proportions & export

| Key | Purpose |
| --- | --- |
| `apply_proportion_edge` | Apply one declarative proportion edge, validating first and stamping state; `--whatif` validates, then reports the geometry the edge would produce — measured by an in-memory trial, never saved. Behavior: `blender.md`. |
| `import_fbx` | Import an FBX via Blender's current importer, never the legacy one, which reorients bones; stamps new armatures `state="unproportioned"` and returns a sanity snapshot including the source file's unit scale. `export_unity_fbx`'s counterpart. |
| `export_unity_fbx` | Export with the Unity/VRChat FBX recipe onto the canonical meter-unit layout; **permanently mutates the scene it exports** (bakes parked object scale), and serves at most one armature (`--armature` scopes; a multi-rig or linked-data export refuses). Canon: `fbx_export.py`'s Orientation, Scale and Linked data docstrings. |
