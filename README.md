# Atelier

Atelier is a workspace where a coding agent (Claude Code) does VRChat avatar work end-to-end: it observes the live Unity scene and Blender armature, modifies them through reviewed scripts and purpose-built tools, and verifies the result. It can self-drive most of my process with the same organization and rigor I would use if I had unlimited time. It uses a mix of:

- Carefully constructed knowledge `.md` files to inject Unity/VRChat conventions and tooling.
- Full control of Blender and Unity via MCP, although models generally prefer to run Blender headless.
- A set of chainable and legible Blender and Unity tools.
- Claude Code skills that package each workflow's judgment calls (own a base, compose an outfit, author a menu) into repeatable units.

The project is opinionated. Vendor assets are never modified, only *owned*: deep-copied exactly as far as a change requires, while the avatar in the scene stays a non-destructive recipe until upload. The agent is fluent in the workflows this implies; it can split an avatar across FBXs and merge it back with Modular Avatar or VRCFury, physbone/constraint/contact topology intact, authoring FX controllers and menus as needed.

## Skills

These skills are how you use the workshop: invoke one by name, or just say what you want and the agent picks the right one. Each runs a complete arc of avatar work end-to-end, driving the tools catalogued at the bottom of this page; most users never need anything past this section. Together they are what this workshop can do, from a vendor `.unitypackage` to a dressed, menued, reshaped avatar live on VRChat.

| Key | Purpose |
| --- | --- |
| `import-vendor-asset` | Bring any vendor asset (avatar, outfit, hair, accessory) into the project cleanly: handle nested zips and companion MaterialPacks, land it untouched under `Vendor/`, and machine-verify every reference before work begins. |
| `own-base` | Turn a vendor avatar into *your* avatar: graph the messy vendor package, then build a clean, normalized, uploadable base body to our conventions. Every step gated, nothing eyeballed. |
| `own-mergeable` | Extract an outfit, hair, or accessory into an owned mergeable, even out of a monolithic avatar: reshaped and carrying its own MA or VRCFury non-destructive seam, so it drops onto a base exactly like the vendor original. |
| `own-material` | Change how anything looks: recolor a dress, add glitter, glow, prep a hue slider or a Poiyomi convert. Picks the right mechanism (custom textures, property adjustments, clip-driven animations) and deep-copies only what actually changes. |
| `compose-mergeable` | Dress the avatar: drop a ready-made outfit, hair, or accessory onto a base, prove the MA or VRCFury seam mechanically resolved, and de-conflict the meshes it covers. |
| `map-outfit-shapes` | Reconcile the links between a body's blendshapes and its clothing: which garment drives which morph, to what values, and what several meshes must agree on. Evaluates FX controllers, non-destructive components, blendshape/mesh names, and vision. |
| `author-menu` | Give the avatar its in-game controls: expression-menu toggles, radials, and gimmick fronts, planned with the user, closed over their dependencies, and authored non-destructively. |
| `author-gimmick` | Build a new gimmick from intent — a touch reaction, a held or droppable prop, synced interactive state: transport and bit design first, authored as recompilable controller text, packaged as one self-contained module, verified up the ladder. |
| `own-gimmick` | Take surgical ownership of an existing gimmick module: extract the one subsystem you want, trim a vendor system, or fork a variant — with the checklist that keeps cut modules from silently resurrecting meshes, drifting params, or driving ghosts. |
| `reproportion` | Reshape proportions to taste (longer arms, a custom body, matching your real measurements so IK feels right) as validated, repeatable profiles, with the Unity side reconciled so nothing downstream breaks. |
| `shoot-thumbnail` | Generate your avatar's upload thumbnail as a staged portrait — your choice of dynamic pose, expression, and background, or a look the agent picks to suit the avatar and its outfit. |
| `upload-avatar` | The last mile to VRChat: preflight the batch, confirm names and scope, and drive the operator-authorized upload, including re-uploading the ten avatars that inherit one changed base. |
| `showcase-record` | Film a work session (ffmpeg screen capture) and cut it into a short showcase video. |
| `fitting-session` | Wear-test the workshop itself: dispatch worker agents on real vendor-asset tasks, grade independently, distill the sharp edges into a cross-run ledger + fixup kickoffs. |

## Controller authoring

The fluency above forms the baseline "common sense" layer required to do useful VRChat work, but is not the ultimate objective of the project. A full set of tools is included to enable full use of frontier model coding aptitude for controller and gimmick work.

