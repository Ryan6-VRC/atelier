# Unity agent tools

Per-tool contracts for the agent inspection harness (`agent-tools`) and the vendor→owned avatar kit
(`avatar-tools`) — the static-method tools called via `execute_code`. The cross-cutting conventions
(string-handle invocation, the namespace-vs-assembly split, the `whatIf`/`preflight` preview grammar)
and the MCP/sharp-edges operating knowledge live in `unity.md`; read it alongside this. Controller and
clip tooling contracts are in `animator.md`.

## Inspection & reporting (agent-tools)

Shipped as the `com.ryan6vrc.agent-tools` package (from `vrc-unity-tools`, consumed via a local `file:`
ref); also home of the shared reporting conventions (`RunLogFormat`, the `[AgentTool]` marker).
`RunLogFormat.WriteRunLog(dir, label, summary, body, ext)` is the body-agnostic writer every
non-transplant emitter routes through: it owns the dir + timestamped filename and appends the in-band
`| log=<path>` trailer, or returns a bare-FAIL with no trailer when the write fails. `RunLogDir`
(`Assets/Agent/RunLogs/`, verdict records) and `SnapshotDir` (`Assets/Agent/Snapshots/`, read-only
captures) are the single declarations of the two output dirs.

**Invocation & preview grammar** — the string-handle invocation rule, the `Ryan6Vrc`/`Ryan6VRC`
namespace-vs-assembly split, and the `whatIf`/`preflight` preview grammar every tool here (and in
§Avatar tools) obeys live in `unity.md` §Agent-callable tools.

`AgentInspector` walks selected/scene objects (incl. VRChat components,
generically via `SerializedObject`) to JSON under `AvatarProject/Assets/Agent/Snapshots/`; the
written path is emitted in-band on the console line (`… => OK | log=<path>`). Agent door:
`AgentInspector.Snapshot("Root/Child/Path", includeChildren, followAssets)` snapshots by hierarchy
path and returns that summary. Any objectReference resolving to a saved asset carries `guid`/`fileId`
(sub-asset-safe) **unconditionally**, so every ref is edit-addressable; a scene-object ref keeps its
`scenePath` instead. `followAssets` additionally inlines a generic `SerializedObject` dump (`fields`,
recursive) of each **ScriptableObject-asset** ref — a `VRCExpressionsMenu` `subMenu` chain or
`VRCExpressionParameters` expands to the whole tree in one snapshot. Non-SO assets (meshes, clips,
controllers) get identity only, not expansion (no overlap with `ReportController`/`ReportClip`). The
expansion is bounded by asset-hop depth and a walk-wide budget, and every cut is signaled inline
(`assetDepthCapped`/`budgetSkipped`/`alreadyDumped`) plus a top-level `assetsTruncated` count — it
dumps raw values; decoding them stays yours.

`ReportGimmick` sits opposite `AgentInspector` on that axis: where `AgentInspector` dumps one object's
raw fields and leaves decoding to you, `ReportGimmick` interprets a whole gimmick subtree into a
compact digest — constraint edge-lists, physbone/contact tables, and mechanically-certain idioms — and
is complete by construction: a generic tier-2 census names every component no table interpreted
(Modular Avatar, custom scripts, broken scripts) with a one-struct-level scalar peek, so `other=0`
genuinely means empty. Reach for it to reason about a gimmick's topology; drop to
`AgentInspector.Snapshot(<host path>)` only for what's past that shallow peek — a component's nested
structs, arrays, or followed assets.

`CheckPackage.VerifyFolder(path)` / `VerifySelection()` is the deterministic import
health check — reports **missing** (not merely empty) material slots, meshes, and scripts, plus
**stale FBX material remaps** (a model whose external-material remap resolves yet imports empty). Its
one-line PASS/FAIL summary ends with the RunLog path in-band (`… => RESULT | log=<path>`); a bad-input
early return is a bare `[CheckPackage] FAIL: …` with no trailer. Distinguishing missing from intentionally-empty submesh slots is the whole
point; raw null counts false-alarm. Call it after every vendor import.

