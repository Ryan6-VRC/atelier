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
  `search_api_docs`, `get_screenshot_of_window_as_image`.
- Mutate: `execute_blender_code` (permission-gated — prefer `bpy.ops`/`bpy.data` over raw edits, and
  inspect the scene before changing it).
- The `_for_cli` MCP variants are deny-hidden (they time out at the server's 120s limit on this
  setup) — headless work uses the `--background` invocation above.
- If `BlenderMCP` tools are absent: Blender isn't open/connected, or Claude Code needs a restart
  (`start-vrc.ps1` is the bring-up doctor).

## avatarprep — our Blender extension

`vrc-blender-tools/` (tool **AvatarPrep**, MIT, public) reproduces the CATS avatar-prep features
still needed on Blender 5.1+ (which abandoned CATS). The callable ops are listed in the meta-repo
`TOOLS.md` (vrc-blender-tools section); this file covers how they behave, not what exists. Dual-use layout:

- `avatarprep/core/` — pure `bpy` functions the agent calls headless: `import_fbx`/`observe_import`,
  `prune_zero_weight_bones`, `apply_pose`, `export_unity_fbx`, `compare_armatures`/`merge_armatures`,
  `proportions.apply_proportion_edge`, `shapekey_bake.bake_shapekey_to_basis` (edge files live per-avatar in `Blender/Avatars/<Name>/`; the
  extension's `edges/` holds fixtures/examples only).
- `operators.py` + `ui.py` — thin N-panel wrappers giving end users installable buttons.
- `cli/` — headless entry points.
- **Mesh-state visual capture** is headless too: the `render_mesh` cli (`--background`, Workbench render
  to a stamped contact-sheet PNG the agent reads — solid or vertexcolor, named world-axis angles) gives
  back the deterministic render the denied `render_*_to_path` MCP tools removed, for mesh reads and the
  RBT vertex-color marker. It covers mesh-state contact sheets, not the live UI/viewport inspection that
  `get_screenshot_of_window_as_image` still serves.

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
`compare_armatures`; like every core op, the seam ops (compat / merge / prune) are reachable both
headless via `cli/` and as N-panel buttons. This Blender **merge seam** is distinct from the Unity
**attach seam** (the MA/VRCFury component resolved at build — `nondestructive.md`); same word, different
pipeline stage, and `compare_armatures` knows nothing of MA/VRCFury.

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
helper (`scene_utils`). Stamps are **advisory and strippable** — Git/RunLogs are authoritative. A
**missing stamp reads as _unknown_, not compatible** — at the runtime merge/compose gate that means
warn-and-proceed; at filing or fit time (`own-mergeable`, `compose-mergeable`) it means ask the operator,
write the stamp back, and refile. They live **in the `.blend` only**: the Unity export recipe omits
`use_custom_props`, so nothing crosses to FBX. **Three independent axes, one writer each** — two on the
armature, one on meshes. Each stays in its lane: base is body lineage, state is proportion state, baked is
folded morphs — a profile transitions the `(base, state)` pair; the axes don't leak into each other.

- **`avatarprep_base`** (armature, str) — lineage of an avatar **or a mergeable** (the owned base an
  outfit was fitted to; e.g. `shinano`). A deliberate agent assertion, never parsed or guessed:
  **created** by `stamp_base`, then **transitioned only by a profile's `target_base` along a gated
  edge** — a pure reproportion re-asserts it unchanged, an equivalency edge moves it to a topo-equivalent
  base. Stamp each source FBX of a multi-FBX base; the merge gate then rejects a wrong-base mismatch.
  `compose-mergeable` resolves-and-reads it to gate an owned outfit's fit against the target base.
- **`avatarprep_state`** (armature, str) — proportion state. `import_fbx` stamps the reserved origin
  **`unproportioned`** at ingest (a fresh import is, by definition, unproportioned; state values are
  base-neutral — `custom`, not `custom_shinano`). `apply_proportion_edge` writes the `<applying>` sentinel before
  mutating, then the target. A stamp left at the sentinel is a crashed mid-apply over half-transformed
  geometry, so it is a **hard-FAIL**, not a soft unknown. The guard exact-matches a profile's edge against
  both axes — `state == source_state` and `base == source_base` — and **base absent at apply is an
  offender** ("stamp_base first"); state absent still only warns-and-assumes.
- **`avatarprep_baked`** (mesh, `{shapekey: cumulative_value}`) — body morphs `bake_shapekey` folded into
  Basis. Reversible: the morph block is **never renamed or deleted**, and only the small body-shape-morph
  subset is ever baked. A reconciler treats a `~0` cumulative (a reversed bake) as **absent** — the block stays.

A profile is a typed edge `(source_base, source_state) → (target_base, target_state)`. On success,
`apply_proportion_edge` writes `avatarprep_base` (`target_base`) **then** `avatarprep_state` (`target_state`) —
state last, since it carries the crash sentinel. **Equivalency** profiles — identity no-op for a shared
body, or pure-scale for a rescaled-identical one — are a first-class edge kind that changes only base.
**mochifitter** (roadmap, not built) owns the future *non-topo* mesh-retarget case a transform can't
reach; topo-preserving base changes stay profiles.

The **merge gate** (`compare_armatures`) — the **Blender structural merge gate** — checks base and state
alongside the structural seam: a mismatch, sentinel, or corrupt value is a named FAIL; a one-sided missing
stamp warns and proceeds. It is distinct from the **Unity `compose-mergeable` stamp/fit gate**, which
compares an owned mergeable's `(base, state)` against the target base at compose time (see
`nondestructive.md`). The override here is **split** — `force` clears structural (skeleton-doubling)
offenders, `force_stamps` clears stamp offenders, neither clears the other, and an override is logged
loudly. Baked morphs are recorded but **not** gated here — their coherence bites at compose time.

Read stamps back with **`report_stamps`**, the query counterpart of `stamp_base`: every armature's base/state
plus, grouped **under each owning armature**, its bound meshes' baked maps (meshes owned by no single
armature fall to an `unbound` bucket). It **groups; it does not collapse** — a two-armature `.blend` (e.g.
`own-mergeable`'s appended base reference) can't fuse its rigs' morphs; the collapse to one value per morph
is compose-time work (`compose-mergeable` step 5), honoring the invariant whose authority is the
`reproportion` skill (*Realizing shapekeys*) — the tool only groups. A fresh import carries
`state=unproportioned` and no base stamp yet; `apply_proportion_edge --whatif` **exact-matches** state, so a named-source
edge applied to an `unproportioned` rig is now an offender — the old vendor-matches-any-source wildcard is
gone. Apply `stamp_base` first, or route through a profile whose source is genuinely `unproportioned`; the
hard-FAIL is reserved for a stamp left mid-apply at the sentinel or a genuine state mismatch.
