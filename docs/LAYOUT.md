# AvatarProject layout & conventions

Where things go in the Unity sandbox. The act of importing a vendor package — file selection,
gates, relocate/verify — is the **`import-vendor-asset`** skill; this doc only defines where the
result lands and why.

## Untouched vs. our work

- **`Assets/Vendor/`** — vendor imports kept as-dropped, hand-edited only for the sanctioned
  reconstructions under *Vendor mutation* below (`Vendor/Avatars/<Name>/`, `Vendor/Outfits/<Outfit>/`,
  and `Vendor/_Common/` for assets shared across a seller's packages).
  **Gitignored**, reproducible by re-importing the source `.unitypackage` from the **asset library** —
  the external store of vendor packages; its location is machine-local (`CLAUDE.local.md`), never
  written into tracked files. Our work references vendor assets **by GUID, not path**, so tracked work survives
  a bare re-import even though a package re-imports to its own native top folder. A **patched** vendor
  asset is the exception — it reproduces only with its patch replayed (*Vendor mutation* below).
- **Everything else under `Assets/`** — our work (prefab variants, scenes, animators, materials).
  Tracked. No `Work/` wrapper.
- **Git tracks diffable text, not large binaries.** It versions what diffs cleanly — YAML
  (scenes/prefabs/materials), `.meta`, `.json`, scripts. Art/source binaries (`.fbx` `.blend` `.psd`
  `.png`, audio) don't diff and bloat history + LFS quota, so:
  - they're **gitignored**, but each keeps its `.meta` (GUID + import settings) so references resolve
    and a re-exported file rebinds;
  - RunLog JSON is gitignored too — disposable per-run diagnostics, not a durable artifact; LFS
    stays only for the VPM bootstrap DLLs;
  - since binaries live outside Git, **back them up externally** — a fresh clone has no
    meshes/textures until they're restored or re-exported.
- **Owning is selective.** An owned asset tracks only what it actually changed and keeps
  **GUID-referencing the vendor original** for everything it didn't — an owned base can still point
  at vendor animator layers or materials it never customized. Provenance is a property of each
  *reference*, not of a folder.
- **A top-level avatar folder holds full prefabs, not loose parts.** `Assets/Avatars/<Name>/` (like
  `Assets/Outfits/<Base>/<Outfit>/`) is essentially only complete prefabs; owned controllers, clips, and
  params live in **subfolders**. This is the on-disk half of *owned = wired* (`animator.md`): a
  properly-owned set is both wired to its load path and filed out of the top level. Convention, not a tool.
- **`Assets/Vendor/` and `Packages/` are read-only to our tooling.** A tool that would mutate an asset
  there must **materialize an owned copy first**; writability is judged **per-asset, by path** (an owned
  controller may still reference a vendor clip — that clip stays read-only). This is a **policy** guard on
  *deliberate* edits, not a byte contract: it means fork-before-you-change (a `force` override records any
  breach loudly), not that vendor bytes never move — VPM restores and importer migrations rewrite
  `Vendor/`/`Packages/` on disk with no agent and no breach (see *Vendor mutation*).
- **`Assets/Materials/<Avatars|Outfits>/<Name>/`** — owned materials and their exported textures,
  mirroring `Photoshop/` by name. Base-independent like the PSD art (texture work doesn't change with
  proportions), so one bucket serves every base wearing the outfit — but when the geometry is *also*
  owned, materials file with it (`Assets/Outfits/<Base>/<Outfit>/Materials/`) instead: one logical
  asset, one home. Copy semantics (selective slot forking, shader handling) are the `own-material`
  skill's.
- **Non-Unity source files live outside `Assets/`** at the project root, so editing them never
  triggers an editor refresh:
  - **`Blender/Avatars/<Name>/`** — the `<Name>.blend` source, namespaced like `Assets/`; also holds
    the **proportion profiles** the reproportion skill reads/writes (see below).
  - **`Blender/Outfits/<Base>/<Outfit>/<Outfit>.blend`** — owned outfits go **base-first**: the base
    you fitted to is held constant, the outfit varies underneath it (file by the axis held constant —
    `Vendor/Outfits/<Outfit>/` stays **outfit-first**, since a vendor product's base varies *inside*
    one package). The exported `.fbx` mirrors this at `Assets/Outfits/<Base>/<Outfit>/Models/` (Unity
    imports only under `Assets/`, **not** here); outfit folders carry no proportion profile of their
    own (see below). One outfit fitted to two bases is **two buckets, two `.blend`s** — duplication
    accepted for clarity, no cross-base sharing.
  - **`Photoshop/Avatars/<Name>/`** and **`Photoshop/Outfits/<Outfit>/`** — `.psd` source art, kept
    **outfit-first** (no `<Base>` segment) unlike the owned Blender/Assets trees above — reproportioning
    is geometry-only, so PSD art is base-independent and the outfit is the constant. A PSD is only
    worth bringing over if we intend to modify it (the package already ships the untouched PNG
    exports), so PSDs are *our* work, not vendor — no `Vendor/` namespace. Gitignored like all
    binaries (above) and kept under external backup. What enters Unity from a PSD is a **flattened
    PNG export** into the owned-materials bucket — the `.blend` → `.fbx` contract mirrored; an
    *owned* material referencing a `.psd` inside `Assets/` is a defect (a vendor material linking
    its own shipped PSD is vendor authoring, untouched until owned).

## Vendor mutation: patch, copy-on-write, importer drift

"Untouched `Vendor/`" is the default, not an invariant — content legitimately changes without
being tampering, so the rule is **sanctioned mutation, marked**:

- **A vendor's own patcher never patches the base in place.** Some DLCs ship a binary patcher
  (`hpatchz` + `.hdiff`) that rewrites a base FBX so a variant prefab referencing it by GUID picks
  up the new mesh. In-place is the vendor's design, not ours — it destroys the original, and a later
  base re-import silently reverts it and breaks the variant with nothing recording a patch ran.
  Extend the copy-on-write rule above to cover it: **reconstruct the parallel-patched layout a
  careful vendor would ship** — patch a **copy** of the base FBX placed as a sibling in the package,
  and repoint the DLC's own variant prefab(s) to that copy (a whole-GUID swap in the prefab YAML;
  sub-asset fileIDs survive a copy, so mesh and avatar references move together). The base FBX and
  the base package's own prefabs stay byte-identical; vanilla and variant coexist. A DLC that already
  ships a parallel patched folder needs no reconstruction. The **three sanctioned edits** — patched
  copy, provenance sidecar, repointed variant prefab — are the enumerated exception to "never nest
  our own structural decisions deeper inside `Vendor/`" (below): sanctioned agent edits, not a claim of
  non-interference. Procedure: the `import-vendor-asset` skill's *Patch a vendor-mutated asset*.
