# Bootstrap — assemble the workspace from zero

Point a capable agent here to stand up the whole Atelier workspace on a bare machine: clone the sub-repos,
install and wire the tools, verify. One-time; everyday operating knowledge lives in `unity.md` / `blender.md`,
and adding a *second* project to a working workspace is `new-project.md`. Bring-up spans three places: an
agent starts editors itself (`unity.md`), Blender runs headless (`blender.md`), and the SessionStart hook
surfaces live editors and flags a broken transport — §4 is the verify procedure.

The install steps name *what* must exist, not an OS-specific recipe — resolve the host specifics as you go.

## 1. Assemble the repos

Atelier is a container of independent git repos. Cloning the meta-repo alone gets you the docs + launcher,
**not** the tools — the sub-repos are gitignored siblings you clone into place:

```
Atelier/
├─ AvatarProject/       github.com/Ryan6-VRC/AvatarProject
├─ vrc-unity-tools/     github.com/Ryan6-VRC/vrc-unity-tools
├─ vrc-blender-tools/   github.com/Ryan6-VRC/vrc-blender-tools
├─ vrc-bridge/          github.com/Ryan6-VRC/vrc-bridge
├─ vrc-patterns/        github.com/Ryan6-VRC/vrc-patterns
├─ vrc-mcp-proxy/       github.com/Ryan6-VRC/vrc-mcp-proxy
└─ vrc-skills/          github.com/Ryan6-VRC/vrc-skills
```

The **folder names are load-bearing**: the VPM `file:` refs, `AvatarProject`'s `../../vrc-unity-tools`
package refs, and the SessionStart hook's `vrc-mcp-proxy` preflight all resolve by these exact paths. Clone
each as a sibling under `Atelier/`.

## 2. Prerequisites

Install per your host; all must exist before wiring:

- **`git` + `git-lfs`** — run `git lfs install` **before** cloning `AvatarProject`. Its VPM resolver ships
  bootstrap DLLs via LFS; without lfs they clone as ~130-byte pointer files and the resolver breaks with a
  baffling error. git must also be on PATH — Unity fetches the MCP package over a git URL.
- **Unity Hub + Unity 2022.3.22f1** — the VRChat-pinned version, never upgraded (breaks uploaded content).
  Sign in and activate a (free personal) license, or first launch stalls on a licensing modal that looks
  like the editor is "still loading" (the bridge heartbeat never goes fresh).
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

**Unity MCP.** Claude Code connects through the owned **`vrc-mcp-proxy`** (the shipped `.mcp.json` runs
`uv run --project vrc-mcp-proxy …` over **stdio**), which spawns the **pinned** upstream MCP-for-Unity
server itself and relays JSON-RPC — allowlisting tools and applying per-tool transforms. The **upstream
server pin and its bump runbook live in the proxy repo** (`docs/bump-runbook.md` there); that runbook owns
every version bump — don't chase one from here.

Per Editor, once: install the in-Editor package (CoplayDev/unity-mcp, MIT) — *Window → MCP for Unity →
Configure All Detected Clients* registers the client. Pin the Unity-side git URL to the **tag matching the
proxy's server pin** (currently `#v10.1.0`), not `#main`:
`https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#v10.1.0`. The package-update flow is unchanged
— Package Manager → *MCP for Unity* → **Update**, or delete the `packages-lock.json` entry to re-resolve.

The workspace keeps **one `UnityMCP` entry** in `.mcp.json`; route with `set_active_instance` as every
session's first Unity call (`unity.md` has the multi-Editor behavior). If registration writes a new
per-project server, collapse it back to the single entry (`new-project.md` step 6 has the policy). Ports
default from 6400 — keep each Editor's distinct. Don't switch to the http transport (`unity.md` says why).

**Roslyn for `execute_code`** (per Editor, once). `execute_code` compiles with modern C# only when the
Roslyn assemblies are present; without them it silently falls back to a C# 6 compiler. Install once per
Editor: *Window → MCP for Unity → (dependencies) → Roslyn (C# 12+ Compiler) → Install* (downloads 5 DLLs
to `Assets/Plugins/Roslyn/`). Then mark all five **Editor-only** — the installer leaves them "Any
Platform": select each DLL under `Assets/Plugins/Roslyn/`, set platform to Editor only, Apply. The payload
is gitignored — **restore per Editor, don't commit it**. Verify: any `execute_code` response's `compiler`
field reads `roslyn` (not `codedom`).

**`run_tests` is unavailable — by design.** MCP `run_tests` runs NUnit in the live Editor, the wrong
venue. The proxy's allowlist **hides `run_tests` and `get_test_job` entirely** (they never reach Claude,
and a call is refused with the venue redirect), so there is nothing to configure. Run the EditMode suite
headless via the runner below; `docs/verify.md` owns the venue rule.

**Running the EditMode suite headless.** Run `tools/setup-test-editor.ps1` once per machine — it needs
AvatarProject's VRChat SDK and the community packages the tests build as real types (Modular Avatar,
VRCFury, NDMF, Av3Emulator, Gesture Manager) already resolved (via ALCOM / `vrc-get resolve`) — to
generate the local, gitignored `TestEditor`; then
`tools/run-editmode-tests.ps1` runs the suite against it. See `docs/verify.md` for why this split
exists (the venue rule and the root cause it's built on).

**Blender MCP.** `uv tool install blender-mcp` installs the MCP **server**; wire it at local scope with your
machine's paths: `claude mcp add BlenderMCP -s local -e "BLENDER_PATH=<blender.exe>" -- <blender-mcp.exe>`.
Separately, install the **blender-mcp add-on** into Blender — this is *not* the
`avatarprep`/`vrc-blender-tools` extension — enable it, turn on **Allow Online Access**, and start its bridge
on localhost:9876. Neither half auto-updates: bump the server with `uv tool upgrade blender-mcp`, re-install
the add-on when it changes.

## 4. Verify

The **SessionStart hook** (`tools/unity-instances-hook.sh`) is the health readout: it lists live editors
and, on a main checkout, fails loud if the `vrc-mcp-proxy` sibling or `uv` is missing (zero UnityMCP).
Confirm a project actually works:

- The hook shows your editor live (or a fresh heartbeat in `~/.unity-mcp/`).
- Green bridges are **necessary but not sufficient**: the Unity bridge heartbeats even over a project full
  of compile errors. Read the console (`read_console`) for zero errors. *That* is "verified working".
- `execute_code`'s `compiler` field reads `roslyn`, not `codedom` (the C#-6 fallback — install Roslyn per §3).

MCP config written mid-session isn't live until the next launch (servers load at launch).
