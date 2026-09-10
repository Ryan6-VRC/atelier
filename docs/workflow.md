# Workflow

`unity.md` and `blender.md` hold per-system how/why; the **skills** are the repeatable units of work, each its own authority on how it runs. This file is the glue above them: which skill a task routes to, how tasks hand off between skills, and how work crosses the Unity↔Blender seam.

## Own vs. compose

Two ways a vendor asset enters an avatar; choose by whether you need to **own its geometry**.

- **Compose (default).** Drop the *untouched* vendor prefab in and attach it non-destructively (Modular Avatar / VRCFury); the stack resolves at upload on a clone, the vendor asset never edited. Right for anything you don't need to durably change — props, accessories, outfits that fit. → **`compose-mergeable`**.
- **Own.** When you need a durable change to the geometry, build your own copy — a new `.blend` + exported `.fbx`, reusing vendor **materials**/**textures**, owning deeper only where customization needs it (a material/texture customization is the **`own-material`** skill — geometry and materials own independently). Once the proportioning system is in play, **every piece that deforms with the body must be owned** to take the shared reshape (a rigid, already-seam-authored piece still just composes), so owning is common. → **`own-base`** (body) / **`own-mergeable`** (outfit / hair / accessory).

Either way the avatar stays non-destructive until upload (`nondestructive.md`).

## Skill routing and handoffs

Each skill carries its own gates, sequencing, and tool doors; this is only the graph between them.

- **own-base → reproportion → compose.** Owning a base yields a clean starting prefab. **reproportion** is a follow-on once that base exists, not part of owning: a proportion profile applies equally to a base and the mergeables sharing it, so both must carry the same profile to stay compatible — it keeps a compatible set coherent through a shape change. `CheckSeam` enforces that compatibility at compose: an `edges`-scaled outfit dropped on an unscaled base `NOT-PASS`es (`unity-tools.md`).
- **compose aborts-to own-mergeable.** `compose-mergeable`'s seam check routes a broken **clip-binding**
  whose `.anim` is **unowned vendor** geometry (`clipAssetPath` under `Assets/Vendor/`|`Packages/`) out
  to `own-mergeable` — that fix is a geometry round-trip compose can't do. An owned/writable clip, or an MA-scene-ref miss, it repairs in place.
- **Deferred arc:** copying Modular Avatar / VRCFury / NDMF systems off a base.

## Is it even a gate?

A correction outside what was asked for, that changes what ships, is the operator's — even when it is plainly right, and even when leaving it feels like shipping a known defect. A correction inside the ask, reversible, and invisible in the built result is yours. What tells them apart is what a reviewer would be surprised to find, not how confident you are in the fix: measured vendor incoherence found in passing, and a whole-avatar mode set so your own change would work, are both the first kind. Name it and queue it — never bank the fix and mention it afterwards.

## No operator to ask?

A gate you can't put to an operator is expected, not a blocker. A background job still **has a channel** — the dispatcher — so surface the gate by ending the turn with `needs input:` and wait; a background job is not "no operator." (A worker dispatched under the `dispatch` skill puts gates to the operator directly, never to the coordinator — that skill's no-handback rule supersedes the dispatcher-as-channel reading for interactive waves.) Only with no channel at all do you take the derivable defaults, and even then the disclosure leads the report — every undecided call flagged at the top, never a silently minted convention (folder or category placement especially). Gated skills cite this protocol; a skill may name its own derivable default beside the citation.

**On a batch the gate instruction becomes *queue, never default*.** Stopping dead on item 3 of 15 wastes the batch, so: work that does not depend on the answer proceeds, work that does is **left undone and named** — never completed on a guess — and every queued question surfaces together in one `needs input:` block at the end. Only the timing of the ask moves; the silent default stays forbidden. This is equally a constraint on how a batch is *dispatched*: "note it and move on rather than stalling" reads to a worker as license to default the gates, and has.

## Deviating from a mandated step

Skills mark a step mandatory because the cheap substitute is known-insufficient — the step exists against a failure the substitute cannot see. A deviation is legitimate only in this form: announced before acting, backed by a probe or measurement (never an inference), citing the skill's own caveat that covers the case, and surfaced on the operator channel. "Proportionate to a small task", "the render will catch it", and "my cheaper read already covers it" are the rationalizations that have preceded every recorded defect from a skipped step — a justification in that family is the signal to stop and run the step as written.

## Unity ↔ Blender split

Blender owns mesh/armature work (FBX import + observe, drop/rename, prune, rest-pose bake, proportion-profile reshaping, FBX export via `avatarprep`); Unity owns assembly, components, and upload. Tasks pass between them as an exported **FBX + Git diffs**. The FBX carries geometry + morph deltas *and* the shape-key value as each blendshape's import weight (`blender.md`) — so body-shape morphs set in Blender cross the seam; **keep them coherent across body + outfit meshes.**

## The coverage cut — trimming the body under a costume's unconditional garments

Run only where a composed row's built triangle count (the `tris` line of `ReportComposition bake:true`) misses the rank line the operator wants **and** the operator has agreed to touch the shared base: the carrier lands in the base body's blend and FBX, so every row wearing that body re-imports it. Most composes never run it.

**The unit is the costume, never the configuration or a single garment.** Coverage is a function of the whole unconditional garment set (a ray one garment lets past, another blocks) plus the shapes that set carries, and both are the costume's facts; hair and form change no body coverage. So one carrier per costume per body, `Cover_<CostumeStem>`, consumed by one Delete row on the costume prefab root, unconditioned — every configuration wearing the costume inherits the cut. A costume shipped in two unconditional states takes the shared set's carrier on the root and the selectable garment's increment as `Cover_<CostumeStem>_<Garment>`, its Delete row declared on that garment's own object, so a configuration that drops the object leaves the row inactive (`outfits.md`: the garment that covers owns the hide).

The sequence, two substrates and one operator gate:

1. **Unity — read the composition.** Garments: the costume's pieces active with no `Clothing` leaf or toggle reaching them, less the base pieces the costume turns off and any extra it ships inactive. Shapes: `map-outfit-shapes`' resolution table is the input — each Set row's resolved value is a `--shape`, each unconditional Delete a `--cut-shape`; a raw index-addressed `m_BlendShapeWeights` override is the one entry that table cannot name, so read that mesh live.
2. **Blender — measure.** `mark_coverage --whatif` with `--render` and `--out-marked` (`blender.md`). Turn `--fold-bones` and `--cone-deg` only against a named swing or a loose boot.
3. **Operator gate.** The renders and the inspect blend are the operator's to approve; nothing writes before that word.
4. **Blender — write.** The same run without `--whatif`, after a venue git checkpoint.
5. **Unity — the base tail** (`blender.md`), plus the triangle diff on every row wearing the body, all expected identical: the unused shape is stripped at build.
6. **Unity — compose.** The Delete row, then the target row's triangle diff, `CheckAvatar` at the recorded offender set, the play-mode bake, and the row's record.

## Validate with a play-mode build

Entering play mode runs the full non-destructive stack on the transient play copy — the one bake path and the universal comprehensive check (`nondestructive.md`; the play-entry gate is enforced — `verify.md`).