`ImportPackage.Import(path)` / `ImportPackage.Verify(path, expectedRoot?)` is the heavy-import door, and
is **two-phase** because `AssetDatabase.ImportPackage` is async and a 60–700MB import outlives the MCP
transport window. `Import` validates, pre-writes a RunLog at a **stable, package-derived path**, starts
the import, and returns immediately (`… => PENDING | log=<path>`); `whatIf` validates only and reports
`wouldLog=`. A transport timeout on `Import` therefore loses nothing — the RunLog is already on disk, so
re-read it with `Verify` rather than re-running the import. `Verify` re-reads that RunLog and walks the
on-disk `expectedRoot`, emitting PASS / PENDING / FAIL; the on-disk walk is **authoritative over the
callback-written status**, because an import that triggers script compilation reloads the domain and drops
the in-flight callback (leaving the log stuck at `pending`). `Verify` routes deep import health
(missing refs / stale remap) to `CheckPackage.VerifyFolder` rather than duplicating it.

`.controller`/`.anim` files have their own read-only reporters — `ReportController`, `ReportClip`,
`CheckAnimator` (whose binding-walk `CheckAvatar` below reuses) — contracted with the rest of the animator
tooling in `docs/animator.md`.

`CheckAvatar.Inspect(avatarRoot)` is the scene-scoped companion to those digests: on an instantiated
in-scene avatar (descriptor) root it names the two path-encoded reference breaks a base rename leaves after
a placement — **MA scene refs** (the `referencePath`+`targetObject` `AvatarObjectReference` signature:
reactive family / BlendshapeSync / Mesh Settings) and **clip/controller bindings** (descriptor playable
layers + every MA MergeAnimator / VRCFury FullController). It resolves every ref against the **placed
scene** — a to-be-merged bone is present pre-bake and resolves now, a base-rename break does not — so it
predicts nothing about what the build will move and never leans on the `Armature.<Name>` convention. Its
verdict is **`CLASSIFY`** (unresolved refs found — a finding for the agent to route, not a tool failure),
distinct from `PASS` and a bad-input bare `FAIL`. It computes **no** heuristic — it names each offender and
its class, and a `clip-binding` offender carries a distinct `clipAssetPath` (the field the compose agent
routes on: owned/writable ⇒ inline `UC2` clip-fix; `Assets/Vendor/`|`Packages/` ⇒ abort the compose and
route to `own-mergeable`). It also names a **`merge-conflict`** class (also `CLASSIFY`): ≥2 dynamics
components (physbone / collider / VRC-constraint, grouped within a category) that resolve to the **same
post-merge transform** through `CheckSeam`'s reused merge map, ≥1 mergeable-sourced (the raw target being a
map key excludes a pure base↔base duplicate — no baseline needed). MA build-prunes exact-duplicate
physbones, so a flagged MA pair may already resolve; the residue (VRCFury physbones, all
colliders/constraints, non-exact MA pairs) is where it earns its keep. Inspection-only — no scene dirty, no
`.anim` write; the remedy lives in the skill, not the tool.

`CheckSeam.Check(baseRoot, mergeableRoot)` is the mechanical **fit** companion to `CheckAvatar`'s
reference check — the pre-render fit gate `verify.md` calls for (a model can't read a ~5cm misfit off a
sheet). It **reflects the seam's own mapping** (MA `GetBonesMapping()` ∪ VRCFury
`ArmatureLinkService.GetLinks()`, never reimplements name-matching) and counts the **weighted humanoid
bones** (a mapped bone whose base side is humanoid and whose merge side a mergeable mesh skins). The count
branches the verdict: **≤1 → `REFUSE`**, naming which zero-bone case it is — a **BoneProxy**
(offset-tolerant seam, operator-positioned — hair/earring/hat/tail; verify the bake) vs a **bare prop**
(no seam; route to `own-mergeable`), which the skill routes oppositely on; **≥2 → gate** world-space
coincidence at `ε = max(0.5mm, 0.2%·Hips→Head span)` → `PASS`, or `NOT-PASS` with worst-first offenders
and `maxOffset=Nmm` (sub-mm noise vs wrong-base reads at a glance). Non-humanoid bones never gate —
they legitimately deviate up to ~75mm (physbone tuning). Coincidence is one signal across both seam types:
MA keeps the offset (a delta ships as the misfit), VRCFury snaps at bake (a delta means the edit-time view
isn't what ships). `REFUSE` (bare line, no trailer, like `CheckAvatar`'s bad-input `FAIL`) also fires on a
seam that won't resolve onto this base, seams that disagree, a non-humanoid base, or a VRCFury bake-time
scale — abstain-class (proxy, unresolvable) at warning, reflection drift at error. Inspection-only; the
same world-space mm-drift primitive as `MatchHumanoidRig`'s `poseDriftMm`, position-only.

