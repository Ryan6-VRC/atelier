# VPM package bump — upgrading vendor packages under reflection pins

Our tooling reflects into MA / VRCFury / NDMF / the emulator by design (no vendor assembly is a compile-time reference of shipped code), so a package bump is a checklist, not a `vrc-get upgrade` and a shrug: the pins are exact member signatures that vendors have moved before, and the EditMode suite's canaries catch most — not all — of what can drift. Commands live in `bootstrap.md` §3; this runbook owns the order and the re-validation surface.

## Command facts the help text does not surface

- `vrc-get upgrade -p <venue> <id>` takes **one package per invocation**.
- It rewrites only the `locked` block; `dependencies` is the *requested range* and staying below `locked` is the tool's normal shape, not drift to repair.
- No live Editor on the venue during any `vrc-get` operation (`bootstrap.md` §3 owns the churn trap).

## The staged arc

1. **Baseline.** Run the EditMode suite unfiltered (`tools/run-editmode-tests.ps1`) and require green *before* touching anything — a bump on a red baseline cannot be attributed. Copy `vpm-manifest.json` aside (`vpm-manifest.json.pre-bump-<date>`); rollback is restoring it + `vrc-get resolve`.
2. **Snapshot the old payloads.** Copy each package dir being bumped (at minimum MA, NDMF, VRCFury) out of `Packages/` to scratch before upgrading — the upgrade deletes the old source, and the source diff below is the cheapest drift detector that exists.
3. **Stage the risky vendor alone.** Upgrade the low-pin-surface packages together, run the suite, then the heavily-pinned vendor (historically VRCFury) by itself and run it again — a red run then names its stage.
4. **Source-check the pins per stage** (rule 10: assert from the source on disk, never a changelog). `diff -rq` snapshot vs new payload, then read every changed file that carries a pin — the map below says which files pin what. A pinned file absent from the diff needs no read.
5. **Live rungs** (headless cannot prove these): open the Editor, `ReportConsole` must verdict OK — its benign families absorb the known vendor noise (MACS, VRCFury build-progress), so the bar is *no new errors*, not literal zero; delete stale bakes under `Packages/com.vrcfury.temp/Builds/` (`verify.md` owns why a stale bake is non-evidence); PlayGate PASS → play entry → fresh bake with console still OK; `CheckAvatar` PASS on the scene avatar; `RenderAvatar` smoke with `canary=live`.
6. **Reconcile anchors.** Grep the tools repo for the old version literals; move only the anchors whose claim you re-measured against the new source (the ReactiveMarkers completeness re-derivation is the canonical one — its own doc names the two MA files to re-read). Historical version references (a comment recording *when* a signature moved) are history, not anchors — leave them.
7. **Other venues.** Each venue bumps by the same arc; the suite only guards the venue `setup-test-editor.ps1` syncs from.

## Pin-surface map (which upgrade obliges which re-read)

Route to the homes — each file's own comments carry the member-level detail; do not restate it here.

| Package | Pin homes |
|---|---|
| VRCFury | `VendorReflect.cs` (the ArmatureLink set + RewriteRelativePath), `PlayGateCore.cs` (FixWriteDefaults), `CheckAnimator.cs` (`rewriteBindings`), `ReportConsole.cs` (VF.Exceptions label strings) |
| Modular Avatar | `ReactiveMarkers.md` (the completeness blind spot — re-derive, no test covers it), `ReportShapeOverlap.cs` §Build-effective active state, `CheckAvatar.cs` / `CheckSeam.cs` type tables |
| NDMF | `RenderAvatar.cs` settle/attribution set (private internals — highest drift risk per release) |
| Av3Emulator | `EmulatorBinding.cs` (canary-tested, fail-don't-skip) |
| CAU / Poiyomi / lilToon | `CauReflect.cs`, `AvatarRecord.cs`, `OwnMaterial.cs` — **no headless coverage** (TestEditor carries none of them), so a bump of these is verified only by using the door live |
| d4rk / AAO / limitex | no reflection pins; `ReportPackageTests` pins their assembly names only |

## Beyond the pins: behavior the docs measured

A vendor release can add or remove play-mode behavior our measured doc claims depend on — signature-stable, invisible to every canary. The tell in the source diff is the vendor's hook/patch trees (VRCFury `Editor-*/Hooks/`, MA `Editor/HarmonyPatches/`): a hook added or removed there is a behavior change at the exact layer `emulator.md` and `osc.md` measure, so name the affected claim and re-measure it or record why it stands (a removed vendor workaround whose job the SDK took over changes nothing while the SDK is unmoved).
