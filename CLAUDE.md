# Atelier — an AI-operated workshop for VRChat avatar work

This is a **container workspace** for AI-assisted VRChat avatar work. An agent (Claude Code)
**observes** the Unity scene/project and Blender armature, **modifies** them via reviewed
editor/Python scripts (or MCP), and **verifies** the result — with **Git as the audit trail**.

**Read first**, before any avatar work: `docs/nondestructive.md`, then `docs/workflow.md`.

## Layout (container of independent repos)

```
Atelier/                        (this folder = session cwd; workspace docs + launcher)
├─ AvatarProject/               Unity sandbox project
│  ├─ Assets/Agent/             agent I/O: Snapshots/ (tracked); RunLogs/ + Scratch/ (gitignored)
│  ├─ Packages/                 vpm-manifest.json = source of truth; SDK payload gitignored
│  └─ STRUCTURE.md              auto-generated asset-tree snapshot (pre-commit hook; do not hand-edit)
├─ vrc-bridge/                  Python OSC/SteamVR bridge
├─ vrc-unity-tools/             Unity editor packages (creator tools, the agent inspection harness, avatar tools)
├─ vrc-skills/                  Claude Code skills (plugin)
├─ vrc-blender-tools/           Blender extension (FBX import/prune + shape-key-safe rest-pose bake + Unity FBX export)
├─ vrc-patterns/                reusable pattern/gimmick example library (YAML-sourced VPM package; own repo)
├─ vrc-mcp-proxy/               owned stdio MCP proxy wrapping the pinned MCP-for-Unity server (allowlist + per-tool transforms)
├─ references/                  open-source projects we study/replicate; routing in references/README.md
└─ start-vrc.ps1                one-command session launcher
```
Each sub-folder is its own independent git repo (gitignored by this meta-repo).
Folder structure is **intentionally grown interactively** — do not impose a rigid tree.

## Hard constraints

- **Unity 2022.3.22f1** — VRChat-pinned. **Never upgrade** (breaks uploaded content). Already installed.
- **Packages are reproducible**: VPM SDK payloads (`Packages/com.vrchat.*`) are gitignored; only
  `vpm-manifest.json` is tracked. Restore with `vrc-get resolve`. Start **newest + trimmed**; add
  VRCFury/Modular Avatar/NDMF/etc. deliberately via ALCOM, not in bulk.

## Tooling stack

Per-system operating details and domain knowledge — install paths, MCP wiring, build commands,
runtime behavior — live in `docs/`. Read the relevant file before operating in that domain:

