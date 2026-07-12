# Animator controllers — the tool doors

The contract for every animator/controller tool: what each door does, its verdict grammar, and when to
reach for it. The YAML **authoring language** the compile/decompile doors speak is `animator-schema.md`;
the one-line index of the whole callable surface is `TOOLS.md`. Shared plumbing lives in `unity.md`: the
`agent-tools`/`avatar-tools` package split, the `RunLogFormat` reporting conventions (`… => RESULT |
log=<path>`; `RunLogs/` verdicts vs `Snapshots/` read-captures), and the `whatIf`/`preflight` preview
grammar every mutating tool obeys.

## Reading a controller

Three read-only introspection tools (`agent-tools`) turn raw `.controller`/`.anim` YAML into cheap
deterministic digests:

- `ReportController.Report(controller)` — a ~50:1 markdown digest that *decodes* animator semantics rather
  than echoing YAML: parameters, layers (+ per-layer Write-Defaults), states and their motions (clips named
  by **asset-path + GUID**, an empty-vs-broken split that surfaces a dangling motion GUID), the first-match
  transition ladder, and VRC state-machine behaviours decoded **typed**. To `Snapshots/`; `… layers=…
  states=… params=… => OK | log=<path>`.
- `ReportClip.Report(clip)` / `ReportFolder(folder)` — bindings as a `path | type | propertyName | keys`
  table (one row per curve), paths as-authored (a `""` root shown as `(root)`, never judged). To
  `Snapshots/`. Folder mode mirrors `CheckPackage.VerifyFolder` (`unity.md`), down to the empty-but-valid
  `0 clips => OK`.
- `CheckAnimator.Lint(controller, basis, mergeSite, avatarRoot, mountRoot)` — binary **PASS/FAIL** (FAIL iff
  an `error`-tier rule fires) + per-kind counts + a two-tier offender body, to `RunLogs/`. Only five `error`
  rules flip the verdict — unresolvable-motion-GUID, undeclared-param (VRC built-ins exempt),
  unconditional-entry-shadow, never-firing transition (a state hop with no condition **and** no exit time),
  broken-binding; every heuristic (WD disagreement, orphans, dead layers, cross-package/archive refs) stays
  **advisory**, so the verdict never rests on a guess. Binding resolution needs a root the `.controller`
  lacks: `basis=auto` reads the merge component at `mergeSite` to take the frame the build will (MA
  `pathMode` / VRCFury prop-root preference — `nondestructive.md`), refusing on zero/multiple/mismatched
  components and rendering the choice (`basis=auto→mount(<path>) [MA MergeAnimator]`); `basis=explicit`
  asserts `avatarRoot`/`mountRoot`. Under `auto`, broken-binding demotes to advisory (the build rewrites
  paths, so an authored-scene resolve would false-FAIL).

`CheckAnimator`'s binding-walk is the same one `CheckAvatar` (`unity.md`) reuses for scene-placement
ref-breaks — one walk, so the two doors can't disagree on how a binding resolves.

## Owning & consolidating a controller

These mutate on-disk assets. All are `avatar-tools` static methods, `whatIf`-previewable and idempotent
(conventions in `unity.md`).

- `CleanController(sourceFx, ownedRoot, outDir, keepLayerNames, whatIf=false)` — **resets an owned avatar's
  FX to a blank slate at the start of a build**: discards the vendor's elaborate FX down to a minimal
  controller keeping the **named** layers (base layer 0 always retained; FAILs on an absent/ambiguous name —
  no magic layer count), its **parameter list pruned to what the kept layers reference**, + empty expression
  params/menu, wired into the descriptor. **Create-if-missing / reuse-if-present** with GUID-stable shared asset names
  (`<sourceFx>_Clean.controller`, `VRCExpressionParameters_Empty.asset`, `VRCExpressionsMenu_Empty.asset`)
  so variations of one base share assets; never delete-recreate. `whatIf` reports what it would
  create/reuse, trim, and wire — touching no asset.