- **Provenance travels with the patched copy.** A sidecar records the replay recipe — patcher,
  `.hdiff`, source FBX (path + GUID), output, date. Like everything in `Vendor/` it is **gitignored**
  (not in the audit trail; restored from external backup, not Git); its job is to catch a base
  re-import that reverted the patch. A patched-variant package reproduces by re-running the import on
  the base + DLC packages, or restoring `Vendor/` from backup — never by re-importing the base alone,
  which restores vanilla only.
- **Benign in-place drift is not tampering.** lilToon rewrites a vendor `.mat` at import
  (`_lilToonVersion` bump + new default props) with no agent acting. A vendor-integrity check protects
  *intent*, not *bytes*.

## Proportion profiles & state naming

Reproportioning edges (JSON) are **co-located per avatar** in `Blender/Avatars/<Name>/`; the shared
`vrc-blender-tools/edges/` is a **curated, shipped sample library** (migrated edges plus known
base-equivalency samples), not examples/fixtures. A profile is a **typed edge** `(source_base,
source_state) → (target_base, target_state)`, authored against one rig's literal bone names, so it is
owned by the avatar it targets. **Outfits have no proportion-edge JSON of their own** — an outfit is
fitted to a (re)proportioned avatar by applying that **avatar's** edge to the outfit's armature. That
doesn't mean an outfit's base is unknown, though: its lineage is separately stamped as `avatarprep_base`
on the outfit's own armature.

