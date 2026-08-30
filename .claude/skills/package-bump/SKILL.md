---
name: package-bump
description: Use when upgrading a Unity venue's VPM/ALCOM packages — "upgrade/bump my packages", pending vendor updates (VRCFury, Modular Avatar, NDMF, the SDK), or any `vrc-get upgrade` about to run. Not adding a new package (`bootstrap.md` §3 `install`), not the MCP-for-Unity server pin (`vrc-mcp-proxy`'s own runbook), and never Unity itself (VRChat-pinned).
---

# Bump a venue's VPM packages

Our tooling reflects into MA / VRCFury / NDMF / the emulator by exact member signature, and vendors have moved those members before — so a bump is a staged arc with verification between stages, not one `vrc-get upgrade` and a green suite at the end. `docs/package-bump.md` is the fact home this skill drives from: the `vrc-get` command facts its help omits, the pin-surface map (which upgrade obliges which re-read), and the hook-tree lesson. Read it before step 1; this skill owns the order and the gates.

**No operator to ask?** `docs/workflow.md` §No operator to ask? owns the protocol. The derivable default: a red baseline ends the task as a report, and a red stage rolls back (step 1's recipe) rather than shipping a fix unattended — never leave a venue between stages, where its packages match no suite run.

## The arc

### 1. Baseline before touching anything

Run the EditMode suite unfiltered — `tools/run-editmode-tests.ps1 -Tag bump-baseline` (`-Tag` is mandatory and names the run's output file; unfiltered means leaving `-Filter` empty) — and require green — a bump on a red baseline cannot be attributed, so a red one ends the task with a report, not a workaround. Copy the venue's `vpm-manifest.json` aside (`vpm-manifest.json.pre-bump-<date>`, beside it); rollback at any later step is restoring that file + `vrc-get resolve`. Confirm no live Editor has the venue open, and `vrc-get update` + `vrc-get outdated -p <venue>` to fix the upgrade set.

### 2. Snapshot the old payloads

Copy each package directory being bumped out of `Packages/` to scratch **before** upgrading — the upgrade deletes the old source, and the old-vs-new diff is the whole basis of step 4. Skipping this because the changelog looks boring is the classic error: the pin map, not the changelog, decides what gets checked.

### 3. Upgrade in stages, suite between

Low-pin-surface packages together first; then the heavily-pinned vendor (the pin map names it — historically VRCFury) **alone**, so a red run names its stage. Run the suite unfiltered after each stage (`-Tag bump-stage-<n>`) — it auto-syncs the **community** set into the test venue, and its vendor canaries fail rather than skip. The SDK trio does not auto-sync: a bumped SDK exits `SDK_DRIFT`, and `tools/setup-test-editor.ps1 -Sync` re-provisions before the re-run. Do not start the next stage on a red run: fix or roll the stage back first.

### 4. Source-check the pins per stage

Diff snapshot vs new payload (`git diff --no-index --name-status`, or GNU `diff -rq` from the Bash tool — PowerShell's `diff` is `Compare-Object` and rejects those flags), then read every **changed** file the pin map routes to — a pinned file absent from the diff needs no read, and rule 10 means the verdict comes from the source on disk, never a release note. Also diff the vendor hook/patch trees (`docs/package-bump.md` §Beyond the pins): an added or removed hook is a behavior change no canary sees — name the doc claim it touches and re-measure it, or record why it stands.

### 5. Live rungs

Headless proves the pins resolve; these prove the venue works. Open the Editor on the bumped venue, then in order: `ReportConsole` verdict OK — its benign families absorb the known vendor noise, so the bar is **no new errors**, never literal zero; delete stale bakes under `Packages/com.vrcfury.temp/Builds/` (`verify.md` owns why a stale bake is non-evidence); PlayGate PASS → play entry → fresh bake with the console still OK; `CheckAvatar` PASS on the scene avatar; `RenderAvatar` with `canary=live`. Leave the Editor as found — closed if you opened it.

### 6. Reconcile the anchors

Grep the tools repo for the old version literals. Move **only** the anchors whose claim you re-measured against the new source in step 4 (`vrc-unity-tools/packages/com.ryan6vrc.agent-tools/Tests/Editor/ReactiveMarkers.md` names its own re-derivation — the completeness check no test covers; the siblings live under the main checkout only, so from a worktree resolve it via `tools/atelier_paths.py`). A comment recording *when* a signature moved is history, not an anchor — leave it. Land the moves as their own PR naming what was re-measured.

### 7. Remaining venues

Each venue bumps by the same arc, but the suite only guards the venue `setup-test-editor.ps1` syncs from — for the others, identical versions inherit step 4's source verdict, and the live rungs ride that venue's next real session unless the bump is the session.

## Report

Name what moved (old→new per package, per venue), the evidence per rung (suite tags, console verdicts, the fresh-bake timestamp), every anchor moved or deliberately left, and each behavior-change finding from the hook diff — flagged even when judged benign, because the judgment has an expiry the reader can check and you cannot.