The **clip-repathing pair** rewrites *clip binding paths* / motion refs in on-disk `.anim` assets — a
different domain from `RemapReferencesByPath` (scene-object refs, `unity.md`). Both obey the
**read-only-asset rule** (`LAYOUT.md`: `Assets/Vendor/` + `Packages/` read-only) and are single-controller,
**frame-blind** rewriters — the **caller owns frame-correctness** (descriptor / MA MergeAnimator / VRCFury
FullController frames differ, VRCFury may mix absolute + relative in one controller; no whole-avatar sweep)
— though the frame is **discoverable from the merge component** (`nondestructive.md`), which is exactly what
`CheckAnimator`'s `auto` basis reads.

- `RepathClips(controller, oldPaths, newPaths, force=false, whatIf=false)` — deterministic **segment-safe**
  repath of the bindings a controller references (float + objectReference; `Armature/Hips` rewrites
  `Armature/Hips[/…]`, never `Armature/HipsFoo`). **Owned-clips-only** (a read-only clip a move would touch
  FAILs unless `force`); curve-collision + duplicate/empty-path FAIL; every write is re-read from disk and
  content-verified (`force` never bypasses that). Mutates each `.anim` in place; idempotent. `whatIf`
  previews.
- `OwnControllerClips(controller, outDir, scope=VendorOnly, force=false, whatIf=false)` — closes the
  CleanController gap (owned controller still referencing **vendor clips by GUID**): copies in-scope clips
  (`VendorOnly` default | `All`) to owned `.anim` copies under `outDir` (absent-only reuse) and **mutates
  the controller**, repointing every motion slot; disk-truthful residual post-condition. `UC2 =
  OwnControllerClips → RepathClips`.

## The compile/decompile substrate

`CompileController(sourcePath, outDir, whatIf=false)` is the animator **write substrate** — the inverse of
`ReportController`: it compiles a declarative YAML document into a persisted `.controller` (+ inline clips,
embedded blend trees, and a `VRCExpressionParameters` asset listing every non-builtin/non-scratch param,
**unsynced included, for legibility**). Pipeline: parse → validate → emit → the shared `ControllerRules`
graph lint → atomic persist. Atomic + PASS/FAIL: nothing reaches `outDir` unless every stage passes, a
`whatIf` preview leaves nothing on disk, and a recompile of the same source to the same `outDir` is
idempotent (reset-in-place, stable GUID). The RunLog body carries never-failing advisories — per-layer
frame latency (the longest firing-transition chain — conditional or exit-time; a conditional hop is ~1
frame, an exit-time hop costs its state's clip length) and driver↔AAP isolation conflicts (a driver cannot
durably set a clip-written param — `runtime.md`). The schema — every key, accepted values, and traps — is
`animator-schema.md`; the three worked fixtures (`vrc-unity-tools/fixtures/animator-substrate/{debounce,
smoother,codec}.yaml` — a dwell timer, an AAP exponential smoother, a float→bool codec) are its runnable
companions, each compiling clean, linting PASS, and emulator-verified.

`DecompileController(controllerPath, outPath, whatIf=false, stripLayout=false)` is the animator **read substrate**, mirror of
`CompileController`: it reachability-walks a built `.controller` and serializes it back to animator-schema
YAML at `outPath`. PASS/FAIL like the compile door — a clean run returns `[DecompileController] <name>:
layers=… states=… orphans=… unresolved=… => OK | log=<path>`, writing the `.yaml` plus a Snapshot RunLog;
`whatIf` runs the whole walk but writes no `.yaml`; `stripLayout` (default off) drops all graph-layout
capture — the own-a-vendor path, where the vendor's node arrangement is noise; a refusal (an out-of-vocabulary or malformed construct)
is a bare `[DecompileController] FAIL:` naming each, writing nothing. A **READ** tool — it never mutates the
controller, so it self-logs to the **Snapshot** dir (read-capture channel), not the verdict RunLog dir.
Incidental walk data (orphans dropped, unresolved GUIDs, import tolerances) rides in the document's
`_notes:` block, which re-compiles inert.