- **Decoded structure.** Animator, constraint, physbone, and contact topology arrive as read-only graph digests (`ReportController`, `ReportGimmick`, `CheckAnimator`), so the model reasons over decoded structure instead of raw unity files.
- **Controllers as code.** `DecompileController` and `CompileController` round-trip a built `.controller` to declarative YAML: reviewable, diffable text, the representation coding models are strongest in. Study a vendor controller, modify it, or author a new system from scratch.
- **A closed validation loop.** The emulator lets the agent drive parameters, frame-step, induce physbone grabs, fake another player's contacts, and spawn remote clones; so it can self-test its work in play mode and iterate instead of asserting.

## Tools for AI

Most Unity plugins and Blender scripts are designed for humans, so they hide complexity behind clever defaults. Tooling built for an AI operator inverts that: legibility beats edge-case cleverness. If a tool cannot do exactly what was asked, it refuses and explains why, so the driving model can understand and adapt. This makes the system robust to the enormous variety of creator assets; there are no brittle hard-coded workarounds to outgrow.

## Repos

Cloning this meta-repo gets you the docs + launcher, **not** the tools; each **tool** repo below is its own independent git repo, gitignored here as a sibling you clone into place. `AvatarProject` (last) is different — an untracked Unity working venue, not a tracked repo.

