# Atelier

Atelier is a workspace where a coding agent (Claude Code) does VRChat avatar work end-to-end: it observes the live Unity scene and Blender armature, modifies them through reviewed scripts and purpose-built tools, and verifies the result. It self-drives most of my process with the organization and rigor I'd use given unlimited time. It uses a mix of:

- Carefully constructed knowledge and routing surfaces to ensure the model reaches the Unity/VRChat information it needs as efficiently as possible.
- Control of Blender and Unity via MCP, with an additional set of generic chainable tools.
- Skills that package each workflow's judgment calls into repeatable units.

The project enforces a strict non-destructive workflow and the agent is fluent in every technique this implies. Vendor assets are never modified, only *owned*: deep-copied exactly as far as a change requires. Avatars remain a modular hierarchy of non-destructive components until upload.

## Showcase

https://github.com/user-attachments/assets/c53430cd-cfc7-43ed-8fd4-733feca46ba7

> Put MidnightReverie on Airi and take six thumbnail shots in play mode. Use a different pose, expression, and background for each one and insert them in the captured footage.

Each run is one uninterrupted session — a single plain-language request in, an avatar out. Every thumbnail links to that run's full cut.

<table width="100%">
<tr><th width="33%">Cut</th><th>Prompt</th></tr>
<tr>
<td align="center"><a href="https://pub-9682660324c24dc7be664b3245e10a3e.r2.dev/2026-07-14-shinano-sweetedgeknit/cut.mp4"><img src="docs/assets/showcase/2026-07-14-shinano-sweetedgeknit.jpg" alt="Shinano × SweetEdgeKnit" width="400"></a><br><a href="https://pub-9682660324c24dc7be664b3245e10a3e.r2.dev/2026-07-14-shinano-sweetedgeknit/cut.mp4"><ins>Watch 1:15</ins></a></td>
<td>Please import Shinano and SweetEdgeKnit, then assemble them in the scene. Author one or two outfit toggles, enter play mode, and capture screenshots before and after.</td>
</tr>
<tr>
<td align="center"><a href="https://pub-9682660324c24dc7be664b3245e10a3e.r2.dev/2026-07-18-manuka-stitchedheart-sio-peridot/cut.mp4"><img src="docs/assets/showcase/2026-07-18-manuka-stitchedheart-sio-peridot.jpg" alt="Manuka × StitchedHeart + Sio × Peridot" width="400"></a><br><a href="https://pub-9682660324c24dc7be664b3245e10a3e.r2.dev/2026-07-18-manuka-stitchedheart-sio-peridot/cut.mp4"><ins>Watch 1:15</ins></a></td>
<td>I have placed a Sio and Manuka in the scene. Please put StitchedHeart in white on Manuka and Peridot in black and red on Sio, and make sure there is no clipping.</td>
</tr>
<tr>
<td align="center"><a href="https://pub-9682660324c24dc7be664b3245e10a3e.r2.dev/2026-07-18-plum-chiffon-swap/cut.mp4"><img src="docs/assets/showcase/2026-07-18-plum-chiffon-swap.jpg" alt="Plum × Chiffon" width="400"></a><br><a href="https://pub-9682660324c24dc7be664b3245e10a3e.r2.dev/2026-07-18-plum-chiffon-swap/cut.mp4"><ins>Watch 2:00</ins></a></td>
<td>Make clean copies of Plum and Chiffon, then extract their outfits as modular prefabs and swap them. Finally, pick one and bring it into play mode to test.</td>
</tr>
<tr>
<td align="center"><a href="https://pub-9682660324c24dc7be664b3245e10a3e.r2.dev/2026-07-18-shinano-noirlace-tallmodel/cut.mp4"><img src="docs/assets/showcase/2026-07-18-shinano-noirlace-tallmodel.jpg" alt="Shinano × NoirLace" width="400"></a><br><a href="https://pub-9682660324c24dc7be664b3245e10a3e.r2.dev/2026-07-18-shinano-noirlace-tallmodel/cut.mp4"><ins>Watch 1:40</ins></a></td>
<td>Bring Shinano into Blender and reproportion her into a tall fashion model. Apply the same adjustment to NoirLace, assemble them in the scene, and build a menu. Organize any dynamics components as you go. Finally, take it into play mode for testing.</td>
</tr>
</table>

