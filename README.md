# Atelier

An AI-operated workshop for VRChat avatar work. A coding agent (Claude Code) sits at the center of
a live Unity Editor and a live Blender session — **observing** scenes, rigs, and animators through
purpose-built inspection tools, **modifying** them through reviewed editor scripts and MCP, and
**verifying** every change against explicit PASS/FAIL gates — with Git as the audit trail.

What began as an avatar/outfit experiment has grown into a full avatar-production pipeline, run as a
conversation:

- **Import** a vendor `.unitypackage` untouched into a quarantined `Vendor/` tree, referenced by
  GUID, verified healthy on arrival.
- **Own** what needs durable change — rebuild a vendor base or outfit as a clean, editable copy:
  normalize the mesh and armature in Blender, then transplant the rig mapping, materials, descriptor,
  and dynamics back in Unity with type-driven tools.
- **Reproportion** with reusable profiles — declarative armature transforms that apply equally to a
  base and every outfit that shares it, so a whole wardrobe survives a shape change together.
- **Compose** non-destructively — outfits, hair, and accessories attach via Modular Avatar / VRCFury
  and resolve at upload on a clone; vendor assets are never mutated.
- **Author** expression menus, toggles, and gimmicks on the composed result.

Each step is a Claude Code **skill** (judgment, gates, sequencing) driving deterministic **tools**
(the mechanics), so the same work is repeatable on the next avatar. The full callable surface is
[indexed below](#tools).

## Design commitments

- **Observe → modify → verify, always.** Every mutating tool emits a diagnostic with named offenders;
  inspection tools produce diffable JSON snapshots; a failed gate is a stop, not a warning.
- **One tool, many doors.** Logic lives in a pure core; the human menu item, the CLI, the MCP call,
  and the agent entry point are thin doors onto the same function. People and agents drive the
  *identical* code.
- **Non-destructive by construction.** The avatar in the scene is a recipe; the deliverable is built
  at upload time on a throwaway clone (NDMF / Modular Avatar / VRCFury). Vendor assets and `Packages/`
  are read-only to the tooling by policy.
- **Git as the audit trail.** Work is tracked as diffable text — scenes, prefabs, `.meta`, generated
  scripts, tool run logs — so every agent action is reviewable after the fact.

## Repos

Cloning this meta-repo gets you the docs + launcher, **not** the tools — each project below is its
own independent git repo, gitignored here as a sibling you clone into place.

- **[`vrc-unity-tools/`](https://github.com/Ryan6-VRC/vrc-unity-tools)** — Unity editor packages
  (UPM): the agent inspection/verification harness (`agent-tools`) and the vendor→owned transplant
  kit (`avatar-tools`). Editor-only, SDK-gated, tested.
- **[`vrc-blender-tools/`](https://github.com/Ryan6-VRC/vrc-blender-tools)** — the `avatarprep`
  Blender extension: shape-key-safe rest-pose bake, proportion profiles, armature merge/prune, Unity
  FBX export. Built for Blender 5.1+, with an N-panel for humans and headless CLIs for agents over
  the same core.
- **[`vrc-skills/`](https://github.com/Ryan6-VRC/vrc-skills)** — the Claude Code skills plugin: the
  import / own / compose / reproportion / menu workflows as repeatable, gated units of work.
- **[`vrc-bridge/`](https://github.com/Ryan6-VRC/vrc-bridge)** — a Python runtime bridge between
  SteamVR controller input and VRChat OSC: zero-config discovery (OSCQuery/mDNS), hot-swappable
  control mappings, camera-system routing.
- **[`AvatarProject/`](https://github.com/Ryan6-VRC/AvatarProject)** — a **sandbox** Unity project
  (2022.3.22f1, VRChat Avatars SDK via VPM/ALCOM) where the loop runs against real avatar setups.

### AvatarProject is a template, not *the* project

The workspace is multi-project by design. `AvatarProject/` is one instance of its conventions — the
vendor/owned split, the generated `STRUCTURE.md` asset-tree snapshot, reproducible packages via a
tracked `vpm-manifest.json` — and the launcher, hooks, and tooling are all project-agnostic. Stand up
as many Unity projects alongside it as you like: the runbook is
[`docs/new-project.md`](docs/new-project.md), the conventions are
[`docs/LAYOUT.md`](docs/LAYOUT.md).

## Get the workspace running

To assemble the full workspace on a bare machine (clone the sub-repos, install and wire
Unity · Blender · the MCP bridges, then verify), point a capable agent at
**[`docs/bootstrap.md`](docs/bootstrap.md)**. Prereqs at a glance: Unity Hub + 2022.3.22f1,
Blender 5.1+, `git`/`git-lfs`, `uv`, `vrc-get`/ALCOM, Python 3.10+, Claude Code.

## Start a session

```powershell
start-vrc AvatarProject          # or:  start-vrc -Path ..\Projects\AnotherProject
```

Brings up Unity + Blender (with their MCP bridges live), then launches Claude — idempotent, so
re-running doubles as a health check. Per-system operating details live in
[`docs/unity.md`](docs/unity.md) / [`docs/blender.md`](docs/blender.md); agent context in
`CLAUDE.md`; the cross-system workflow in [`docs/workflow.md`](docs/workflow.md).

The [`references/`](references/README.md) routing table maps the open-source VRChat tooling
ecosystem this workspace studies — animator codegen, optimizers, emulators, sync systems — with
explicit license discipline about what gets cloned and what stays study-only.

## Tools

_The callable surface of this system. Generated from `TOOLS.md`._

<!-- BEGIN tools -->
<!-- generated from TOOLS.md — edit TOOLS.md, not here -->

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
| `ImportVerify` | Post-import health check: MISSING (vs. intentionally empty) material/mesh/script refs + stale FBX remaps. |
| `AvatarPackageGraph` | Vendor-package report: FBX/mesh inventory, superset FBX, FX toggles, MA/VRCFury/NDMF presence. |
| `ReproportionFreshness` | Gate: does the humanoid bind still match the model geometry, or must `MatchHumanoidRig` re-run? |
| `ControllerReport` | Markdown digest of an `AnimatorController` — params/layers+WD/states/transitions/blend-trees, motions by path+GUID, typed VRC behaviour decode. |
| `ClipReport` | Markdown binding digest of a clip (or every `.anim` under a folder) — one row per curve (`path \| type \| propertyName \| keys`). |
| `AnimatorLint` | PASS/FAIL + tiered offenders for mechanically-detectable controller rot (root basis auto-detected from a merge site, or asserted). |
| `AvatarLint` | PASS/CLASSIFY: on a placed in-scene avatar root, names the MA-scene-ref + clip/controller-binding refs a base rename silently broke (clip-binding carries `clipAssetPath` for the abort-and-own vs. inline route). Inspection-only. |
| `AvatarGrab` | Isolated Scene-View render of one avatar subtree (NDMF preview-resolved), silhouette-framed from named world-axis angles, headlight-lit, to an OS-temp contact-sheet PNG — the visual backstop for compose de-conflict/fit. Grab in a separate call from any edit — a same-call grab is the pre-edit proxy. |
| `GimmickReport` | Markdown topology digest of a gimmick subtree — contacts/physbones/constraints tables + constraint edge-list (TargetTransform indirection, weights, axes), VRCFury authoring inventory, and mechanically-certain idioms (world anchor, feedback loop, indirection, hold, editor/runtime swap). |

### vrc-unity-tools · transplant kit (vendor → owned)

| Key | Purpose |
| --- | --- |
| `CopyComponents` | Type-driven component copy between hierarchies (deep VRC tier + conservative tier). |
| `RelocateComponents` | Move components onto a new holder hierarchy, anchors pinned back (behavior-neutral). |
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
| `SweepController` | Mark-and-sweep an owned controller's orphaned sub-assets + dead-end transitions (guarded, `whatIf`-previewable) — the mutating half of `AnimatorLint`'s detection. |
| `CompileController` | The animator **write substrate**: compile a declarative YAML document into a persisted `.controller` (+ inline clips, embedded blend trees, `VRCExpressionParameters`). parse→validate→emit→`ControllerRules` lint→atomic persist; idempotent (stable GUID), `whatIf`-previewable. Schema: [`docs/animator-schema.md`](docs/animator-schema.md). |
| `DecompileController` | The animator **read substrate**, inverse of `CompileController`: reachability-walk a built `.controller` back to animator-schema YAML. A READ tool (self-logs to Snapshot, never mutates); named refusals for out-of-vocabulary constructs; `whatIf`. `Decompile→edit→Compile` is the lossless round-trip oracle. Schema: [`docs/animator-schema.md`](docs/animator-schema.md). |
| `SplitHSVGClips` | Generate per-channel HSVG constant-value variant clips (lilToon/Poiyomi `_MainTexHSVG`). |
| `NormalizeExpressionClips` | Make expression clips share one binding/key-time set; optionally prune unused curves. |

### vrc-unity-tools · scene utilities

| Key | Purpose |
| --- | --- |
| `RemapMaterials` | Swap materials by asset path across a hierarchy. |
| `DuplicateAndConstrain` | Clone a hierarchy + wire VRC constraints between original/duplicate bones. |

## vrc-blender-tools

### vrc-blender-tools · inspect & verify (read-only)

| Key | Purpose |
| --- | --- |
| `armature_compat` | Seam check: do two rigs share bone names/parents/positions, base, and state? (The merge dry-run.) |
| `validate_profile` | Gate: will this proportion edge apply cleanly to the live scene? |
| `report_stamps` | Read a `.blend`'s avatarprep provenance — per-armature base/state (+ kind) and a per-armature grouping of each bound mesh's `avatarprep_baked` map (+ an `unbound` bucket). The query counterpart of `stamp_base`. |
| `mesh_grab` | Headless Workbench contact-sheet render of scene meshes from named world-axis angles — solid \| vertexcolor (the RBT "RBT Matched" marker), to an OS-temp PNG. AvatarGrab's Blender sibling. |

### vrc-blender-tools · armature & mesh ops

| Key | Purpose |
| --- | --- |
| `apply_pose_as_rest` | Bake current pose into the rest pose (shape-key-safe). |
| `merge_armatures` | Union-merge two armatures by bone name behind the compat gate; gates on base + state (`force_stamps` overrides the stamp gate, `whatif` previews). |
| `prune_bones` | Prune zero-weight bone chains (keeps physbone tips + attachment bones). |
| `bake_shapekey` | Normal-preserving shape-key→Basis bake (refuses the head mesh); records `avatarprep_baked`. |
| `stamp_base` | Stamp `avatarprep_base` (avatar lineage) on an armature — a deliberate agent assertion. |

### vrc-blender-tools · proportions & export

| Key | Purpose |
| --- | --- |
| `apply_profile` | Apply one declarative proportion edge (validates first; stamps state). |
| `apply_recipe` | Replay an ordered chain of proportion edges. |
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

<!-- END tools -->
