# Unity

`AvatarProject/` is the sandbox Unity project (its own Git repo). Unity **2022.3.22f1**, VRChat-pinned —
never upgrade (breaks uploaded content).

Packages are VPM-managed and reproducible (constraints: workspace `CLAUDE.md`; commands: `bootstrap.md`).

## Unity MCP

Transport is stdio; Claude Code connects through our **`vrc-mcp-proxy`** (sibling repo), which pins and
spawns the upstream MCP-for-Unity server and owns the tool allowlist plus known-lie corrections — a
`[vrc-mcp-proxy]` note or refusal in a tool result comes from that layer (its README lists the behaviors).
The server brokers to each Editor's bridge across recompiles/domain reloads. Registration, transport,
and package-update wiring: `bootstrap.md`.

- Read editor state via **resources** (`mcpforunity://editor/state`, `project_info`, …); perform
  mutations via **tools** (`manage_scene`, `manage_gameobject`, … — permission-gated) or `execute_code`.
- After creating/editing scripts, check `read_console` for compile errors before using new types
  (poll `editor_state.isCompiling` for the domain reload).
- The one `UnityMCP` server reaches every local Editor. With **2+ Editors connected and no pin it
  hard-errors, naming the instances**; a **single** Editor auto-selects. Still make
  `set_active_instance` with the **full** `Name@hash` the first Unity call of every session — the
  reliable way to pin routing for the whole session. The live instance table is injected into session
  context at start (SessionStart hook → `tools/unity-instances-hook.sh`); also queryable via the
  `mcpforunity://instances` resource. Hashes are path-derived cache keys — read them live, never
  copy them into docs or config.
- If `UnityMCP` tools are absent: the Editor isn't open on `AvatarProject`, or Claude Code needs a
  restart (`start-vrc.ps1` is the bring-up doctor).
- **Trust the heartbeat, not the MCP window.** The Editor's *MCP for Unity* window can show "No Session"
  while the stdio bridge is up — a cosmetic desync; the `~/.unity-mcp/` heartbeat (what `start-vrc.ps1`
  reads) is truth.
- **Never switch to the Editor-hosted http transport.** It drops on every domain reload, and its toggle
  (`MCPForUnity.UseHttpTransport`) is a **machine-global** EditorPref shared by every project on this
  Editor version — flipping it hits all of them on the next restart.

## Agent-callable tools

The agent inspection harness (`agent-tools`) and the vendor→owned avatar kit (`avatar-tools`) are the
static-method tools you call via `execute_code`; their per-tool contracts live in **`docs/unity-tools.md`**
(read it before driving one). The two conventions every one of them shares stay here, since they govern
how the whole surface is invoked:

**Invocation.** Every door in the `agent-tools` and `avatar-tools` kits is a `public static` method called
via `execute_code` with **string** handles — GameObject hierarchy paths, asset paths, never object refs.
Namespaces: agent-tools under **`Ryan6Vrc.AgentTools.Editor`**, avatar-tools under
**`Ryan6Vrc.AvatarTools.Editor`** — but the **assembly** capitalizes the acronym (`Ryan6VRC.…Editor`),
so an assembly-qualified reflection lookup uses `Ryan6VRC` while the type namespace is `Ryan6Vrc`.

**Preview grammar.** Every mutating tool takes a default-off preview: **`whatIf`** when the tool can run
its full plan and mutate nothing (preview == execute — `CopyComponents`/`MoveComponents`/`GraftHierarchy`
/`ConformRenderers`/`CopyDescriptor`/`FixViewpoint`, and the animator-doc owning tools), or **`preflight`** when the operation can't be
dry-run at all and only its preconditions are checkable (`MatchHumanoidRig`, whose reimport *is* the
operation). The dividing line is *ran the plan and mutated nothing* vs *couldn't run the op at all* — not
complete-vs-incomplete numbers (so `CopyDescriptor` stays `whatIf` even though its remap counts land only on
execute).

## Geometry-change reconcile (reproportion / re-export)

Changing avatar geometry leaves Unity-side state stale — it holds frozen references or meters that do
**not** track the new geometry. The `reproportion` skill sequences this; the durable facts:

- **Humanoid bind.** Frozen into the FBX `.meta` at rig time; it does not self-update. **Re-run
  `MatchHumanoidRig` after any geometry change** or the bind disagrees with the bones (folded hips);
  `CheckHumanoidRig` verifies it.
- **ViewPosition** (eye height) is an avatar-local **meters** vector — recompute on any height change or
  the viewpoint floats off the eyes (not sub-notice).
- **Absolute component dimensions** — physbone / collider / contact radii are meters; they don't scale
  with a rescale (drift linear in magnitude, negligible at small reproportions).
- **Prefab-persisted SkinnedMeshRenderer blendshape weights unlink (reset to 0) when a mesh is renamed
  or re-exported** — re-verify driven weights, and keep them coherent across meshes (an outfit's
  matching morph is often name-variant, e.g. `Bra_Breasts_big` ↔ `Breasts_big`). A Blender shape-key
  *value* crosses as the imported blendshape weight (see `blender.md`); body-shape morphs can be set in Blender or here, kept coherent across meshes — the one-value-per-morph coherence invariant is the `reproportion` skill's (*Realizing shapekeys*).