## Skills

These skills are how you use the workshop: invoke one by name, or just say what you want and the agent picks the right one. Each runs a complete arc of avatar work end-to-end, driving the tools catalogued at the bottom of this page; most users never need anything past this section. Together they are what this workshop can do, from a vendor `.unitypackage` to a dressed, menued, reshaped avatar live on VRChat.

| Key | Purpose |
| --- | --- |
| [`import-vendor-asset`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/import-vendor-asset/SKILL.md) | Bring any vendor asset (avatar, outfit, hair, accessory) into the project cleanly: handle nested zips and companion MaterialPacks, land it untouched under `Vendor/`, and machine-verify every reference before work begins. |
| [`own-base`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/own-base/SKILL.md) | Turn a vendor avatar into *your* avatar: graph the messy vendor package, then build a clean, normalized, uploadable base body to our conventions. Every step gated, nothing eyeballed. |
| [`own-mergeable`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/own-mergeable/SKILL.md) | Extract an outfit, hair, or accessory into an owned mergeable, even out of a monolithic avatar: reshaped and carrying its own MA or VRCFury non-destructive seam, so it drops onto a base exactly like the vendor original. |
| [`own-material`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/own-material/SKILL.md) | Change how anything looks: recolor a dress, add glitter, glow, prep a hue slider or a Poiyomi convert. Picks the right mechanism (custom textures, property adjustments, clip-driven animations) and deep-copies only what actually changes. |
| [`compose-mergeable`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/compose-mergeable/SKILL.md) | Dress the avatar: drop a ready-made outfit, hair, or accessory onto a base, prove the MA or VRCFury seam mechanically resolved, and de-conflict the meshes it covers. |
| [`map-outfit-shapes`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/map-outfit-shapes/SKILL.md) | Reconcile the links between a body's blendshapes and its clothing: which garment drives which morph, to what values, and what several meshes must agree on. Evaluates FX controllers, non-destructive components, blendshape/mesh names, and vision. |
| [`fix-clipping`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/fix-clipping/SKILL.md) | Fix clipping on a built avatar: a short interview, a measured classification of what is touching what and why, the cheapest reversible fix (colliders and chain settings here; shapes, weights, coverage and fit routed to their owning skills), a number that shows it landed, and the watch list to run in the client. |
| [`author-menu`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/author-menu/SKILL.md) | Give the avatar its in-game controls: expression-menu toggles, radials, and gimmick fronts, planned with the user, closed over their dependencies, and authored non-destructively. |
| [`author-gimmick`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/author-gimmick/SKILL.md) | Build a new gimmick from intent — a touch reaction, a held or droppable prop, synced interactive state: transport and bit design first, authored as recompilable controller text, packaged as one self-contained module, verified up the ladder. |
| [`own-gimmick`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/own-gimmick/SKILL.md) | Take surgical ownership of an existing gimmick module: extract the one subsystem you want, trim a vendor system, or fork a variant — with the checklist that keeps cut modules from silently resurrecting meshes, drifting params, or driving ghosts. |
| [`reproportion`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/reproportion/SKILL.md) | Reshape proportions to taste (longer arms, a custom body, matching your real measurements so IK feels right) as validated, repeatable profiles, with the Unity side reconciled so nothing downstream breaks. |
| [`mochifit`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/mochifit/SKILL.md) | Refit an outfit authored for one base onto a genuinely different, non-topo base: the agent drives MochiFitter end-to-end — install, profile routing, the warp, and cleanup — landing an owned mergeable equivalent to the original. |
| [`shoot-thumbnail`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/shoot-thumbnail/SKILL.md) | Generate your avatar's upload thumbnail as a staged portrait — your choice of dynamic pose, expression, and background, or a look the agent picks to suit the avatar and its outfit. |
| [`upload-avatar`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/upload-avatar/SKILL.md) | The last mile to VRChat: preflight the batch, confirm names and scope, and drive the operator-authorized upload, including re-uploading the ten avatars that inherit one changed base. |
| [`showcase-record`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/showcase-record/SKILL.md) | Film a work session (ffmpeg screen capture) and cut it into a short showcase video. |
| [`fitting-session`](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/fitting-session/SKILL.md) | Wear-test the workshop itself: dispatch worker agents on real vendor-asset tasks, grade independently, distill the sharp edges into a cross-run ledger + fixup kickoffs. |