`ReportShapeOverlap.Report(meshObject, shapeNames)` fills the coupling blind spot `CheckSeam`/`CheckAvatar`
leave — neither reads blendshapes. Given a candidate **co-active** shape set the agent names from the
FX/`ShapeChanger` graph, it reports each shape's touched-vertex footprint and pairwise **containment**
(`|A∩B| / min(|A|,|B|)`) on **one** mesh: the double-subtraction `outfits.md` warns of — a base `Shrink_*`
left worn while an outfit `ShapeChanger` shrinks the **same vertices**, stacking into an inverted limb the
render sheet and the fit gates never show. A **`Report`, not a verdict** — it flags pairs past a
conservative, deliberately un-asset-tuned containment floor as places to look; whether an overlap is a
defect or a wanted coupling stays the agent's read of the graph. Same-mesh only; `map-outfit-shapes` drives it.

`RenderAvatar.Capture(target, angles, hide, margin, showGizmos, resolution)` drives the
operator's **Scene View** to render **one** avatar subtree in isolation to a temp contact-sheet PNG —
the clipping/fit backstop `compose-mergeable` defers to the operator. Where the MCP
`manage_camera`/`manage_scene` screenshots render the whole scene, this shows the target alone with the
**NDMF/MA preview resolved** (reactive fit applied). It auto-frames each angle to the drawn silhouette,
so prop-heavy and shader-scaled avatars fit correctly; `margin` pulls back, `hide` drops clutter props
(the build-added ~10 km `Culling` mesh is dropped automatically), `showGizmos` overlays physbone/contact
gizmos. It renders the avatar **as the operator has it** — eye-hidden children stay hidden; to include a
hidden part, un-hide it before the grab and restore it after (the read-only tool never reveals what the
operator hid). Angles are the six world axes `{front,back,left,right,top,bottom}` (default `[front,back]`);
success carries a `png=` trailer to `Read`.

The traps a model won't hit by just calling it: the fit is the editor *preview*, not the baked upload
clone (`nondestructive.md`) — a play-mode build and the operator's eye stay the bar, and **a model-read of
the sheet is not an agent fit gate** (`verify.md` owns why; quantified `CheckSeam` decides the compose
seam). **Grab in a separate
call from any edit** — a same-call grab shows the pre-edit proxy; the summary's `note=` flags an in-flight
rebuild but cannot catch the same-call case. A **transient settle miss logs as a `Warning`, not an
`Error`** — it won't fail a console-clean gate, so just re-grab; a genuine failure stays `Error`. Angles are **world** axes, so a rotated target shows the scene's front (the upside: it also
works on a child or non-avatar object). Headlight shading is truthful for geometry/silhouette/clipping/
fit, not matcap/rim/fresnel. INSPECTION-class: it restores the view transform, display toggles,
selection, and root-level visibility, leaving the scene un-dirtied, and writes to
`Application.temporaryCachePath`; visibility restore is coarse — a nested eye-hide the operator set
under a subtree the grab hid isn't preserved. In **play mode** it captures the
driven runtime: play's game loop pumps `update` ticks continuously, so the reactive rebuild settles on its
own — no separate-call step needed — and the `note=` is suppressed (nothing in flight to flag). It doubles
as the visual companion to `verify.md`. **Grab driven state while still in play**: exiting play reverts the
scene to authoring state, so a post-exit grab can verify only the static baseline — never a
toggle/param-driven claim.

## Avatar tools