- **[`vrc-unity-tools/`](https://github.com/Ryan6-VRC/vrc-unity-tools)** — Unity editor packages (UPM): the agent inspection/verification harness (`agent-tools`) and the vendor→owned transplant kit (`avatar-tools`). Editor-only, SDK-gated, tested.
- **[`vrc-blender-tools/`](https://github.com/Ryan6-VRC/vrc-blender-tools)** — the `avatarprep` Blender extension: shape-key-safe rest-pose bake, proportion profiles, armature merge/prune, Unity FBX export. Blender 5.1+, with an N-panel for humans and headless CLIs for agents over the same core.
- **[`vrc-skills/`](https://github.com/Ryan6-VRC/vrc-skills)** — the Claude Code skills plugin: the import / own / compose / reproportion / menu workflows as repeatable, gated units of work.
- **[`vrc-patterns/`](https://github.com/Ryan6-VRC/vrc-patterns)** — a VPM library of reusable, verified avatar patterns, controllers, and drop-in gimmick modules: YAML-sourced (`CompileController`), gated on compile→decompile-equality, with built assets committed only where a prefab references them by GUID.
- **[`vrc-bridge/`](https://github.com/Ryan6-VRC/vrc-bridge)** — a Python runtime bridge between SteamVR controller input and VRChat OSC: zero-config discovery (OSCQuery/mDNS), hot-swappable control mappings, camera-system routing.
- **[`vrc-mcp-proxy/`](https://github.com/Ryan6-VRC/vrc-mcp-proxy)** — an owned stdio MCP interception proxy wrapping the pinned MCP-for-Unity server: validates the upstream tool schemas against a committed baseline, allowlists the tools the agent uses, and applies per-tool request/response transforms so a class of upstream sharp edges is corrected at the moment of failure.
- **[`AvatarProject/`](https://github.com/Ryan6-VRC/AvatarProject)** — an **untracked** Unity working venue (2022.3.22f1, VRChat Avatars SDK via VPM/ALCOM) where the loop runs against real avatar setups. The linked public repo is a stripped **sample skeleton** to seed a fresh clone from (bootstrap removes its `.git`), not the tracked project. One instance of the workspace's conventions, not the only one; stand up more via [`docs/new-project.md`](docs/new-project.md).

## Get the workspace running

To assemble the full workspace on a bare machine (clone the sub-repos, install and wire Unity · Blender · the MCP bridges, then verify), point a capable agent at **[`docs/bootstrap.md`](docs/bootstrap.md)**. Prereqs at a glance: Unity Hub + 2022.3.22f1, Blender 5.1+, `git`/`git-lfs`, `uv`, `vrc-get`/ALCOM, Python 3.10+, Claude Code.

## Tools

_The tool surface the skills above drive. Generated from `TOOLS.md`._

<!-- BEGIN tools -->
<!-- generated from TOOLS.md — edit TOOLS.md, not here -->

Every agent-facing tool across `vrc-unity-tools` / `vrc-blender-tools`, one row each. Rows are routing, not contracts; behavior lives in `docs/unity-tools.md` / `docs/animator.md` (controllers & clips) / `docs/blender.md`. The pre-commit hook `tools/sync_tool_inventory.py` verifies each key against its code declaration site (Unity `[AgentTool]` classes, Blender operator names ∪ `cli/` stems) and mirrors this file into `README.md`; it never writes a row itself. The agent landing a tool change updates its row by hand at merge (the hook skips worktrees).

## vrc-unity-tools

### vrc-unity-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `AgentInspector` | JSON snapshot of a scene object (by hierarchy path or selection) or the whole scene; a generic walk over any component. |
| `RenderAvatar` | Isolated Scene-View render of one avatar subtree, NDMF-preview-resolved, to a contact-sheet PNG. Two doors: `Capture` is **operator-eye evidence only** — a model-read of the sheet is never a fit or clipping verdict — and `CaptureDiff`, the pinned-camera exact differential (`verify.md`'s sanctioned form), the only door whose output settles a decision. Contract: `unity-tools.md`. |
| `CheckPackage` | Post-import health check: missing (vs. intentionally empty) material/mesh/script refs, plus stale FBX material remaps. |
| `ReportPackage` | Vendor-package report: FBX/mesh inventory, the superset FBX, FX toggles, MA/VRCFury/NDMF presence. |
| `CheckHumanoidRig` | Gate: does the humanoid bind still match the model geometry, or must `MatchHumanoidRig` re-run? |
| `ReportController` | Markdown digest of an `AnimatorController`: parameters, layers with Write Defaults, states, transitions, blend trees, motions by path + GUID (dangling refs flagged empty-vs-broken at any depth, including inside blend trees), VRC behaviours decoded typed. Contract: `animator.md`. |
| `ReportClip` | Binding digest of a clip, or of every `.anim` under a folder: one row per curve (`path \| type \| propertyName \| keys`). Contract: `animator.md`. |
| `CheckAnimator` | PASS/FAIL plus tiered offenders for mechanically-detectable controller rot; the binding-resolution root is auto-detected from a merge site or asserted explicitly. Contract: `animator.md`. |
| `CheckAvatar` | On a placed in-scene avatar root, names the MA scene refs and clip/controller bindings a base rename silently broke, plus dynamics `merge-conflict`s (≥2 physbones/colliders/constraints resolving to one post-merge transform); PASS/CLASSIFY, inspection-only. Each clip-binding break carries its `clipAssetPath` so the caller can route between repathing inline and owning the asset. |
| `CheckSeam` | On a base + placed mergeable, reflects the MA/VRCFury seam mapping and gates world-position coincidence of weighted humanoid bones within tolerance, naming worst-first offenders. Certifies the humanoid skeleton coincides, not accessory placement; inspection-only, the mechanical fit gate to run before any render. |
| `ReportShapeOverlap` | Same-mesh blendshape overlap: per-shape touched-vertex footprints, pairwise containment, and a resolution table (reaction / current weight / resolved-target). Catches the double-subtraction a worn base `Shrink_*` and an outfit `ShapeChanger` stack over the same vertices — invisible to the render sheet and CheckSeam/CheckAvatar. Assembles its own co-active set, but ingests the weight-0 MA `ShapeChanger` reactions only when passed the outfit root. A report, not a verdict; `map-outfit-shapes` drives it and owns the disposition. |
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
| `ConformRenderers` | Copy materials by renderer name from a source hierarchy and normalize bounds/anchor (optional `ownedToSource` override map — direction is the reverse of the transplant kit's). |
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
| `RenderThumbnail` | Baked posed portrait for an avatar's upload thumbnail — 1200x900 PNG, **edit-mode** default: bakes the **full VRC SDK preprocess chain** (optimizers included), so it shows what actually uploads; `RenderAvatar` never bakes. One deterministic synchronous call. `pose` and optional `expression` are names, and an unknown one enumerates. `png=` feeds `UploadAvatar`. |
| `RenderThumbnailPlay` | Same thumbnail from **play mode** — hair/cloth **settled** by the real physbone solver, FX toggles/materials **resolved**; same caller vocabulary, shared spine (`RenderThumbnailCore`). A play **session**: `Begin` → `manage_editor play` → `Shoot` (async; poll `Status()`) → `manage_editor stop` → `End`. Names any chain **still moving** at capture. `unity-tools.md` §Thumbnails. |

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
| `prune_bones` | Prune zero-weight bone chains, keeping physbone tips (`whatif` previews the removals as rooted chains); refuses when an object rides a doomed bone unless `force`. |
| `bake_shapekey` | Normal-preserving shape-key→Basis bake (refuses the head mesh); records `avatarprep_baked`. |
| `stamp_base` | Stamp `avatarprep_base` (avatar lineage) on an armature; a deliberate agent assertion. |

### vrc-blender-tools · proportions & export

| Key | Purpose |
| --- | --- |
| `apply_proportion_edge` | Apply one declarative proportion edge, validating first and stamping state; `--whatif` validates read-only against the live scene. |
| `import_fbx` | Import an FBX via Blender's current importer (never the legacy one, which reorients bones); stamps new armatures state="unproportioned" and returns a sanity snapshot. `export_unity_fbx`'s counterpart. |
| `export_unity_fbx` | Export with the Unity/VRChat FBX recipe; `--armature` scopes an owned re-export to one rig (selection-only, no texture embed). |

<!-- END tools -->