## Controller authoring

The fluency above forms the common-sense layer required to do useful VRChat work, but is not the ultimate objective of the project. Atelier includes all the tooling needed to apply **frontier model coding aptitude** to controller and gimmick authoring.

- **Decoded structure.** Animator, constraint, physbone, and contact topology arrive as read-only graph digests (`ReportController`, `ReportGimmick`, `CheckAnimator`), so the model reasons over decoded structure instead of raw unity files.
- **Controllers as code.** `DecompileController` and `CompileController` round-trip a built `.controller` to declarative YAML: reviewable, diffable text, the representation coding models are strongest in. Study a vendor controller, modify it, or author a new system from scratch.
- **A closed validation loop.** The emulator lets the agent drive parameters, frame-step, induce physbone grabs, fake another player's contacts, and spawn remote clones; so it can self-test its work in play mode and iterate instead of asserting.

## Pattern library

The [`vrc-patterns`](https://github.com/Ryan6-VRC/vrc-patterns) library is both evidence of the system's capabilities and a resource agents can draw on. It contains a mix of known systems normalized into documented NDMF modules as well as new creations, with a lot more to come. When asked to understand, modify, or author a gimmick the patterns library provides deep domain knowledge and tested working designs to copy or compare against. Browse by [what you want to build](https://github.com/Ryan6-VRC/vrc-patterns#find-by-what-you-want-to-build).

![anchor-prop animator controller](docs/assets/anchor-prop-controller.png)

## Tools for AI

Most Unity plugins and Blender scripts are designed for humans, so they hide complexity behind clever defaults. Tooling built for an AI operator inverts that: legibility beats edge-case cleverness. If a tool cannot do exactly what was asked, it refuses and explains why, so the driving model can understand and adapt. This makes the system robust to the enormous variety of creator assets; there are no brittle hard-coded workarounds to outgrow.

The same philosophy governs the workspace's own working process: project skills in [`.claude/skills/`](.claude/skills/) — [`write-for-agents`](.claude/skills/write-for-agents/SKILL.md) for the writing craft in every doc, skill, and diagnostic an agent will read; [`kickoff`](.claude/skills/kickoff/SKILL.md) and [`dispatch`](.claude/skills/dispatch/SKILL.md) for authoring work briefs and coordinating worker sessions. [`write-pattern-readme`](.claude/skills/write-pattern-readme/SKILL.md) for a `vrc-patterns` entry README, new or rewritten, with its audit and review loop. (They live in this repo, not the plugin — the skills table above is the workshop's avatar workflows.)

## Repos

Cloning this meta-repo gets you the docs + launcher, **not** the tools; each **tool** repo below is its own independent git repo, gitignored here as a sibling you clone into place. `AvatarProject` (last) is different — an untracked Unity working venue, not a tracked repo.