- **`docs/nondestructive.md`** — **read first.** How NDMF / Modular Avatar / VRCFury compose avatars non-destructively (build-on-a-clone), and the reference-hardening facts all avatar tooling depends on.
- **`docs/unity.md`** — Unity operating knowledge (always-read): MCP usage, the tool invocation/preview grammar, geometry-change reconcile, sharp edges. (Controller tooling lives in `animator.md`.)
- **`docs/unity-tools.md`** — per-tool contracts for the agent inspection harness (`agent-tools`) and the vendor→owned avatar kit (`avatar-tools`); read when driving one of those tools, alongside `unity.md`'s conventions.
- **`docs/animator.md`** + **`docs/animator-schema.md`** — animator-controller work: the tool doors (report/lint, clean/sweep/repath/own, compile/decompile + the round-trip) and the `CompileController` YAML authoring language. Read for any controller build, inspection, or round-trip.
- **`docs/blender.md`** — Blender operating knowledge: headless batch + Blender MCP usage, the `avatarprep` extension.
- **`docs/workflow.md`** — cross-system orchestration above any one tool: goals, sequencing, Unity↔Blender handoffs.
- **`docs/tool-design.md`** — the interface lens for agent-facing tools; read before adding or changing tools in `vrc-unity-tools`, `vrc-blender-tools`, or skills that drive them.
- **`TOOLS.md`** (repo root) — the system tool index: every callable across `vrc-unity-tools` / `vrc-blender-tools`. Read it to see the whole tool surface at once. (Skills aren't listed there — their descriptions are already injected into your context.)
- **`docs/runtime.md`** + **`docs/gimmicks.md`** + **`docs/verify.md`** — gimmick/animator/network-sync work only: runtime (physics) then gimmicks (patterns) then verify (how to prove a claim); skip for other work.
- **`docs/menus.md`** — expression-menu authoring on composed avatars: where menus live, the control vocabulary, toggles as dependency closures, MA-first substrate choice. Read for any menu/toggle work.
- **`docs/outfits.md`** — base-body (kisekae) clothing conventions: layered toggleable clothing meshes, the clothing↔body-blendshape coupling, and the FX controller as its authoritative map. Read before de-conflicting a base under a composed outfit (the `map-outfit-shapes` skill executes it).
- **`docs/LAYOUT.md`** — AvatarProject folder conventions: untouched-`Vendor/` vs. our-work split, non-Unity files outside `Assets/`.
- **`docs/bootstrap.md`** — from-zero workspace assembly: clone the sub-repos, install + wire Unity·Blender·MCP, verify. Point a fresh agent here to stand the workspace up.
- **`docs/new-project.md`** — runbook for adding another Unity project to an already-working workspace (git/gitignore, VPM, the structure-snapshot hook). Skip in normal sessions.
- **`docs/mochifitter.md`** — roadmap-only brief on the MochiFitter outfit-retargeting tool (not integrated). Read only for that roadmap item.
- **`references/README.md`** — routing table of open-source projects we learn from.

## Rules

1. **Observe before changing.** Read the current state first: exports, callers, shared utilities, scenes, prefabs, Blender files, generated assets, and known-good examples. Do not rewrite what you do not understand.
2. **Simplicity first.** Make the smallest change that solves the requested problem. No features beyond what asked, no abstractions for single-use code. If a senior engineer would call it overcomplicated, simplify.
3. **Prefer deterministic edits.** Use generated scripts, editor tools, Git diffs, and checkpoints over raw asset/YAML edits or opaque write operations.
4. **Examples and tested patterns are ground truth.** When patterns conflict, choose the more recent, more tested, or more local example; say why, and flag the discarded pattern. Do not average incompatible approaches.
5. **Verify intent, not just output.** Tests, scene checks, import checks, and diagnostics should prove the reason the behavior matters. A check that still passes after breaking the business or asset logic is wrong.
6. **Checkpoint after significant steps.** Summarize what changed, what was verified, and what remains. Do not continue from a state you cannot describe back.
7. **Fail loud.** "Done" is wrong if anything was skipped silently. "Verified" is wrong if checks were skipped. Surface uncertainty, missing inputs, and named offenders.
8. **Package source is the authority on package behavior.** Everything we build on ships its source on disk under `Packages/` — Modular Avatar, VRCFury, NDMF, the optimizers (d4rk / Limitex), the shaders (lilToon / Poiyomi). When you need precision about what one *does* — a mechanism, an edge case, an exact name — read that source and assert from it or a live measurement, never from a doc summary or your prior. Our docs orient you to where to look and the traps; they do not adjudicate your specific case.

## Writing for agents (docs, runbooks, skills, comments, handoffs)

Everything written in this workspace is read by another agent.

- **The reader is you** — a model at your own capability level with the repo open. Keep only what it can't derive: decisions made, invisible constraints, traps. If a capable agent would know or do it anyway, the line dilutes the ones that matter.
- **After drafting, make a deletion pass** — remove every sentence the reader could regenerate from the artifacts. Draft-then-delete binds; "be concise" doesn't.
- **Specifics rot.** Bias version-agnostic, outcome-based instructions — point at the enforcement mechanism, not a copied value that will drift. **Update documents, don't add to them**: growing line count should reflect a larger underlying system, not accumulated amendments.
- **Omit, don't litigate.** Say what a thing *is*; frame the general rule so edge cases fall out, and simply don't build what you don't want.
- **Favor clean domain separation.** Duplicated knowledge multiplies rot surface; refactor and reorganize rather than restate.
- Capable models do their best work when given **tools and discretion** — give the outcome and the constraints, not the procedure.
- **Legibility over edge-case cleverness.** Tools are read and driven by frontier models — a tool that's intuitive to use and whose diagnostic you can *trust* beats one that silently handles a rare case but is hard to reason about.