# Workflow

`unity.md` and `blender.md` hold per-system how/why; **skills** are the repeatable units of work. This
file is the glue above them — goals, sequencing, and how a task hands off between Unity and Blender.

## Own vs. compose

Two ways a vendor asset enters an avatar; choose by whether you need to own its geometry.

- **Compose (default).** Drop the *untouched* vendor prefab in and attach it non-destructively (Modular
  Avatar / VRCFury). The vendor asset is never edited; the stack resolves at upload on a clone. Right for
  anything you don't need to durably change — props, accessories, outfits that fit. Placing one is the
  **`compose-mergeable`** skill, which runs `CheckAvatar` on the placed root: an MA-scene-ref miss is
  retargeted in place (stays a compose), but a **clip-binding** miss whose `.anim` is unowned vendor
  geometry (`clipAssetPath` under `Assets/Vendor/`|`Packages/`) **aborts the compose and routes to owning**
  — that fix is a geometry round-trip compose can't do; an already-owned clip is repathed inline.
- **Own.** When you need a durable change to the geometry, build your own copy — a new `.blend` +
  exported `.fbx`, reusing vendor **materials**/**textures**, owning deeper only where customization
  needs it. Once the proportioning system is in play, every piece that **deforms with the body** must be
  owned to take the shared reshape — a rigid, already-seam-authored piece still just composes — so owning
  is common. Copy the vendor's dynamics/authoring onto the owned FBX so it stays drop-in-equivalent.

Either way the avatar stays non-destructive until upload. See `nondestructive.md`.

## The owning arc

Crystallized as the **`own-base` skill** (judgment, gates, sequencing) over the
`com.ryan6vrc.avatar-tools` Unity tools and the `avatarprep` Blender functions. The skill is the entry
point; this is the shape it drives:

1. **Graph & decide** — `ReportPackage` reports the vendor package (read-only). Pick the superset
   FBX; the owned base stays **outfit-agnostic**, so keep every non-identical body mesh rather than
   choosing one variant up front (the prefab consumer disables the unwanted ones per outfit). Surface
   to the operator: vendor import settings that differ from ours, a **no-superset case** (variations
   split across FBXs — built into a superset by armature-merge in step 2, not a dead end), or
   MA/VRCFury/NDMF presence (copying those is a later arc).
2. **Blender normalize** — import the chosen FBX, observe-before-changing, drop every clothing mesh
   (keep all body/underwear), rename head→`Body` / body→`Body_Base`, prune the orphaned zero-weight bone
   chains, export via the avatarprep CATS recipe. (Renaming the head mesh tends to break facial-gesture
   clips — re-path them.)
3. **Unity rebuild** — work on the **scene** instance of our FBX, in order: conform the humanoid rig →
   assign vendor materials + the standard bounds/anchor → transplant the descriptor (+ fresh
   PipelineManager) → reproduce the dynamics, then group them (grouping is an operator-gated ask, not
   automatic — `own-base`). Convert to a prefab variant, move the FBX into `Models/`,
   ask the operator to **test-drive**, then build the clean FX.

Each Unity tool emits a one-line diagnostic + RunLog — a `Check` or write gate carries a PASS/FAIL
verdict, a `Report` (e.g. `ReportPackage`) a verdict-free `=> OK` digest. Treat a vendor-leak or
nulled-ref count as a stop-and-investigate gate (usually a name/path mismatch), not something to push
past — but a flagged-missing host is the expected subset case, not a gate.

Outfit / hair / accessory owning is the **`own-mergeable`** skill — the same three-phase spine minus the
body-only steps. Deferred (a later arc): copying Modular Avatar / VRCFury / NDMF systems off a base.

## The reproportion arc

Crystallized as the **`reproportion` skill** — a follow-on once a clean base exists, not part of
owning. A proportion profile is a **repeatable armature transform that applies equally to a base and
the mergeables sharing it** — both must carry the same profile to stay compatible, so it keeps a
compatible set coherent through a shape change. On disk a profile is an **edge** (one declarative
source→target transform JSON) or a **recipe** (an ordered chain of edges); "profile" is the umbrella
term for either. Reshape proportions in Blender (the `avatarprep` profile
engine), re-export, then reconcile the Unity side. It's **one operation whose reconcile tail scales with how much Unity state exists**:
re-run the humanoid rig (the bind is frozen in the `.meta`), then reconcile ViewPosition, component
dimensions, and blendshape coherence — all per `unity.md`'s geometry-change reconcile.

Reproportion runs **in place** (re-export the FBX under the existing prefab, reconcile) or as a
**twin/copy** — a proportioned variant built onto a fresh re-exported twin by transplanting the finished
original's dynamics (the `reproportion` skill's twin/copy flow). The twin path **forces** the source's
holder-parked dynamics back rather than relocating them (see `unity.md`).

A **baked body morph** is a same-set coherence property, like a proportion profile: every mergeable on that
base must match the value — carried as a live shape-key value or folded in via `bake_shapekey` (recorded in
`avatarprep_baked`) — reconcilable via the delta when two differ. The one-value-per-morph invariant is
canonical in the `reproportion` skill (*Realizing shapekeys*).

## Unity ↔ Blender split

Blender owns mesh/armature work (FBX import + observe, drop/rename, prune, rest-pose bake,
proportion-profile reshaping, FBX export via `avatarprep`); Unity owns assembly, components, and upload.
Tasks pass between them as an exported FBX + Git diffs. **The FBX carries geometry + morph deltas *and* the shape-key value as each blendshape's import weight** (see `blender.md`) — so body-shape morphs set as shape-key values in Blender cross the seam; keep them coherent across body + outfit meshes.

## Validate with a play-mode build

Entering play mode runs the full non-destructive stack on the transient play copy — the one bake
path and the universal comprehensive check (`unity.md`; the play-entry gate is enforced — `verify.md`).