`com.ryan6vrc.avatar-tools` (from `vrc-unity-tools`, local `file:` ref) is the agent-callable kit for
turning a vendor avatar into our own normalized avatar. (The package split is by domain, not
read-vs-write: `agent-tools` holds generic Unity inspection/reporting plus the shared conventions;
`avatar-tools` holds the avatar-owning kit, including its own read-only reporters like
`ReportPackage` — and depends on `agent-tools`, never the reverse.) Each tool is a static method invoked via
`execute_code`, emits a one-line summary that ends with its JSON RunLog path in-band
(`… => RESULT | log=<path>`, written under `Assets/Agent/RunLogs/`; omitted only when the write
failed), and is **idempotent** (safe to re-run on the same instance). Per the tool-design grammar a
`Check` carries a `PASS/FAIL` verdict; a `Report` (e.g. `ReportPackage`) is a verdict-free descriptive
digest that ends `=> OK` (or `=> ERROR` only on bad input / a mid-scan exception — never a content verdict). They share `RemapReferencesByPath`, a
path-based remapper that rebinds scene references from the vendor hierarchy to ours, duplicate-sibling
safe.

Avatar assembly here is non-destructive (NDMF / Modular Avatar / VRCFury); see `nondestructive.md` for the
reference-hardening model that governs what these path-based tools can rebind and what they must preserve.

- `ReportPackage.Report(vendorFolder)` — read-only: per-FBX mesh inventory, a head/body **guess**
  (`headGuess`/`bodyGuess`, a most-blendshapes heuristic — verify), the superset FBX (or "none"),
  toggle membership (renderers a clip drives via `m_IsActive` — GameObject-active — not a name
  convention), constraint count, MA/VRCFury/NDMF detection.
- `MatchHumanoidRig` — builds a fresh humanoid from our own model's skeleton (the bind, so it survives
  reproportioning) and conforms the vendor's bone mapping + muscle settings onto it (copying a rig
  wholesale is unreliable). `poseDriftMm` is informational only — a raw max world-space drift of the
  humanoid bones vs the vendor, in mm; expected nonzero after reproportion, never gates. `Preflight`
  reports the pre-reimport preconditions go/no-go without reimporting (the reimport is the operation, so
  there is no `whatIf`).
- `CheckHumanoidRig` — read-only guard: asserts each humanoid bone's stored bind (frozen in the
  `.meta`) still matches the current model's local position, FAILing (named) on drift — catches a
  re-export that skipped re-running `MatchHumanoidRig`. Position-only: Unity stores a thumb-corrected
  bind rotation that legitimately differs even on a healthy rig.
- `ConformRenderers` — assigns vendor materials by renderer name from any source hierarchy (by reference,
  no `.mat` copies; an optional override map covers meshes renamed during normalization) and applies the
  renderer-normalization standard below. `whatIf` previews the full match/verdict and mutates nothing. A
  **mergeable** (no humanoid rig / no `Hips`) **PASSes with a note** on the missing anchor rather than
  FAILing — that missing `Hips` is exactly the input `own-mergeable` prescribes it for; an avatar base
  still resolves its anchor via `Hips`.
- `CopyDescriptor` — gates on scale + face-blendshape parity, transplants the VRCAvatarDescriptor with
  refs remapped, and installs a **fresh PipelineManager** (never the vendor blueprint ID). Post-copy it
  recomputes `ViewPosition` via `FixViewpoint` (non-fatal — a viewpoint miss never flips the transplant
  verdict). `whatIf` runs the gates + critical-ref snapshot and reports the predicted outcome (remap counts
  land only on execute).
- `FixViewpoint(ownedRoot, referenceRoot, whatIf=false)` — recomputes the owned descriptor's `ViewPosition`
  from a **required** known-good `referenceRoot` (vendor source, or the pre-reshape prior version) plus both
  rigs' Head + eyes, re-seating the creator's eye→viewpoint offset on the moved eyes rather than snapping to
  them. **Named FAIL (no guess)** on a non-humanoid rig, unmapped eyes, or coincident eyes. Idempotent. The
  `reproportion` skill drives the in-place case; `CopyDescriptor` calls it post-copy.

