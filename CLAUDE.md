# Atelier — an AI-operated workshop for VRChat avatar work

This is a **container workspace** for AI-assisted VRChat avatar work. An agent (Claude Code) **observes** the Unity scene/project and Blender armature, **modifies** them via reviewed editor/Python scripts (or MCP), and **verifies** the result — with **Git the audit trail** for the tools and this meta-repo.

**Read first**, before any avatar work: `docs/nondestructive.md`, then `docs/workflow.md`.

## Layout

```
Atelier/                        (this folder = session cwd; workspace docs + launcher)
├─ AvatarProject/               Unity sandbox project
│  ├─ Assets/Agent/             agent I/O: Snapshots/ (durable); RunLogs/ + Scratch/ (disposable)
│  └─ Packages/                 vpm-manifest.json = source of truth; SDK payload reproducible
├─ vrc-bridge/                  Python OSC/SteamVR bridge
├─ vrc-unity-tools/             Unity editor packages (creator tools, the agent inspection harness, avatar tools)
├─ vrc-skills/                  Claude Code skills (plugin)
├─ vrc-blender-tools/           Blender extension (FBX import/prune + shape-key-safe rest-pose bake + Unity FBX export)
├─ vrc-patterns/                reusable pattern/gimmick example library (YAML-sourced VPM package; own repo)
├─ vrc-mcp-proxy/               owned stdio MCP proxy wrapping the pinned MCP-for-Unity server (allowlist + per-tool transforms)
├─ test-output/                 disposable: headless-run results/logs, gitignored + self-pruned at 30d
├─ docs/local/                  untracked working artifacts: dispatch board, coordinator state, transient briefs
└─ references/                  open-source projects we study/replicate; routing in references/README.md
```
**Two classes of sub-folder.** The `vrc-*` tool sub-repos are independent git repos (gitignored here, cloned in as siblings); `references/` holds reproducible reference clones. The **Unity projects** (`AvatarProject`, and local venues such as `Sandbox`) are **untracked working venues** — not git repos, reproducible from `vpm-manifest.json` (`vrc-get resolve`), backed up externally. Folder structure is **intentionally grown interactively** — do not impose a rigid tree.

**Run-output never lands in a tracked tooling dir.** A script that writes results or logs writes them to `test-output/`, not beside itself: a disposable pile inside `tools/` is invisible to `git status` and grows unbounded.

## Tooling stack

Per-system operating details and domain knowledge — install paths, MCP wiring, build commands, runtime behavior — live in `docs/`. Read the relevant file before operating in that domain:

