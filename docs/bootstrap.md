# Bootstrap — assemble the workspace from zero

Point a capable agent here to stand up the whole Atelier workspace on a bare machine: clone the sub-repos,
install and wire the tools, verify. One-time; everyday operating knowledge lives in `unity.md` / `blender.md`,
and adding a *second* project to a working workspace is `new-project.md`. `start-vrc.ps1` is the living
bring-up doctor — run it to check or re-check health, and debug by hand only if it fails.

The install steps name *what* must exist, not an OS-specific recipe — resolve the host specifics as you go.

## 1. Assemble the repos

Atelier is a container of independent git repos. Cloning the meta-repo alone gets you the docs + launcher,
**not** the tools — the six sub-repos are gitignored siblings you clone into place:

```
Atelier/
├─ AvatarProject/       github.com/Ryan6-VRC/AvatarProject
├─ vrc-unity-tools/     github.com/Ryan6-VRC/vrc-unity-tools
├─ vrc-blender-tools/   github.com/Ryan6-VRC/vrc-blender-tools
├─ vrc-bridge/          github.com/Ryan6-VRC/vrc-bridge
├─ vrc-patterns/        github.com/Ryan6-VRC/vrc-patterns
└─ vrc-skills/          github.com/Ryan6-VRC/vrc-skills
```

The **folder names are load-bearing**: `start-vrc.ps1`, the VPM `file:` refs, and `AvatarProject`'s
`../../vrc-unity-tools` package refs all resolve by these exact paths. Clone each as a sibling under
`Atelier/`.

## 2. Prerequisites

Install per your host; all must exist before wiring:

- **`git` + `git-lfs`** — run `git lfs install` **before** cloning `AvatarProject`. Its VPM resolver ships
  bootstrap DLLs via LFS; without lfs they clone as ~130-byte pointer files and the resolver breaks with a
  baffling error. git must also be on PATH — Unity fetches the MCP package over a git URL.
- **Unity Hub + Unity 2022.3.22f1** — the VRChat-pinned version, never upgraded (breaks uploaded content).
  Sign in and activate a (free personal) license, or first launch stalls on a licensing modal and the doctor
  misreports it as "still loading".
- **Blender 5.1+ portable** under `~/Apps/blender-<ver>-windows-x64/` (the launcher auto-discovers the
  newest one there).
- **`uv`/`uvx`** — runs the MCP servers.
- **`vrc-get`** and **ALCOM/VCC** — you want both; see §3.
- **Python 3.10+** — the Unity/Blender tools, the bridge, and `dump_asset_structure.py`.
- **Claude Code** — the agent host.

## 3. Wire it

**MCP config.** The tracked `.mcp.json` carries only machine-invariant servers (currently `UnityMCP`) —
nothing to fill in. Machine-specific servers (paths, private projects) register at **local scope** instead:
`claude mcp add <Name> -s local -e KEY=VAL -- <command>` — BlenderMCP's registration is in its section below.

**VPM packages — seed the repos, then resolve.** `vpm-manifest.json` pins community packages (VRCFury,
Modular Avatar/NDMF, lilToon, Poiyomi, av3emulator, …) whose payloads are gitignored. A bare machine has only
the official VRChat repo registered, so a raw `vrc-get resolve` fails "package not found" for most of them.
**ALCOM/VCC bundles the curated community repo set** — the supported way to seed them; or `vrc-get repo add
<url>` each. Then:

```powershell
vrc-get resolve  -p .\AvatarProject      # restore packages from the manifest
vrc-get outdated -p .\AvatarProject      # list updatable
vrc-get upgrade  -p .\AvatarProject <id> # bump one
```

`vrc-get` resolves/upgrades but **cannot create** a project — `AvatarProject` already ships the skeleton, so
the clone is enough.

**Unity MCP** (per Editor, once). Package: CoplayDev/unity-mcp (MIT), git URL
`https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main`. In Unity, *Window → MCP for Unity →
Configure All Detected Clients* registers the client. The workspace keeps **one `UnityMCP` entry in
`.mcp.json`, deliberately without `--default-instance`** — no pin is trustworthy: the server does not
error on multi-Editor ambiguity, and unpinned calls silently land on an arbitrary Editor, so the only
reliable routing is `set_active_instance` as every session's first Unity call (live `Name@hash` values
in the `mcpforunity://instances` resource; the hash is path-derived and changes when a project moves
or renames). If registration writes a pin or a new per-project server, collapse it back to the single
entry (`new-project.md` step 6 has the policy). Ports default from
6400 — keep each Editor's distinct. Transport is **stdio**
(Claude launches `uvx mcp-for-unity`, which brokers to the Editor's bridge across domain reloads); don't
switch to the http transport (`unity.md` says why). The git package is frozen to a commit in
`packages-lock.json` (`#main` doesn't auto-track) — update via Package Manager → *MCP for Unity* → **Update**,
or delete its lock entry to re-resolve.

**Roslyn for `execute_code`** (per Editor, once). `execute_code` compiles with modern C# only when the
Roslyn assemblies are present; without them it silently falls back to a C# 6 compiler. Install once per
Editor: *Window → MCP for Unity → (dependencies) → Roslyn (C# 12+ Compiler) → Install* (downloads 5 DLLs
to `Assets/Plugins/Roslyn/`). Then mark all five **Editor-only** — the installer leaves them "Any
Platform": select each DLL under `Assets/Plugins/Roslyn/`, set platform to Editor only, Apply. The payload
is gitignored — **restore per Editor, don't commit it**. Verify: any `execute_code` response's `compiler`
field reads `roslyn` (not `codedom`).

**`run_tests` is blocked — leave it that way.** MCP `run_tests` runs NUnit in the live Editor, the wrong
venue; a tracked `PreToolUse` hook in `.claude/settings.json` denies it and redirects to the headless
runner. Its `mcp__UnityMCP.*__run_tests` matcher covers every UnityMCP Editor, current and future. It
ships with the clone — no setup, just don't remove it. (Hooks load at launch, so it's live from the
next session, not mid-session.)

**Running the EditMode suite headless.** Run `tools/setup-test-editor.ps1` once per machine — it needs
AvatarProject's VRChat SDK already resolved — to generate the local, gitignored `TestEditor`; then
`tools/run-editmode-tests.ps1` runs the suite against it. See `docs/verify.md` for why this split
exists (the venue rule and the root cause it's built on).

**Blender MCP.** `uv tool install blender-mcp` installs the MCP **server**; wire it at local scope with your
machine's paths: `claude mcp add BlenderMCP -s local -e "BLENDER_PATH=<blender.exe>" -- <blender-mcp.exe>`.
Separately, install the **blender-mcp add-on** into Blender — this is *not* the
`avatarprep`/`vrc-blender-tools` extension — enable it, turn on **Allow Online Access**, and start its bridge
on localhost:9876. Neither half auto-updates: bump the server with `uv tool upgrade blender-mcp`, re-install
the add-on when it changes.

## 4. Verify

Run `start-vrc.ps1` — it launches Unity + Blender, waits for both MCP bridges, and reports health. It also warns (non-fatal) when a project lacks the Roslyn DLLs — `execute_code` would fall back to C# 6. Green
bridges are **necessary but not sufficient**: the Unity bridge heartbeats even over a project full of compile
errors. Confirm a clean build too — once the bridge is up, read the Unity console (`read_console`) and check
for zero errors. *That* is "verified working".

MCP config written mid-session is not live in that session (servers load at launch), so verify through the
doctor's ports/heartbeat — the MCP tools you just wired come online on the next launch, not now.