The **component-transplant kit** — `CopyComponents`, `MoveComponents`, `GraftHierarchy` over a shared
transplant core — is **component-agnostic**: selection is a list of **type-name strings** (resolved via
`TypeCache`, matched by assignability, fail-loud on ambiguity), so the same tools serve VRC dynamics on a
base body and MA/VRCFury/NDMF on an outfit without the package referencing those assemblies (stays
VRC-SDK-only). Two tiers: a **deep** tier for the closed, owned VRC set (physbone / collider / contact /
VRC-constraint — dependency-follow, `Col_*` leaf-anchor recreate, hard/soft criticality, `force`/scaffold,
from a typed table) and a **conservative** tier for everything else (MA / VRCFury / NDMF / unknown / Unity
built-in constraints — `CopySerialized` + generic object-ref remap, leave-missing-missing). The **reach
root** `(vendorSource, ownedRoot)` bounds the remap: refs to objects under the vendor source rebind to
our counterparts; out-of-reach refs (assets, other-avatar objects) are left for placement-repair.

A **differently-named armature-root GO** (owned `Armature.1` vs vendor `Armature`) nulls every ref through
it under the name-based matching above. `CopyComponents` / `GraftHierarchy` take an optional `renameMap`
(`vendorName ⇒ ownedName`, injective, **case-sensitive**) that reconciles it — one entry
(`"Armature" ⇒ "Armature.1"`) covers hosts and relocated-outside-armature anchor refs alike. An absent map
is a no-op; a non-injective or ambiguous map (one that can't address a unique dest sibling) is a **named
FAIL in both `whatIf` and execute**, never a silent mis-bind.

- `CopyComponents(ownedRoot, vendorSource, typeNames, force=null, renameMap=null, whatIf=false)` — reproduce all
  components of the named types onto our rig, **additive + idempotent** (count-parity skip per
  `(host, type)`; never destroys; a re-run is a no-op). `whatIf` reports the full plan and mutates nothing;
  a real run replays that same plan (preview == execute). A **flagged-missing host is PASS** — the named
  prune-backstop list to triage (`force` it via `vendorRelativePath :: ComponentType`, re-prune, or
  accept). A **null ref on a copied component** is surfaced separately as "verify — may block build"
  (non-fatal but can abort the downstream VRCF/SDK build). **FAIL** only on a vendor-source leak,
  `AddComponent`/scaffold failure, or unresolved type. Copy from the **standalone** vendor source, not an
  outfit already placed in an avatar.
  Flagged-missing hosts are classified in the RunLog note: **`[bone]`** — a skeleton bone absent on our
  rig, a genuine prune/rename divergence to investigate; **`[holder]`** — a non-bone GO the source parked
  the component on (deep-tier only; conservative hosts are untagged, having no scaffold path). When the
  source parked dynamics on holder GOs (a consolidated/grouped avatar), the holder paths are absent on a
  **faithfully re-exported** target and flag `[holder]` — physbones/constraints always, and
  colliders/contacts too **when their holder's parent is also absent** (holders under an `AvatarDynamics/…`
  container). A collider/contact whose holder sits directly under a **surviving bone** is instead
  auto-recreated (`RecreateLeaf`, no force key needed) and never appears in the `[holder]` set. Forcing the
  `[holder]` keys scaffolds those holders back — anchors path-remap to our bones, collider refs resolve by
  topo order — which **reconstructs the grouping, so a following `MoveComponents` is redundant**.
  Force-all-`[holder]` is safe **only** when the target is a faithful re-export (no bones pruned, no
  content dropped — the reproportion twin/copy case); on the vendor→owned path a `[holder]` may be a
  deliberately-pruned accessory, so the flagged-missing default (force / re-prune / accept) stands.
- `MoveComponents(ownedRoot, targetRoot, typeNames, destPath, whatIf=false)` — relocation primitive
  (the type-name list replaces the old `mode`). Matches components whose effective anchor descends from
  `targetRoot`, mints a holder under `destPath`, pins each anchor to its original transform — behavior-neutral,
  **never moves a bone**. Anchor field per type comes from the VRC table; a targeted type with **no table
  anchor FAILs loud** (refuses MA/VRCF/NDMF *and* Unity built-in constraints). Idempotent (skips a holder
  already placed under `destPath`); run **pre-prefab**. Called N times at operator discretion; echoes matches for closed-accounting.
