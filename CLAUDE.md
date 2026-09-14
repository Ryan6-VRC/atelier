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
**Two classes of sub-folder.** The `vrc-*` tool sub-repos are independent git repos (gitignored here, cloned in as siblings); `references/` holds reproducible reference clones. The **Unity projects** (`AvatarProject`, plus any local venues you add) are **untracked working venues** — untracked by *this* repo, each carrying a local-only git repo of its own over hand-authored text (`docs/LAYOUT.md` §Principles owns the ruleset), reproducible from `vpm-manifest.json` (`vrc-get resolve`), backed up externally; a venue you add is yours alone, so ignore it in `.git/info/exclude` and never name it in tracked code. Folder structure is **intentionally grown interactively** — do not impose a rigid tree.

**Run-output never lands in a tracked tooling dir.** A script that writes results or logs writes them to `test-output/`, not beside itself: a disposable pile inside `tools/` is invisible to `git status` and grows unbounded.

## Tooling stack

Per-system operating details and domain knowledge — install paths, MCP wiring, build commands, runtime behavior — live in `docs/`. Read the relevant file before operating in that domain:

- **`docs/nondestructive.md`** — how NDMF / Modular Avatar / VRCFury compose on a clone, and the reference-hardening every avatar tool depends on. Always-read before avatar work.
- **`docs/unity.md`** — Unity operating knowledge; always-read. Controller tooling is `animator.md`'s.
- **`docs/unity-tools.md`** — per-tool contracts for `agent-tools` and `avatar-tools`. Read when driving one, alongside `unity.md`.
- **`docs/animator.md`** + **`docs/animator-schema.md`** — read for any controller build, inspection, or round-trip; the second is the `CompileController` YAML authoring language.
- **`docs/blender.md`** — Blender operating knowledge; read for any mesh or armature work.
- **`docs/workflow.md`** — which skill a task routes to, how tasks hand off, and the Unity↔Blender seam.
- **`docs/dispatched-work.md`** — read when a launch prompt or pasted block points you at it.
- **`docs/tool-design.md`** — read before adding or changing a tool, a skill, or any agent-directed prose.
- **`TOOLS.md`** — the tool index; read to see the whole callable surface at once.
- **`docs/runtime.md`** + **`docs/gimmicks.md`** — gimmick/animator/network-sync work only: runtime (physics) then gimmicks (patterns); skip for other work. Exception: `gimmicks.md` §Packaging owns `globalParams` for any VRCFury `FullController`.
- **`docs/optimization.md`** — read for any rank or budget work, and before composing to a stated rank line.
- **`docs/verify.md`** — read before proving any claim about an avatar, not just gimmick work.
- **`docs/emulator.md`** — read before driving any play session.
- **`docs/vrchat-client.md`** — read when a claim needs the shipping client.
- **`docs/osc.md`** — read for any rig driven or read over OSC; `vrc-bridge` keeps its own design record.
- **`docs/menus.md`** — read for any menu or toggle work.
- **`docs/outfits.md`** — base-body (kisekae) clothing conventions. Read before de-conflicting a base under a composed outfit, and before dropping or baking down any layer a base's own FX drives.
- **`docs/LAYOUT.md`** — venue conventions, **§Vendor mutation** enumerating where a write under `Vendor/` is sanctioned. Read before creating, filing, or writing any asset in a venue.
- **`docs/bootstrap.md`** — point a fresh agent here to stand the workspace up.
- **`docs/new-project.md`** — adding another Unity venue; skip in normal sessions.
- **`references/README.md`** — routing table of open-source projects we learn from.

## Rules

1. **Observe before changing.** Read the current state first: exports, callers, shared utilities, scenes, prefabs, Blender files, generated assets, and known-good examples. Do not rewrite what you do not understand.
2. **Simplicity first.** Make the smallest change that solves the requested problem. No features beyond what asked, no abstractions for single-use code. If a senior engineer would call it overcomplicated, simplify.
3. **Prefer deterministic edits.** Use generated scripts, editor tools, Git diffs, and checkpoints over raw asset/YAML edits or opaque write operations.
4. **Examples and tested patterns are ground truth.** When patterns conflict, choose the more recent, more tested, or more local example; say why, and flag the discarded pattern. Do not average incompatible approaches.
5. **Verify intent, not just output.** Tests, scene checks, import checks, and diagnostics should prove the reason the behavior matters. A check that still passes after breaking the business or asset logic is wrong.
6. **Checkpoint after significant steps.** Summarize what changed, what was verified, and what remains. Do not continue from a state you cannot describe back.
7. **Fail loud.** "Done" is wrong if anything was skipped silently. Surface uncertainty, missing inputs, and named offenders.
8. **Everything here is live public.** Credit commercial and open-source ancestors by name; refer to personal projects, personas, and private avatars generically (`vrc-patterns/CONVENTIONS.md` §Provenance has the mechanics).
9. **One agent drives Unity at a time, reads included.** Every fork and subagent shares the session's single MCP connection and the one mutable venue behind it, so concurrent Unity work silently re-routes pins and interleaves edits neither side can see. Delegate Unity work only to one foregrounded subagent at a time (`run_in_background: false`, never a parallel fan-out), making no Unity calls yourself until it returns — then re-pin, since its `set_active_instance` outlives it. Batch mode (`batch-venue-work`) is the carve-out: unlimited subagents against one Editor, over disjoint buckets, nobody in play.
10. **Package source is the authority on package behavior.** Everything we build on ships its source on disk under `Packages/` — Modular Avatar, VRCFury, NDMF, the optimizers (d4rk / Limitex), the shaders (lilToon / Poiyomi). When you need precision about what one *does* — a mechanism, an edge case, an exact name — read that source and assert from it or a live measurement, never from a doc summary or your prior. Our docs orient you to where to look and the traps; they do not adjudicate your specific case.
11. **A lean is not a constraint.** The operator's "I'd rather", "I favour", "probably X" is a weighted preference: carry it forward as a preference, with the weight it was given, and keep the option space open. Only a stated rule, a written spec, or an explicit "must"/"never" binds. When you relay or brief work for another agent, quote the operator's framing rather than restating it; a preference rewritten as a rule combines with the next rule into a deadlock nobody asked for, and the agent holding it stops searching. If you notice you have hardened one, say so and unwind it.

## Writing for agents (docs, runbooks, skills, comments, handoffs)

Everything written in this workspace — docs, skills, comments, handoffs, diagnostic strings — is read by another agent: a model at your own capability level with the repo open.

*Where* a fact lives — the routing ladder, echoes, trap-lifting, the governed fence — is `docs/tool-design.md`'s to own.

*How* the sentences get made is the `write-for-agents` skill (`.claude/skills/`) — invoke it for any agent-read prose, including diagnostics in code and markdown the hook can't see (Bash-written files); the hook routes you on Write/Edit of `.md`.

Form: one line per paragraph, no hard wrap — `tools/reflow_md.py --check` is the meter (advisory), and a per-repo `.editorconfig` records the rule.
