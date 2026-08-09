# AvatarProject layout & conventions

Where things go in the Unity sandbox. The act of importing a vendor package — file selection, gates, relocate/verify — is the **`import-vendor-asset`** skill; this doc only defines where the result lands and why.

## Untouched vs. our work

- **`Assets/Vendor/`** — vendor imports kept as-dropped, hand-edited only for the sanctioned reconstructions under *Vendor mutation* below (`Vendor/Avatars/<Name>/`, `Vendor/Outfits/<Outfit>/`, and `Vendor/_Common/` for assets shared across a seller's packages). **Not kept**, reproducible by re-importing the source `.unitypackage` from the **asset library** — the external store of vendor packages; its location is machine-local (`CLAUDE.local.md`), never written into a tracked file. Our work references vendor assets **by GUID, not path**, so our work survives a bare re-import even though a package re-imports to its own native top folder. A **patched** vendor asset is the exception — it reproduces only with its patch replayed (*Vendor mutation* below).
- **Everything else under `Assets/`** — our work (prefab variants, scenes, animators, materials). Durable, kept. No `Work/` wrapper.
- **Durable work is diffable text, not large binaries.** What we keep is what diffs cleanly — YAML (scenes/prefabs/materials), `.meta`, `.json`, scripts. Art/source binaries (`.fbx` `.blend` `.psd` `.png`, audio) don't diff, so:
  - they're **not kept**, but each keeps its `.meta` (GUID + import settings) so references resolve
    and a re-exported file rebinds;
  - RunLog JSON is disposable too — per-run diagnostics, not a durable artifact;
  - since binaries aren't kept, **back them up externally** — a restored venue has no
    meshes/textures until they're restored or re-exported.
- **Owning is selective.** An owned asset tracks only what it actually changed and keeps **GUID-referencing the vendor original** for everything it didn't — an owned base can still point at vendor animator layers or materials it never customized. Provenance is a property of each *reference*, not of a folder.
- **A top-level avatar folder holds full prefabs, not loose parts.** `Assets/Avatars/<Name>/` (like `Assets/Outfits/<Base>/<Outfit>/`) is essentially only complete prefabs; owned controllers, clips, and params live in **subfolders**. This is the on-disk half of *owned = wired* (`animator.md`): a properly-owned set is both wired to its load path and filed out of the top level. Convention, not a tool.
- **`Assets/Vendor/` and `Packages/` are read-only to our tooling.** A tool that would mutate an asset there must **materialize an owned copy first**; writability is judged **per-asset, by path** (an owned controller may still reference a vendor clip — that clip stays read-only). The **one exempt class** is a blocking platform importer setting — *Vendor mutation* below owns it, and `ConformImportSettings` is its only door (no `force`: its whole scope is the sanctioned class). This is a **policy** guard on *deliberate* edits, not a byte contract: it means fork-before-you-change (a `force` override records any breach loudly), not that vendor bytes never move — VPM restores and importer migrations rewrite `Vendor/`/`Packages/` on disk with no agent and no breach (see *Vendor mutation*).
- **`Assets/Materials/<Avatars|Outfits>/<Name>/`** — owned materials and their exported textures,
  mirroring `Photoshop/` by name. Base-independent like the PSD art (texture work doesn't change with proportions), so one bucket serves every base wearing the outfit — but when the geometry is *also* owned, materials file with it (`Assets/Outfits/<Base>/<Outfit>/Materials/`) instead: one logical asset, one home. Copy semantics (selective slot forking, shader handling) are the `own-material` skill's.
- **Non-Unity source files live at the Unity project root** (`AvatarProject/`, outside `Assets/` so editing them never triggers a refresh) — inside the untracked venue, never the meta-repo:
  - **`Blender/Avatars/<Name>/`** — the `<Name>.blend` source (a binary: not kept, externally backed
    up), namespaced like `Assets/`; it also holds the **proportion-edge JSONs** the reproportion
    skill reads/writes, which *are* kept (diffable recovery artifacts — see below).
  - **`Blender/Outfits/<Base>/<Outfit>/<Outfit>.blend`** — owned outfits go **base-first**: the base
    you fitted to is held constant, the outfit varies underneath it (file by the axis held constant —
    `Vendor/Outfits/<Outfit>/` stays **outfit-first**, since a vendor product's base varies *inside*
    one package). The exported `.fbx` mirrors this at `Assets/Outfits/<Base>/<Outfit>/Models/` (Unity
    imports only under `Assets/`, **not** here); outfit folders carry no proportion profile of their
    own (see below). One outfit fitted to two bases is **two buckets, two `.blend`s** — duplication
    accepted for clarity, no cross-base sharing.
  - **`Photoshop/Avatars/<Name>/`** and **`Photoshop/Outfits/<Outfit>/`** — `.psd` source art,
    **outfit-first** (no `<Base>` segment): reproportioning is geometry-only, so art is
    base-independent. A PSD comes over only to be modified (the package already ships its PNG
    exports), so PSDs are *our* work, never `Vendor/`; not kept, externally backed up like all
    binaries. What enters Unity is a **flattened PNG export** into the owned-materials bucket —
    the `.blend` → `.fbx` contract mirrored; an *owned* material referencing a `.psd` inside
    `Assets/` is a defect (a vendor material linking its own shipped PSD is vendor authoring,
    untouched until owned).

## Vendor mutation: patch, copy-on-write, importer drift

"Untouched `Vendor/`" is the default, not an invariant — content legitimately changes without being tampering, so the rule is **sanctioned mutation, marked**:

- **A vendor's own patcher never patches the base in place.** Some DLCs ship a binary patcher (`hpatchz` + `.hdiff`) that rewrites a base FBX so a variant prefab referencing it by GUID picks up the new mesh. In-place is the vendor's design, not ours — it destroys the original, and a later base re-import silently reverts it and breaks the variant with nothing recording a patch ran. Extend the copy-on-write rule above to cover it: **reconstruct the parallel-patched layout a careful vendor would ship** — patch a **copy** of the base FBX placed as a sibling in the package, and repoint the DLC's own variant prefab(s) to that copy (a whole-GUID swap in the prefab YAML; sub-asset fileIDs survive a copy, so mesh and avatar references move together). The base FBX and the base package's own prefabs stay byte-identical; vanilla and variant coexist. A DLC that already ships a parallel patched folder needs no reconstruction. The **three sanctioned edits** — patched copy, provenance sidecar, repointed variant prefab — are the enumerated exception to "never nest our own structural decisions deeper inside `Vendor/`" (below): sanctioned agent edits, not a claim of non-interference. Procedure: the `import-vendor-asset` skill's *Patch a vendor-mutated asset*.
- **Provenance travels with the patched copy.** A sidecar records the replay recipe — patcher, `.hdiff`, source FBX (path + GUID), output, date. Like everything in `Vendor/` it is **not kept** (no durable history; restored from external backup); its job is to catch a base re-import that reverted the patch. A patched-variant package reproduces by re-running the import on the base + DLC packages, or restoring `Vendor/` from backup — never by re-importing the base alone, which restores vanilla only.
- **A blocking platform importer setting is ours to correct** — in place, on the vendor asset, by `ConformImportSettings` at the import door (`unity-tools.md`), across the **whole folder passed, including assets no avatar references**. Sanctioned on three counts — it **blocks** (an advisory never is), its offender status is **intrinsic to the asset** (the SDK's menu-icon rule fails that and stays the operator's), and it writes only the **`.meta`** — with its RunLog naming every path written, any texture capped below its source, and the SDK version the severity was read against; no sidecar, and a `.unitypackage` re-import or venue restore simply drops it.
- **A self-writing vendor system's generated output is its own layout, not a breach** — VRCLens writes per-avatar assets under its own `User/<avatar>/`, non-redirectable by design. What that does *not* cover is collateral: such a system's blanket `SaveAssets()` can rewrite incidentally-loaded vendor assets far from its folder (a merely-referenced controller churned content-clean; Resource renderTextures re-serialized). After any vendor-system apply, diff the vendor tree and triage every touched path — expected generated output vs. incidental rewrite vs. real mutation.
- **Benign in-place drift is not tampering.** lilToon rewrites a vendor `.mat` at import (`_lilToonVersion` bump + new default props) with no agent acting. A vendor-integrity check protects *intent*, not *bytes*.

## Proportion profiles & state naming

Reproportioning edges (JSON) are **co-located per avatar** in `Blender/Avatars/<Name>/`; the shared `vrc-blender-tools/edges/` is a **curated sample library** (migrated real edges plus known base-equivalency samples) that doubles as that repo's test-fixture corpus — it is not packaged into the extension build. A profile is a **typed edge** `(source_base, source_state) → (target_base, target_state)`, authored against one rig's literal bone names, so it is owned by the avatar it targets. **Outfits have no proportion-edge JSON of their own** — an outfit is fitted to a (re)proportioned avatar by applying that **avatar's** edge to the outfit's armature. That doesn't mean an outfit's base is unknown, though: its lineage is separately stamped as `avatarprep_base` on the outfit's own armature.

State names are **stamped onto the armature** (`avatarprep_state`) and travel with the `.blend`; they are **never exported to FBX** (the export recipe omits `use_custom_props`). `apply_proportion_edge --whatif` reads them **in Blender**, before apply, exact-matching both the state and the separate `avatarprep_base` stamp — an absent base is an **offender** (stamp it first), an absent state only warns:
- **State values are base-neutral.** `custom` is the correct target state, not `custom_shinano` or `plum-tall` — body identity belongs to the `avatarprep_base` stamp, never the state label.
- **`unproportioned`** is the one reserved generic — the as-imported origin state (never `vendor`, which conflates provenance with shape).
- **Filenames may carry the base the state value doesn't**, in two cases: a **reproportion** (same base) is named for its target config — `custom_shinano.json` (target state + base, for legibility); a **base-change/equivalency** is named `<source_base>-to-<target_base>.json` — `plum-to-chiffon.json`.

The folder tree above is for **browsing**; the authoritative provenance is always the `(base, state)` stamp in the **mirrored `.blend`** (see below) — except a **refit bucket**, which has no mirror and carries a refit sidecar instead (see *Vendor categorization*). If a stamp is missing at filing or fit time, the fix is to ask the operator, write the stamp back, and refile into the correct base bucket — that loop lives in the `own-mergeable` skill, not here.

`avatarprep_state` is one axis of a three-axis base/state/baked model; its behavior (and the `avatarprep_base`/`avatarprep_baked` axes) lives in `blender.md`.

## The project `.gitignore`

The venue is untracked, so this `.gitignore` doesn't act on the live tree — but it ships in the seed skeleton and records the durable-vs-not-kept split. The stock `!/[Aa]ssets/**/*.meta` un-ignore is load-bearing in two directions:
- It **keeps** the `.meta` of the **binaries we don't keep** (we ignore `*.fbx`, not `*.fbx.meta`) — that's what lets refs resolve.
- Rules that must **drop** metas — `Vendor/`, `Vendor.meta`, and the RunLog `*.json.meta` — must sit **after** it, or those `.meta` leak back in.

## Vendor categorization

- **Never double up a vendor folder.** Vendor content is categorized one level deep as `Vendor/<Category>/<Package>` (e.g. `Vendor/Avatars/Chocolat`, `Vendor/Outfits/<Outfit>`); we never nest our own structural decisions deeper inside `Vendor/`. A new vendor system gets its own category (e.g. `Vendor/FaceTracking/`), not a folder buried under an avatar.
- **A vendor tool that discovers content by scanning its own install path is the sanctioned exception to that categorization** — it stays at its native path and its content-packages install into it, because relocating either blinds the scan. MochiFitter (`Assets/OutfitRetargetingSystem/`, profiles inside its `Editor/`) is the case; `docs/mochifitter.md` owns the mechanics.
- **Vendor sample content and profile drops can also land at the `Assets/` root**, outside any vendor folder (an install's bundled sample costume, a profile's own top-level folder) — the scanning-tool exception covers the install dir only. Expect them after an install and enumerate them in the import commit; they are vendor content wherever they land.
- **Keep our top-level names English.** Folders we author should use English names where possible — some vendors ship Japanese filenames, but our organizing layer stays legible.
- Because our work references vendor **by GUID, not path**, the co-located naming convention (`Avatars/Chocolat` next to `Vendor/Avatars/Chocolat`) is a **convention, not authoritative linkage** — a renamed or GUID-only dependency won't line up by name. True dependency resolution is a separate concern.
- The **owned** mirror is a stronger claim than that vendor convention: an owned outfit's `Assets/Outfits/<Base>/<Outfit>/` and `Blender/Outfits/<Base>/<Outfit>/` **are** the same logical asset in two trees — **load-bearing**, not cosmetic — and a fit gate resolves the `.blend` from that mirror. Baked-vs-unbaked never forks a separate `<Base>` bucket: baked-ness is a mesh stamp (`avatarprep_baked`), not a folder axis.
- A **refit** output (MochiFitter-warped onto a new base — the `mochifit` skill) files in that same owned bucket shape, `Assets/Outfits/<TargetBase>/<Outfit>/` — **never `Vendor/`** (a later-purchased official variant of the same outfit must import beside it, not collide with it), and never a separate refit tree: one (base, outfit) pair has one home whatever its history. The bucket has **no `.blend` mirror**; its recovery artifact is the **refit sidecar** — `refit-provenance.json` beside the prefab, written by `mochifit`, keys `target_base`, `target_state`, `source_base`, `outfit`, `tool_version`, `profiles[]`, `route[]`, `shape_selections[]`, `date` (this list is the canon; the skills route here) — and it reproduces from vendor package + profile rather than from a `.blend`. Compose's provenance routing reads the sidecar where the bucket has no mirror (`compose-mergeable`). Fully owning it later is **in-place surgery** — import the refit FBX **into Blender** to author the bucket's reserved `Blender/Outfits/<TargetBase>/<Outfit>/<Outfit>.blend` (`own-mergeable`), keeping the sidecar for lineage — never a refile.