- `GraftHierarchy(ownedRoot, vendorSource, subtreeRoots, renameMap=null, whatIf=false)` — copies named GO **subtrees
  wholesale**: scaffold the full structure (vendor verbatim local TRS) + copy **all** components on every
  GO (type-blind), remapped against the reach root. For pulling an outfit's authoring/menu subtree without
  listing every GameObject. Inverted contract vs CopyComponents: a missing host is **expected/normal**
  (you are scaffolding), never flagged. Count-parity + reuse-by-path idempotent.

The **controller owning/consolidation kit and the compile/decompile substrate** — `CleanController`, the
clip-repathing pair (`RepathClips`/`OwnControllerClips`), `CompileController`/
`DecompileController`, and the `SchemaValidation`↔`ControllerRules` split — are `avatar-tools` members
obeying the same static-method + `whatIf` + RunLog conventions as the tools above. Their contracts, the
`Decompile→Compile` round-trip that reframes the owning tools, and the YAML authoring language are in
`docs/animator.md` (schema: `docs/animator-schema.md`).

Two standalone **scene utilities** round out the kit, simple enough that the signature is the contract
(open the tool): `RemapMaterials` — swap materials by **asset path** across a hierarchy, in place (no
source hierarchy, no name matching — a different operation from `ConformRenderers`' copy-by-renderer-name);
`ConstrainedDuplicate` — clone a hierarchy and wire VRC constraints between original and duplicate bones.

The **`own-base` skill** (in `vrc-skills`) orchestrates these — it holds the judgment, gates, and
sequencing; the tools hold the mechanics. In a transplant diagnostic, read what each count *means*: a
**flagged-missing host is PASS** (expected subset — triage the named list), while a **vendor-source leak**
or a **null ref on a copied component** stays stop-and-investigate (almost always a name/path mismatch).

**Renderer-normalization standard:** every renderer's bounds are **ensured ≥** center (0,0,0)/extents
(1,1,1) — grown to that anti-cull floor, never shrunk, so a deliberately larger box survives — the
Anchor Override is set to **Hips** only when invalid (null or not a child of `ownedRoot`); a valid
internal anchor is preserved, and a null Root Bone is filled with Hips. Not copied from the vendor (creators get these wrong). On a *composed*
avatar, Modular Avatar `Mesh Settings` can own bounds/anchor at build — there the tool's writes are
authoring-only, so its PASS is not a runtime guarantee.

`OwnMaterial(materialPath, outDir=null, forkTextureSlots=null, newName=null, force=false, whatIf=false)` brings a
vendor material into ownership and forks the **named** texture slots into the owned copy's own namespace —
every unforked slot keeps its source-GUID reference, and the `slots[]` provenance table it returns is the
caller's gate. Routing is target-identity: `outDir` given ⇒ own a vendor source (or branch an owned one) into
a NEW `.mat` (named `newName`, default the source's name); `outDir` omitted ⇒ augment the already-owned source
in place (fork more slots). A locked-Poiyomi copy is unlocked via Thry's ShaderOptimizer — it **refuses**
rather than risk Thry's blocking dialog when the original-shader tag can't resolve, and leaves the vendor
source untouched. The `own-material` skill holds the judgment of which slots to fork; the tool executes it
deterministically and returns a one-line PASS/FAIL + RunLog path.

## Publish

`UploadAvatar` batch-uploads composed avatars live to VRChat, driving Continuous Avatar Uploader (CAU) by
reflection (CAU absent ⇒ **REFUSE** with the fix). **Operator-gated** — the `upload-avatar` skill's explicit
"upload now" is the only trigger, never autonomous — and fail-loud: verdicts are **PASS / REFUSE / FAIL**,
where REFUSE means the environment isn't ready (CAU absent, not logged in, panel closed, wrong build target)
and FAIL is a genuine upload rejection. It runs async — `Run` fires and returns while the editor update loop
pumps CAU's continuations, so poll `Status()` until it stops reporting "running". A per-handle attempt ceiling
counts *consecutive* failures (cleared on each success) so account safety doesn't lean on skill prose, and
**no blueprint id ever enters output** (public-repo safety). `whatIf` previews readiness without uploading.
