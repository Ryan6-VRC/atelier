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

## No operator to ask?

A gate you can't put to an operator is expected, not a blocker. A background job still **has a channel** — the dispatcher — so surface the gate by ending the turn with `needs input:` and wait; a background job is not "no operator." (A worker dispatched under the `dispatch` skill puts gates to the operator directly, never to the coordinator — that skill's no-handback rule supersedes the dispatcher-as-channel reading for interactive waves.) Only with no channel at all do you take the derivable defaults, and even then the disclosure leads the report — every undecided call flagged at the top, never a silently minted convention (folder or category placement especially). Gated skills cite this protocol; a skill may name its own derivable default beside the citation.

**On a batch the gate instruction becomes *queue, never default*.** Stopping dead on item 3 of 15 wastes the batch, so: work that does not depend on the answer proceeds, work that does is **left undone and named** — never completed on a guess — and every queued question surfaces together in one `needs input:` block at the end. Only the timing of the ask moves; the silent default stays forbidden. This is equally a constraint on how a batch is *dispatched*: "note it and move on rather than stalling" reads to a worker as license to default the gates, and has.

## Deviating from a mandated step

Skills mark a step mandatory because the cheap substitute is known-insufficient — the step exists against a failure the substitute cannot see. A deviation is legitimate only in this form: announced before acting, backed by a probe or measurement (never an inference), citing the skill's own caveat that covers the case, and surfaced on the operator channel. "Proportionate to a small task", "the render will catch it", and "my cheaper read already covers it" are the rationalizations that have preceded every recorded defect from a skipped step — a justification in that family is the signal to stop and run the step as written.

## Unity ↔ Blender split

Blender owns mesh/armature work (FBX import + observe, drop/rename, prune, rest-pose bake, proportion-profile reshaping, FBX export via `avatarprep`); Unity owns assembly, components, and upload. Tasks pass between them as an exported **FBX + Git diffs**. The FBX carries geometry + morph deltas *and* the shape-key value as each blendshape's import weight (`blender.md`) — so body-shape morphs set in Blender cross the seam; **keep them coherent across body + outfit meshes.**

## Validate with a play-mode build

Entering play mode runs the full non-destructive stack on the transient play copy — the one bake path and the universal comprehensive check (`nondestructive.md`; the play-entry gate is enforced — `verify.md`).
