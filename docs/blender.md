# Blender

Blender drives armature/mesh prep and the outfit-fitting pipeline. Two front doors to the same logic:
an **interactive** MCP session (collaborate live) and **headless** batch scripts (deterministic, reproducible).

Blender **5.1.2 portable** is the pipeline target — invoke by explicit path; config/addons live under
`%APPDATA%\Blender Foundation\Blender\5.1\`. **4.5.4 LTS** (Microsoft Store) is a legacy fallback only —
never `winget upgrade` it (replaces in place). **5.2 LTS** is expected to become the standard;
re-validate the pipeline when it lands. Install + MCP wiring: `bootstrap.md`.

## Headless (agent) — reproducible batch

Run scripts against a clean baseline, enabling only the addons the script needs so results don't depend
on GUI pref state:

```powershell
& "<your-blender>\blender.exe" --background --factory-startup --python <script.py>
```

`blender.exe` is GUI-subsystem — it does not block under `& exe`. Wrap in `Start-Process -Wait` (or
`Wait-Process`) when you need to block on completion.

Each launch on a full-avatar `.blend` (startup + open + save) nears the 120 s tool-timeout ceiling, so
two sequential CLI calls in one command get killed mid-write. Chain multi-step work into one `--python`
script (single launch), or background each launch.

## Interactive (collaborative) — Blender MCP

Preferred path: Blender open on a second screen with the MCP add-on enabled and its bridge started
(the `BlenderMCP` server reaches it over localhost:9876; wiring/updates: `bootstrap.md`).

- Read-only/observe: `get_objects_summary`, `get_object_detail_summary`, `get_blendfile_summary_*`,
  `search_api_docs`, `search_manual_docs`, `get_screenshot_*`.
- Mutate: `execute_blender_code` (permission-gated — prefer `bpy.ops`/`bpy.data` over raw edits, and
  inspect the scene before changing it).
- The headless `_for_cli` MCP variants time out at the server's 120s limit on this setup — use the
  `--background` invocation above for headless work, not those tools.
- If `BlenderMCP` tools are absent: Blender isn't open/connected, or Claude Code needs a restart
  (`start-vrc.ps1` is the bring-up doctor).

## avatarprep — our Blender extension

`vrc-blender-tools/` (tool **AvatarPrep**, MIT, public) reproduces the CATS avatar-prep features
still needed on Blender 5.1+ (which abandoned CATS). The callable ops are listed in the meta-repo
`TOOLS.md` (vrc-blender-tools section); this file covers how they behave, not what exists. Dual-use layout:

- `avatarprep/core/` — pure `bpy` functions the agent calls headless: `import_fbx`/`observe_import`,
  `prune_zero_weight_bones`, `apply_pose_as_rest`, `export_unity_fbx`, `armature_compat`/`merge_armatures`,
  `proportions.apply_profile`, `shapekey_bake.bake_shapekey_to_basis` (edge files live per-avatar in `Blender/Avatars/<Name>/`; the
  extension's `profiles/` holds fixtures/examples only).
- `operators.py` + `ui.py` — thin N-panel wrappers giving end users installable buttons.
- `cli/` — headless entry points.

**Code freshness — which door sees your edits.** Headless `cli/` runs the repo source directly
(`sys.path`-inserted under `--factory-startup`), so every edit is live on the next launch — no
install step. The MCP path does not: Blender loads a **built copy** installed under
`…/extensions/user_default/avatarprep/`, and Python caches the imported modules, so edits to
`vrc-blender-tools/avatarprep/` stay invisible to a running session. To run current source over MCP
without restarting, send `execute_blender_code` that `sys.path`-inserts the repo and
`importlib.reload`s the `avatarprep.core.*` modules before calling them (`core` is plain,
operator/UI-free `bpy` code — safe to import and reload). Treat the installed copy as only the
human's N-panel buttons; refreshing those needs a rebuild + reinstall and a Reload Scripts.

The structural **seam** — how two skeletons line up to be mergeable — is surfaced read-only by
`armature_compat`; like every core op, the seam ops (compat / merge / prune) are reachable both
headless via `cli/` and as N-panel buttons. This Blender **merge seam** is distinct from the Unity
**attach seam** (the MA/VRCFury component resolved at build — `nondestructive.md`); same word, different
pipeline stage, and `armature_compat` knows nothing of MA/VRCFury.

`import_fbx` runs the same under `--background` and over the windowed MCP path (it wraps the operator in
`scene_utils.op_override` only when a VIEW_3D area exists); it uses the current `wm.fbx_import` — the
legacy `import_scene.fbx` `automatic_bone_orientation` rotates some bones ~90° and corrupts bone-local
pose ops. `prune_zero_weight_bones` keeps physbone tips
(a zero-weight leaf of a weighted parent), attachment-point bones, and any weighted-descendant ancestor,
and deletes the rest. It preserves only **depth-1** zero-weight leaves — a wrongly-pruned load-bearing bone
surfaces downstream as an unresolved transplant target, not at prune time (over-pruning is unrecoverable
post-export, so it errs toward keeping).

**Shape-key facts that bite the Unity round-trip.** The FBX export writes the **value-0 Basis + morph
deltas** for geometry, **and** the current shape-key *value* as each blendshape's default weight — which Unity imports as the SMR blendshape weight (value ×100), so a Blender-set value is **visible by default and still sliderable** in Unity, not inert. Set values coherently across body + outfit meshes in Blender and they cross. The `bake_shapekey` op —
the Approach-2 finalize for proportioning, which refuses the head mesh — bakes one morph into Basis
(refreshing normals while preserving authored custom normals in a protected vertex group). Baking is
optional — it folds the morph into geometry to fix normal/shader bugs, not to avoid loss. Editing the Basis
**drags every relative shape key with it**, preserving each key's delta-from-Basis — which is why the
bake folds a morph into Basis without corrupting the other morphs' effects.

### State stamps (`avatarprep_` namespace)

Irreversible mutating ops record their trace in an `avatarprep_` custom-property namespace through one
helper (`scene_utils`). Stamps are **advisory and strippable** — Git/RunLogs are authoritative, and a
**missing stamp reads as _unknown_, not compatible**. They live **in the `.blend` only**: the Unity export
recipe omits `use_custom_props`, so nothing crosses to FBX. Two armature slots plus one mesh map:

- **`avatarprep_base`** (armature, str) — avatar **body lineage** (e.g. `shinano`). A deliberate agent
  assertion: written only through the `stamp_base` door, never parsed or guessed, and never overwritten by a
  state op. Stamp each source FBX of a multi-FBX base; the merge gate then rejects a wrong-base mismatch.
- **`avatarprep_state`** (armature, str) — proportion/shape state. `import_fbx` stamps `vendor` at ingest;
  `apply_profile` writes the `<applying>` sentinel before mutating, then the target. A stamp left at the
  sentinel is a crashed mid-apply over half-transformed geometry, so it is a **hard-FAIL**, not a soft
  unknown. Base plus `state=vendor` identifies an untouched import, so `vendor` stays a valid state.
- **`avatarprep_baked`** (mesh, `{shapekey: cumulative_value}`) — body morphs `bake_shapekey` folded into
  Basis. Reversible: the morph block is **never renamed or deleted**, and only the small body-shape-morph
  subset is ever baked. A reconciler treats a `~0` cumulative (a reversed bake) as **absent** — the block stays.

The **merge gate** (`armature_compat`) checks base and state alongside the structural seam: a mismatch,
sentinel, or corrupt value is a named FAIL; a one-sided missing stamp warns and proceeds. The override is
**split** — `force` clears structural (skeleton-doubling) offenders, `force_stamps` clears stamp offenders,
neither clears the other, and an override is logged loudly. Baked morphs are recorded but **not** gated
here — their coherence bites at compose time.

Read stamps back with **`report_stamps`**, the query counterpart of `stamp_base`: every armature's base/state
plus, grouped **under each owning armature**, its bound meshes' baked maps (meshes owned by no single
armature fall to an `unbound` bucket). It **groups; it does not collapse** — a two-armature `.blend` (e.g.
`own-mergeable`'s appended base reference) can't fuse its rigs' morphs; the collapse to one value per morph
is compose-time work (`compose-mergeable` step 5), honoring the invariant whose authority is the
`reproportion` skill (*Realizing shapekeys*) — the tool only groups. A fresh import carries `state=vendor`,
which `validate_profile` **warns-and-assumes** matches any named-source edge (a fresh piece takes a base
edge without a re-stamp); the hard-FAIL is reserved for a genuine mismatch between a non-`vendor` state
and the edge's source.