- **`docs/nondestructive.md`** — How NDMF / Modular Avatar / VRCFury compose avatars non-destructively (build-on-a-clone), and the reference-hardening facts all avatar tooling depends on.
- **`docs/unity.md`** — Unity operating knowledge (always-read): MCP usage, the tool invocation/preview grammar, geometry-change reconcile, sharp edges. (Controller tooling lives in `animator.md`.)
- **`docs/unity-tools.md`** — per-tool contracts for the agent inspection harness (`agent-tools`) and the vendor→owned avatar kit (`avatar-tools`); read when driving one of those tools, alongside `unity.md`'s conventions.
- **`docs/animator.md`** + **`docs/animator-schema.md`** — animator-controller work: the tool doors (report/lint, clean/sweep/repath/own, compile/decompile + the round-trip) and the `CompileController` YAML authoring language. Read for any controller build, inspection, or round-trip.
- **`docs/blender.md`** — Blender operating knowledge: headless batch + Blender MCP usage, the `avatarprep` extension.
- **`docs/workflow.md`** — cross-system orchestration above any one tool: goals, sequencing, Unity↔Blender handoffs.
- **`docs/tool-design.md`** — the design constitution for everything agent-facing: tool interfaces, and where knowledge lives (routing ladder, managed echoes, trap-lifting, governed diagnostics). Read before adding or changing tools, skills, or any agent-directed prose.
- **`TOOLS.md`** — the system tool index: every callable across `vrc-unity-tools` / `vrc-blender-tools`. Read it to see the whole tool surface at once.
- **`docs/runtime.md`** + **`docs/gimmicks.md`** — gimmick/animator/network-sync work only: runtime (physics) then gimmicks (patterns); skip for other work.
- **`docs/verify.md`** — how to prove a claim about an avatar: the enforced play-mode gate, render evidence, emulator observation, what needs two clients or a headset. Read before verifying anything, not just gimmick work.
- **`docs/menus.md`** — expression-menu authoring on composed avatars: where menus live, the control vocabulary, toggles as dependency closures, MA-first substrate choice. Read for any menu/toggle work.
- **`docs/outfits.md`** — base-body (kisekae) clothing conventions: layered toggleable clothing meshes, the clothing↔body-blendshape coupling, and the FX controller as its authoritative map. Read before de-conflicting a base under a composed outfit.
- **`docs/LAYOUT.md`** — AvatarProject folder conventions: untouched-`Vendor/` vs. our-work split, non-Unity files outside `Assets/`.
- **`docs/bootstrap.md`** — from-zero workspace assembly: clone the sub-repos, install + wire Unity·Blender·MCP, verify. Point a fresh agent here to stand the workspace up.
- **`docs/new-project.md`** — runbook for adding another Unity project (an untracked working venue: seed the folder, VPM restore, wire the Editor). Skip in normal sessions.
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
8. **Everything here is live public.** Credit commercial and open-source ancestors by name; refer to personal projects, personas, and private avatars generically (`vrc-patterns/CONVENTIONS.md` §Provenance has the mechanics).
9. **Package source is the authority on package behavior.** Everything we build on ships its source on disk under `Packages/` — Modular Avatar, VRCFury, NDMF, the optimizers (d4rk / Limitex), the shaders (lilToon / Poiyomi). When you need precision about what one *does* — a mechanism, an edge case, an exact name — read that source and assert from it or a live measurement, never from a doc summary or your prior. Our docs orient you to where to look and the traps; they do not adjudicate your specific case.

## Writing for agents (docs, runbooks, skills, comments, handoffs)

Everything written in this workspace is read by another agent. *Where* a fact lives — the routing ladder, echoes, trap-lifting — is `docs/tool-design.md`'s to own; this section is the resident echo of the craft, whose full form is the `write-for-agents` skill.

- **The reader is you** — a model at your own capability level with the repo open. Keep only what it can't derive: decisions made, invisible constraints, traps. If a capable agent would know or do it anyway, the line dilutes the ones that matter.
- **After drafting, make a deletion pass** — remove every sentence the reader could regenerate from the artifacts. Draft-then-delete binds; "be concise" doesn't.
- **Specifics rot.** Bias version-agnostic, outcome-based instructions — point at the enforcement mechanism, not a copied value that will drift. **Update documents, don't add to them**: growing line count should reflect a larger underlying system, not accumulated amendments.
- **One line per paragraph.** No hard-wrapping — a mid-paragraph edit then diffs as one line, not a reflowed block. `tools/reflow_md.py --check` is the form meter (advisory — pre-commit reports drift, never blocks); a per-repo `.editorconfig` records the rule.
- **Omit, don't litigate.** Say what a thing *is*; frame the general rule so edge cases fall out, and simply don't build what you don't want.
- **Litigate only discipline junctures.** At a delegation seam or an irreversible act, explicit loophole closure and rationalization rebuttals earn their lines — skipped-step defects cluster exactly there; everywhere else, omit-don't-litigate stands.
- **Favor clean domain separation.** Duplicated knowledge multiplies rot surface; refactor and reorganize rather than restate.
- Capable models do their best work when given **tools and discretion** — give the outcome and the constraints, not the procedure.
- **Legibility over edge-case cleverness.** Tools are read and driven by frontier models — a tool that's intuitive to use and whose diagnostic you can *trust* beats one that silently handles a rare case but is hard to reason about.