## Non-destructive avatar build

Modern avatar tooling — Modular Avatar (on NDMF), VRCFury, the **d4rk Avatar Optimizer**, the
**Limitex (LAC) texture compressor** — is **non-destructive**: the components do nothing to the editor
scene and rebuild a throwaway copy at Play/upload. They **stack freely on an untouched vendor asset**,
and none deep-copies meshes or textures — add them, don't bake them in. This is what makes a vendor
prefab safe to drop optimizers onto, and what lets animator controllers be merged without editing them.
(There's no Add-Component menu over MCP — discover a tool's exact component type with an `AppDomain`
`MonoBehaviour` scan: e.g. `d4rkAvatarOptimizer`, `dev.limitex.avatar.compressor.TextureCompressor`,
VRCFury features under `VF.Model.Feature.*` held by a `VF.Model.VRCFury` component.)

Validate the baked result without uploading: **enter play mode** — it runs the *whole* stack
(VRCFury services + NDMF/MA + d4rk + LAC) on the transient play copy, removed on exit. One session
is both the baked read (the built clone + `VRCFuryDebugInfo`) and the live drive (av3emulator).
The **play-entry gate** is enforced on entry; `verify.md` owns the preconditions and the emulator recipes.

## Sharp edges

- **Bridge "Connection closed" on the first call** after the Editor's been idle or just reloaded —
  retry once; it reconnects.
- **`execute_code` is async-blind.** `AssetDatabase.ImportPackage(path, false)` returns before the
  import finishes — verify the asset/folder exists in a separate call before chaining dependent ops.
- **`execute_code` `safety_checks` blocks destructive patterns** (`AssetDatabase.DeleteAsset`,
  `File.Delete`, `Process.Start`, loops). Pass `safety_checks=false` for a narrowly-scoped,
  confirmed-intentional one.
- **Editing asset/package files outside Unity** leaves the asset DB stale ("Build asset version
  error"); clear the console + `refresh_unity` (mode=force, scope=all).
- **Scene creation over `execute_code` is `NewSceneMode`, not `NewSceneSetupMode`**; `manage_scene create`
  emits an **empty** scene — the server's "always include a Camera and main Light" instruction is fiction.
- **`manage_asset search` scoped to a nonexistent path silently returns *global* results** (not empty or
  an error) — verify the scope path exists, or read every hit's path.
- **`AssetDatabase.MoveAsset` leaves the drained wrapper folder inconsistently** — self-cleaned in some
  cases, lingering until a later `STRUCTURE.md` regen / refresh in others. Re-list the destination after
  every relocate rather than assuming either.
- **Vendor GameObject names carry trailing spaces** (`"Menu "`, `"Ears "`) that silently break exact-path
  lookups (`transform.Find` / `GameObject.Find`) — copy the name from an inspector dump, or match by
  trim/`StartsWith`, rather than retyping it.
- **VRCFury's first build of an avatar lacking a "Fix Write Defaults" component pops a blocking
  dialog** that stalls the build waiting for a click. Hard-check before any build; if absent, add
  the VRCFury Fix Write Defaults component with mode **Disabled** (suppresses the prompt, changes
  nothing).
- **FBX external-material remap (`materialLocation: External`) applies only at import time.** A model
  imported before its `.mat` targets exist (costume package before a separate MaterialPack) caches
  empty slots that no later import re-triggers — force-reimport the FBX. `CheckPackage` flags it; the
  `import-vendor-asset` skill owns the procedure.
- **Reparenting a prefab instance's internal children silently no-ops.** `Transform.SetParent` on an
  object owned by a prefab instance reverts with no error — restructure before prefab conversion, or
  edit the asset via `PrefabUtility.LoadPrefabContents`. Verify by `childCount`, not `SetParent` calls.
- **The play-entry gate is enforced in-Editor** — the `PlayGate` hook cancels a mis-set entry with a
  console `[PlayGate] … => FAIL` (each offender + its fix) and a one-shot override; see `verify.md`.
  Entering play **blocks the Editor main thread while the non-destructive build runs**
  (NDMF/VRCFury/d4rk/LAC): `editor_state` freezes and reads can time out for ~minutes on a heavy
  avatar. `execute_code` issued during it **queues and returns once the build frees the thread** — don't
  read the delay/timeout as failure. Batch play-mode work; re-entering play re-runs the whole build.
- **`Unity.exe` is GUI-subsystem and does not block under `& exe`** — use `Start-Process -Wait` for
  headless batchmode runs.
- **Driving Av3Emulator in play mode: read params via the `LyumaAv3Runtime` `Floats/Ints/Bools` lists,
  never `Animator.Get*`.** The emulator drives its own `PlayableGraph`, so the base `Animator`'s
  parameter dictionary reads empty; observe outputs through those lists, scene transforms/blendshapes,
  or `ContactReceiver.paramValue`/`IsColliding()`. Frames advance only *between* `execute_code` calls.
