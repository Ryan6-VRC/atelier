# AvatarProject layout & conventions

Where things go in the Unity sandbox. The act of importing a vendor package — file selection,
gates, relocate/verify — is the **`import-vendor-asset`** skill; this doc only defines where the
result lands and why.

## Untouched vs. our work

- **`Assets/Vendor/`** — untouched vendor imports, never hand-edited (`Vendor/Avatars/<Name>/`,
  `Vendor/Outfits/<Outfit>/`, and `Vendor/_Common/` for assets shared across a seller's packages).
  **Gitignored**, reproducible by re-importing the source `.unitypackage` from the **asset library** —
  the external store of vendor packages; its location is machine-local (`CLAUDE.local.md`), never
  written into tracked files. Our work references vendor assets **by GUID, not path**, so tracked work survives
  a bare re-import even though a package re-imports to its own native top folder.
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
- **`Assets/Vendor/` and `Packages/` are read-only to our tooling.** A tool that would mutate an asset
  there must **materialize an owned copy first**; writability is judged **per-asset, by path** (an owned
  controller may still reference a vendor clip — that clip stays read-only). This is a **policy** guard, not
  physical immutability — VPM-restored `Packages/` payloads are writable on disk, so the rule is a convention
  the tools enforce (with a `force` override that records the breach loudly), not an OS-level lock.
- **Non-Unity source files live outside `Assets/`** at the project root, so editing them never
  triggers an editor refresh:
  - **`Blender/<Avatars|Outfits>/<Name>/`** — per-avatar (or per-outfit) folder, namespaced like
    `Assets/`: the `<Name>.blend` source. The exported `<Name>.fbx` goes to `Assets/<…>/Models/` (Unity
    imports only under `Assets/`), **not** here. Avatar folders also hold the **proportion profiles** the
    reproportion skill reads/writes (see below); outfit folders carry none.
  - **`Photoshop/<Avatars|Outfits>/<Name>/`** — `.psd` source art. A PSD is only worth bringing over
    if we intend to modify it (the package already ships the untouched PNG exports), so PSDs are
    *our* work, not vendor — no `Vendor/` namespace. Gitignored like all binaries (above) and kept
    under external backup; the package ships the untouched PNG exports.

## Proportion profiles & state naming

Reproportioning edges (JSON) are **co-located per avatar** in `Blender/Avatars/<Name>/`; the shared
`vrc-blender-tools/profiles/` holds only examples/fixtures. An edge is authored against one rig's
literal bone names, so it is owned by the avatar it targets. **Outfits have no edge of their own** — an
outfit is fitted to a (re)proportioned avatar by applying that **avatar's** edge to the outfit's armature.

State names are **stamped onto the armature** (`avatarprep_state`) and travel with the `.blend`; they are
**never exported to FBX** (the export recipe omits `use_custom_props`). The source-state guard reads them
**in Blender** (`validate_profile`), before apply — so they must be self-describing:
- **Avatar-qualified and descriptive.** Bare adjectives (`custom`, `base`, `final`, `new`) are
  disallowed as a whole name — qualify them (`shinano-base`, `plum-tall`). (The banned adjective `base`
  is unrelated to the avatar-base noun (`nondestructive.md`) or the `avatarprep_base` slot below.)
- **`vendor`** is the one reserved generic (the untouched import origin).
- **Filenames mirror the `source`/`target` fields** — `vendor-to-shinano-base.json` — keeping
  file ↔ stamp ↔ fields consistent.

`avatarprep_state` is one slot of a two-slot base/state model; its behavior (and the `avatarprep_base`
lineage slot) lives in `blender.md`.

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
