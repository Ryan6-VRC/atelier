# MochiFitter — outfit retargeting (roadmap, not integrated)

MochiFitter (もちふぃった～, BOOTH, ¥2,500, by Nine Gates / おもちのびる — also the author of the
*Beryl* avatar that ships as its test data) fits a garment mesh authored for one base body onto a
*different* base body. It warps the mesh through a precomputed dense per-vertex deformation field plus a
Laplacian mesh solver — not a bone remap — and reportedly ports ~90% of outfits onto unsupported avatars.
Its own compatible-avatar list runs to a few hundred products. We have the vendor `.unitypackage`
(~1 GB) on the asset NAS. Nothing here is wired in; this brief exists so future work doesn't unknowingly
close the door.

**Intended role if adopted.** One more *edge type* over the same base-to-base graph the proportion system
crosses (`blender.md`, `reproportion`): proportion edges reshape the *body*, a mochi edge transfers
an *outfit* between bodies. Scope is deliberately narrow — **convert outfits between bases using
pre-authored conversion data only.** We would not adopt its field-authoring pipeline (the expensive part),
so the install/Blender/auto-download machinery below stays out of scope; we consume its data, not its
front-end.

## Shape of the thing

Three layers, all editor-time — it produces a **baked** garment mesh, not an NDMF non-destructive plugin,
so its *output* is what would enter our pipeline:

- **Unity editor front-end** — a closed-source editor plugin plus a `ScriptableObject` holding the job
  (target prefab, base FBX, conversion profile, blendshape selections). The documented flow is
  `Tools > MochiFitter` → Install → drop the outfit prefab → Execute Retargeting.
- **Native solver** — a per-platform (win/linux/mac-arm64) executable with bundled FFI libraries; its
  `THIRD_PARTY_NOTICES` names robust-Laplacian, nanoflann, Eigen, and OpenMP, which is what a
  deformation-field + nearest-neighbour mesh solve needs.
- **Blender bridge** — a GPL Blender addon ("OMOCHI Format") the tool installs and drives headless for
  mesh ops.

## Data model — the part integration depends on

The package ships its conversion data as plain JSON + NumPy `.npz`, which is legible without the plugin.
Per base body there is an `avatar_data_<name>.json` (humanoid↔bone-name map, mesh name, blendshapes, base
poses). A conversion is a directional `config_<src>2<dst>.json` naming a pose-delta file and a
`deformation_*.npz` (the 30–57 MB dense field), with per-blendshape field variants each carrying a
**bone mask** (e.g. the highheel field masked to foot/leg bones).

**The shipped fields are hub-and-spoke through a neutral `template`.** Bodies covered out of the box:
`beryl`, `kikyo`, `manuka`, `shinano`. Each has `config_<X>2template` and `config_template2<X>` but **no
direct `X2Y`** — a base→base conversion is two hops (source→template→dest). Any new base needs its own
`<X>_to_template` field pair authored; that authoring is the barrier, and "pre-authored data only" is
exactly what sidesteps it. In the wider ecosystem a **conversion profile** is this per-avatar data bundle,
published (by the tool author and the community) per source/target avatar — the unit we would consume.
Shape variants present: breasts big/flat/small, highheel, corset, stocking, hip.

**`.omochi` interchange format** (specified openly by the GPL Blender addon source): a glTF-style binary
container — magic `ORS\0`, then u32 version / JSON-length / binary-length, a UTF-8 JSON block (mesh,
armature, materials, blendshapes, bufferViews) indexing a little-endian buffer of float32 vec3/vec2/scalar
and uint32 arrays. Readable and writable from the addon alone.

## Traps that could silently block the path

- **GPL-3.0-or-later.** The native solver and Blender addon are copyleft, and our repos are public-bound.
  Keep the binaries vendor-side; consume the openly-formatted profile data (`.omochi`/JSON/`.npz`) rather
  than committing or linking against them.
- **Install-time network fetch.** The tool's Install step pulls a Blender and conversion data over the
  network. That side effect and supply-chain surface is at odds with our reproducible pipeline — another
  reason to consume pre-fetched profile data directly rather than driving the front-end.
- **Fixed base set.** Out of the box it converts only among the four bodies above; new bases need authored
  fields (the deferred, expensive precompute).
- **Baked, and lossy on rigging.** Output is a baked mesh; per public reports, animations and complex
  gimmicks on the outfit often need rework afterward, and a single conversion runs 20 min–1 hr. Treat a
  mochi edge as producing static garment geometry, not preserved outfit behavior.
- **Size.** ~1 GB, mostly `.npz` + native binaries — vendor-only or LFS, never plain git.

A `.unitypackage` is a gzipped tar of `<guid>/{asset,pathname}` entries; reconstruct the logical tree from
the `pathname` files.