- **[`vrc-unity-tools/`](https://github.com/Ryan6-VRC/vrc-unity-tools)** — Unity editor packages (UPM): the agent inspection/verification harness (`agent-tools`) and the vendor→owned transplant kit (`avatar-tools`). Editor-only, SDK-gated, tested.
- **[`vrc-blender-tools/`](https://github.com/Ryan6-VRC/vrc-blender-tools)** — the `avatarprep` Blender extension: shape-key-safe rest-pose bake, proportion profiles, armature merge/prune, Unity FBX export. Blender 5.1+, with an N-panel for humans and headless CLIs for agents over the same core.
- **[`vrc-skills/`](https://github.com/Ryan6-VRC/vrc-skills)** — the Claude Code skills plugin: the import / own / compose / reproportion / menu workflows as repeatable, gated units of work.
- **[`vrc-patterns/`](https://github.com/Ryan6-VRC/vrc-patterns)** — a VPM library of reusable, verified avatar patterns, controllers, and drop-in gimmick modules: YAML-sourced (`CompileController`), gated on compile→decompile-equality, with built assets committed only where a prefab references them by GUID. [**Browse the catalog**](https://github.com/Ryan6-VRC/vrc-patterns#find-by-what-you-want-to-build) to find an entry by what you want to build.
- **[`vrc-bridge/`](https://github.com/Ryan6-VRC/vrc-bridge)** — a Python runtime bridge between SteamVR controller input and VRChat OSC: zero-config discovery (OSCQuery/mDNS), hot-swappable control mappings, camera-system routing.
- **[`vrc-mcp-proxy/`](https://github.com/Ryan6-VRC/vrc-mcp-proxy)** — an owned stdio MCP interception proxy wrapping the pinned MCP-for-Unity server: validates the upstream tool schemas against a committed baseline, allowlists the tools the agent uses, and applies per-tool request/response transforms so a class of upstream sharp edges is corrected at the moment of failure.
- **[`AvatarProject/`](https://github.com/Ryan6-VRC/AvatarProject)** — an **untracked** Unity working venue (2022.3.22f1, VRChat Avatars SDK via VPM/ALCOM) where the loop runs against real avatar setups. The linked public repo is a stripped **sample skeleton** to seed a fresh clone from (bootstrap removes its `.git`), not the tracked project. One instance of the workspace's conventions, not the only one; stand up more via [`docs/new-project.md`](docs/new-project.md).

## Get the workspace running

To assemble the full workspace on a bare machine (clone the sub-repos, install and wire Unity · Blender · the MCP bridges, then verify), point a capable agent at **[`docs/bootstrap.md`](docs/bootstrap.md)**. Prereqs at a glance: Unity Hub + 2022.3.22f1, Blender 5.1+, `git`/`git-lfs`, `uv`, `vrc-get`/ALCOM, Python 3.10+, Claude Code.

## Tools

_The tool surface the skills above drive. Generated from `TOOLS.md`._

<!-- BEGIN tools -->
<!-- generated from TOOLS.md — edit TOOLS.md, not here -->

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
| `mark_coverage` | Mark the body triangles an explicit garment set hides — rays from the skin in a cone, blocked only by garment faces on the skin's own bones — and emit the Modular Avatar Delete carrier shape key at polygon granularity. `--whatif` reports; the real run writes the key into the base blend the linked body resolves to, refusing a changed body. Behavior: `blender.md`. |
| `stamp_base` | Stamp `avatarprep_base` (avatar lineage) on an armature; a deliberate agent assertion. |
| `rename_objects` | Rename scene objects as a **set**, so a swap (`Face=Body Body=Body_Base`) is legal rather than a silent `Body.001`; emits the `{ourName: sourceName}` map a by-name material copy consumes. Object names only. Behavior: `blender.md`. |

### vrc-blender-tools · proportions & export

| Key | Purpose |
| --- | --- |
| `apply_proportion_edge` | Apply one declarative proportion edge, validating first and stamping state; `--whatif` validates, then reports the geometry the edge would produce — measured by an in-memory trial, never saved. Behavior: `blender.md`. |
| `import_fbx` | Import an FBX via Blender's current importer, never the legacy one, which reorients bones; stamps new armatures `state="unproportioned"` and returns a sanity snapshot including the source file's unit scale. `export_unity_fbx`'s counterpart. |
| `export_unity_fbx` | Export with the Unity/VRChat FBX recipe onto the canonical meter-unit layout; **permanently mutates the scene it exports** (bakes parked object scale), and serves at most one armature (`--armature` scopes; a multi-rig or linked-data export refuses). Canon: `fbx_export.py`'s Orientation, Scale and Linked data docstrings. |

<!-- END tools -->
