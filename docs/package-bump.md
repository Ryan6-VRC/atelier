# VPM package bump — the fact home

Our tooling reflects into MA / VRCFury / NDMF / the emulator by design (no vendor assembly is a compile-time reference of shipped code), so a package bump re-validates exact member signatures that vendors have moved before. The **`package-bump` skill owns the process** — the staged arc, its gates, and the report shape; this doc holds the facts the arc consumes. Commands live in `bootstrap.md` §3.

## Command facts the help text does not surface

- `vrc-get upgrade -p <venue> <id>` takes **one package per invocation**.
- It rewrites only the `locked` block; `dependencies` is the *requested range* and staying below `locked` is the tool's normal shape, not drift to repair.
- No live Editor on the venue during any `vrc-get` operation (`bootstrap.md` §3 owns the churn trap).

## Pin-surface map (which upgrade obliges which re-read)

Route to the homes — each file's own comments carry the member-level detail; do not restate it here.

| Package | Pin homes |
|---|---|
| VRCFury | `VendorReflect.cs` (the ArmatureLink set + RewriteRelativePath), `PlayGateCore.cs` (FixWriteDefaults), `CheckAnimator.cs` (`rewriteBindings`), `ReportConsole.cs` (VF.Exceptions label strings) — the highest pin count; the stage-alone vendor |
| Modular Avatar | `ReactiveMarkers.md` (the completeness blind spot — re-derive, no test covers it), `ReportShapeOverlap.cs` §Build-effective active state, `CheckAvatar.cs` / `CheckSeam.cs` type tables |
| NDMF | `RenderAvatar.cs` settle/attribution set (private internals — highest drift risk per release) |
| Av3Emulator | `EmulatorBinding.cs` (canary-tested, fail-don't-skip) |
| CAU / Poiyomi / lilToon | `CauReflect.cs`, `AvatarRecord.cs`, `OwnMaterial.cs` — **no headless coverage** (TestEditor carries none of them), so a bump of these is verified only by using the door live |
| d4rk / AAO / limitex | no reflection pins; `ReportPackageTests` pins their assembly names only |

## Beyond the pins: behavior the docs measured

A vendor release can add or remove play-mode behavior our measured doc claims depend on — signature-stable, invisible to every canary. The tell in the source diff is the vendor's hook/patch trees (VRCFury `Editor-*/Hooks/`, MA `Editor/HarmonyPatches/`): a hook added or removed there is a behavior change at the exact layer `emulator.md` and `osc.md` measure, so name the affected claim and re-measure it or record why it stands (a removed vendor workaround whose job the SDK took over changes nothing while the SDK is unmoved).