`CompileClips(sourcePath, outDir, force=false, whatIf=false)` is the **second write door**: the sole *authoring* writer
of external clips — it emits clip content from a clips-file YAML, where `OwnControllerClips` emits standalone
`.anim`s only by *copying* existing clips. Its source is a clips file — the same schema surface (`schema:`, `basis:`, `clips:`,
optional `parameters:`) but with **no `layers:`** — and it emits each clip to `<outDir>/<clip>.anim` as a
standalone, *visible*, human-editable asset (contrast the controller's hidden inline sub-assets). **Which
clips belong here:** hand-authored artifacts a human sees, tunes, or repaths as a unit (poses, expressions,
toggle targets) — not generated plumbing, which stays inline even when it targets a material (AAP and
blend-tree endpoints; `animator-schema.md` §external clips carries the decidable rule). The contract is in its
doc-comment; the load-bearing decisions:

- **Emit-only — never prunes.** A clip dropped from the file is left on disk, which is exactly what makes
  *promotion* a no-op: delete a clip from the file to hand it to a human, and the controller's path `ref:`
  keeps resolving to an `.anim` no compile touches again (`animator-schema.md` §external clips).
- **Refuses to clobber a hand-edit.** It stamps each `.anim` with a content hash and, on recompile, writes
  nothing if the on-disk clip diverged from that stamp — so *promote to keep edits*, don't `force` over them.
  `force` overrides both this divergence refusal and the read-only-outDir (`Vendor/`/`Packages/`) guard.
- **Writer/reader split → two-door order.** `CompileClips` writes; `CompileController` only reads (a path
  `ref:` resolves like any motion, a miss fails loud). Compile the clips file **before** the controller: a
  controller has no back-reference to its clips file, so an unresolved `ref:` into a clips `outDir` usually
  just means the clips file is uncompiled — read the failure that way before hunting a missing asset.

External clips decompile as a path `ref:`, never re-inlined; the embedded/inline path is unchanged and the
vrc-patterns gate stays green.

**The round-trip reframes the owning tools above.** `Decompile→edit→Compile` emits a controller that is a
pure function of the document — **graph node layout included, so a hand-arranged controller round-trips its
positions** (`animator-schema.md` §layout). For any controller you are willing to **own** (decompile), orphan
sub-assets, unwanted layers, and stale clip refs all vanish on recompile — subsuming the in-vocabulary use
of `CleanController` and `OwnControllerClips`. Each is nonetheless **KEEP**, narrowed to
the niche the round-trip can't reach: **vendor-lineage controllers we deliberately don't decompile**
(Decompile refuses their out-of-vocabulary constructs). `CleanController` trims those by layer **name**
without parsing contents; `OwnControllerClips` forks vendor `.anim`s the compiler holds outside its document
scope.

`SchemaValidation` (pre-emit gate on the typed document — condition operator-vs-param-type legality,
reserved names, base-fx layer floor, dangling default/inline-clip refs) and `ControllerRules` (post-emit
graph oracle on the built asset — missing motions, undeclared params, orphans, dead transitions) **stay
separate**: two representations, not two copies of one check. They share the one rule library
`ControllerRules.Run` (both `CheckAnimator` and `CompileController` call it); each pass catches what only its
representation can express, and the lone overlap — parameter declaration — is partitioned by an explicit
deferral, so there is no duplicated rule to merge.

## Trap — the playable-layer enum

Reading `VRCAvatarDescriptor.baseAnimationLayers` from YAML: the `type` field is the `AnimLayerType` enum —
Base=0, Additive=2, Gesture=3, Action=4, FX=5 (the enum skips 1, `Deprecated0`; special layers: Sitting=6,
TPose=7, IKPose=8). Array index ≠ enum value; an off-by-one read misattributes the FX slot as Sitting (a
real past misread). These are the slots `animator-schema.md`'s `role:` names.