State names are **stamped onto the armature** (`avatarprep_state`) and travel with the `.blend`; they are
**never exported to FBX** (the export recipe omits `use_custom_props`). `apply_proportion_edge --whatif` reads them **in
Blender**, before apply, exact-matching both the state and the separate `avatarprep_base` stamp — an
absent base is an **offender** (stamp it first), an absent state only warns:
- **State values are base-neutral.** `custom` is the correct target state, not `custom_shinano` or
  `plum-tall` — body identity belongs to the `avatarprep_base` stamp, never the state label.
- **`unproportioned`** is the one reserved generic (the as-imported origin state; replaces the old
  `vendor` word, which conflated provenance with shape).
- **Filenames may carry the base the state value doesn't**, in two cases: a **reproportion** (same
  base) is named for its target config — `custom_shinano.json` (target state + base, for legibility);
  a **base-change/equivalency** is named `<source_base>-to-<target_base>.json` — `plum-to-chiffon.json`.

The folder tree above is for **browsing**; the authoritative provenance is always the `(base, state)`
stamp in the **mirrored `.blend`** (see below). If a stamp is missing at filing or fit time, the fix is
to ask the operator, write the stamp back, and refile into the correct base bucket — that loop lives in
the `own-mergeable` skill, not here.

`avatarprep_state` is one axis of a three-axis base/state/baked model; its behavior (and the
`avatarprep_base`/`avatarprep_baked` axes) lives in `blender.md`.

## gitignore note

The stock `!/[Aa]ssets/**/*.meta` un-ignore is load-bearing in two directions:
- It **keeps** the `.meta` of gitignored **binaries** (we ignore `*.fbx`, not `*.fbx.meta`) — that's
  what lets tracked refs resolve.
- Rules that must **drop** metas — `Vendor/`, `Vendor.meta`, and the RunLog `*.json.meta` — must sit
  **after** it, or those `.meta` leak back into tracking.

## Structure snapshot & vendor categorization

- **`STRUCTURE.md`** (project root) is a generated, folded `Assets/` tree (see
  [`new-project.md`](new-project.md) and `tools/dump_asset_structure.py`). It is regenerated by the
  pre-commit hook — **do not hand-edit**. (Unrelated to the `AgentInspector` JSON snapshots under
  `Assets/Agent/Snapshots/` — `unity.md`; same word, different artifact.) Gitignored subtrees (`Vendor/`) are truncated 2 levels
  deep with a recursive file-count rollup, so the snapshot shows our full layout plus a
  per-package vendor inventory.
- **Never double up a vendor folder.** Vendor content is categorized one level deep as
  `Vendor/<Category>/<Package>` (e.g. `Vendor/Avatars/Chocolat`, `Vendor/Outfits/<Outfit>`); we
  never nest our own structural decisions deeper inside `Vendor/`. A new vendor system gets its
  own category (e.g. `Vendor/FaceTracking/`), not a folder buried under an avatar. This is what
  makes the snapshot's depth-2 truncation lossless for *our* decisions.
- **Keep our top-level names English.** Folders we author that surface in `STRUCTURE.md` should use
  English names where possible — some vendors ship Japanese filenames, but our organizing layer stays
  legible.
- Because our work references vendor **by GUID, not path**, the snapshot's co-located names
  (`Avatars/Chocolat` next to `Vendor/Avatars/Chocolat`) are a **convention, not authoritative
  linkage** — a renamed or GUID-only dependency won't line up by name. True dependency resolution
  is a separate concern, out of scope for the snapshot.
- The **owned** mirror is a stronger claim than that vendor convention: an owned outfit's
  `Assets/Outfits/<Base>/<Outfit>/` and `Blender/Outfits/<Base>/<Outfit>/` **are** the same logical
  asset in two trees — **load-bearing**, not cosmetic — and a fit gate resolves the `.blend` from
  that mirror. Baked-vs-unbaked never forks a separate `<Base>` bucket: baked-ness is a mesh stamp
  (`avatarprep_baked`), not a folder axis.
