# Non-destructive composition (NDMF / Modular Avatar / VRCFury)

How avatars are assembled here. This is the foundation: the avatar you edit is **authoring**, never the shipped product.

Read this to orient, then stop. The framework mechanism below the surface — build order, per-component behaviour, what survives a copy — is the tools' to know, not yours; what stays here is what has to shape your authoring *before* a check can help, and each item says whether a check backs it. The **package source is the authority** on any framework question (`Packages/nadena.dev.modular-avatar/`, `Packages/com.vrcfury.vrcfury/`); read it or measure live rather than reasoning from a summary.

## An avatar is a base + mergeables

An avatar is an **avatar base** plus any number of **mergeables** attaching through one normalized armature seam (matching bone names under a shared root) — the **attach seam**, an MA/VRCFury component resolved at build, and a different thing from the Blender-side structural merge seam that runs before Unity sees the asset (`blender.md`). "Outfit", "hair", "tail", "accessory" are human labels — the stack treats them identically; the base is just the mergeable carrying the avatar descriptor. A base can be an untouched vendor body or customized to any degree; composition is indifferent to how much it changed.

**Armature names at the seam.** A base's armature is exactly `Armature`; a mergeable we own gets a distinctive `Armature.<Name>`, set in Blender. It is our convention for what we own, **never a way to identify a mergeable** — real vendors ship module armatures named plain `Armature`, so an agent using the name to *detect* mergeables mis-reads those packages entirely.

## The build is non-destructive, on a clone

The avatar in the scene is a recipe. The final avatar is produced at **build time on a throwaway clone** — the SDK clones on upload, play mode runs on the transient play copy. **Vendor and scene assets are never mutated**: non-destructiveness is structural, not our discipline. **The one input this does not cover is importer state** — the SDK's blocking validations read the on-disk `TextureImporter`/`ModelImporter`/`AudioImporter`, not the asset, so a `.meta` setting that blocks an upload cannot be corrected on the clone by any pass, ours or a vendor's. Deliberate edit policy for that is `LAYOUT.md` §Vendor mutation's; the door is `ConformImportSettings`.

- **Stay non-destructive until upload.** The live authoring stack *is* the avatar; baking is for inspecting a result, never for producing a deliverable.
- **NDMF** runs ordered phases over the clone. **Modular Avatar is an NDMF plugin**; **VRCFury is its own SDK preprocessor running after Modular Avatar.** You never sequence them — they self-order.
- **A full build is the real correctness check.** A play-mode build exercises the whole stack at once, catching what no single tool's PASS/FAIL can (`verify.md`; behaviour has its own ladder in `gimmicks.md`).
- The stack won't process a hierarchy still holding prefab instances — a clone is unpacked first.
- **Anything derived from the avatar** — clips, meshes, binding paths — is read from the **baked** result, never the source asset, because the build renames and merges.

### The bake door — `OnPreprocessAvatar`, never `ManualProcessAvatar`

**If you write a tool that bakes**, the door is `VRCBuildPipelineCallbacks.OnPreprocessAvatar` — never `AvatarProcessor.ManualProcessAvatar`, which runs NDMF's plugin chain only, so Modular Avatar survives while VRCFury and the optimizers are skipped: a plausible baked avatar, no error, and nothing signalling it is not the one that uploads. It mutates its argument in place and returns `false` when a hook blocks the build; surface that refusal. Hooks may also open **modal dialogs** (VRCFury prompts on a broken Write Defaults mix), so a bake driven over MCP can wedge the editor — recovery in `unity.md` §Sharp edges. Don't suppress the prompt; it reports a real defect.

## Reference hardening — the fact tooling hinges on

The two frameworks store references differently, which decides what survives a copy into another hierarchy:

| | Asset refs (controllers, menus, params, materials) | Scene-object refs (bones, toggle targets, renderers) |
|---|---|---|
| **Modular Avatar** | direct | **path-hardened** — an avatar-relative path, re-resolved at build |
| **VRCFury** | **GUID-hardened** (survive copying) | **raw pointers** — no hardening |

- **Modular Avatar self-heals across a copy**; its one failure is a **renamed path segment** (a normalized `Body_base`→`Body_Base`), because the lookup is exact — `CheckAvatar` names those breaks.
- **`referencePath` is the authoritative half of an MA scene ref, and code that sets only `targetObject` is a silent no-op.** At runtime and at build, an empty `referencePath` resolves to null whatever `targetObject` holds; with a path present, a **live `targetObject` under the avatar root wins before the path is ever tried** (verified against MA source) — so a stale path beside a live target still resolves, and "repairing" the path on its own evidence fixes nothing that was broken. The *inspector's* editor-side resolver checks `targetObject` **first**, with no empty-path guard — so a hand-written ref looks correct in the UI and resolves nowhere at bake. Write the path. `CheckAvatar` names the offender. Don't mirror the resolver — invoke MA's own `Get(Component)`; a hand-walk of its order is legitimate only as a loudly-declared fallback for when the invoke itself is unreachable.
- **VRCFury's scene refs are the only thing a transplant must actively repath** — raw pointers that null out when copied across hierarchies. Only refs inside the copy's reach can be repathed.
- **A VRCFury asset ref is a PAIR — a `<guid>|<path>` string and a live `objRef` — and `objRef` wins.** Setting only the string leaves the component loading whatever the object pointer still holds, while every path you read back looks right. It bites hardest when you build a component by copying a configured one and repointing it: the copy carries the donor's `objRef` and silently keeps running the donor's controller. `CheckAvatar`'s `clip-binding` class is what catches it — bindings that resolve nowhere from the new mount; nothing else does.
- **A merged clip's binding path resolves by walking UP from the component's own object, first valid prefix winning** (`ClipRewritersService.CreateNearestMatchPathRewriter`). A FullController therefore resolves paths written relative to any ancestor on that walk, which is what lets one sit on a rig root and bind `Child/Grandchild/…` unchanged — and what makes a *newly* valid shorter prefix silently capture a path after a reparent. `rootBindingsApplyToAvatar` governs **only** the empty-path binding: read it as "where does a root binding land", never as "what frame are paths in".

## Choosing a framework, and the two hard rules

**Modular Avatar by default** — the self-heal makes it forgiving. **VRCFury** when a mergeable needs robust animator merging: the more it drives the avatar's FX (gestures moving ears, tail, expressions), the more VRCFury earns its place.

1. **A module that both moves objects and animates them keeps both operations in one framework.** The break runs **one way**: a clip VRCFury merged that paths through a node Modular Avatar moved is dropped from the built FX, while the reverse survives, because VRCFury repaths the merged clips along with its own moves and MA has no counterpart running late enough to return the favour. So a VRCFury `ArmatureLink` under a `FullController` is a sanctioned anchor; an MA `BoneProxy` or `MergeArmature` above an animated node in that subtree is not. **The build does warn** — it names each dropped binding path, names the emptied layer, and that layer's VRCFury prefix carries the module's name; on the live clone the layer survives renamed `(NO VALID ANIMATIONS)`. That string is **not this break's fingerprint** — VRCFury appends it to any layer holding no valid bindings and no behaviours, so a param-only `Toggle` whose layer legitimately does nothing earns it in a working build (measured: 2 of 3 toggles in a verified build); route on `CheckAvatar`'s `anchor-seam` class, never on the string. What no message ever names is the anchor that caused it, so the warnings read as a broken clip rather than a misplaced component. The same asymmetry hits VRCFury's parameter-name rewrite, which reaches only its own subtree too: a param-carrying component MA moved out keeps the bare name and its writes bridge to nothing, so a receiver under a moved anchor reads 0 forever — and *that* one produces no message at all. Hence behaviour lives in VRCFury, MA touches only anchor nodes carrying no animated bindings, and a module **senses from inside**: constrain a sense point to the anchor GO, never parent it there. `CheckAvatar`'s `anchor-seam` class names the anchor the build's warnings don't (`unity-tools.md`); `vrc-patterns`' gate fails an entry carrying one.
2. **A module that may be instanced more than once needs VRCFury** — per-instance parameter isolation by default.

## Merge behaviours that change what you author

Everything else about these components is the package source's to answer. These decide work *before* you reach a tool:

- **`Merge Armature` matches by bone name**, and which branch a bone takes decides what an owned base should carry. A name-matched bone **zips** — the outfit's collapses onto the avatar's — while an unmatched one is reparented and **kept** as the outfit's own, the ordinary case for skirt/ribbon chains, not a defect. Components on the outfit bone can force the kept branch even on a name match; the package source owns which. So a base retaining a chain it does not weight flips a mergeable from kept to zipped, and the base's own bone then carries the mergeable's geometry. A *whole-armature* mismatch zips nothing and skins the outfit to a private copy of the armature; `CheckSeam` REFUSEs on that rather than scoring it.
- **The merge is identity-preserving.** MA retargets bones exactly as they sit and reconciles nothing, so a mismatched rest pose bakes through unchanged: what you see pre-build is what ships. VRCFury is the exception — its align-to-base options apply **at build**, not in edit mode, so that invariant does not hold for it.
- **`Armature Link` deletes parent constraints on the objects it merges, by default** (`removeParentConstraints`, under Super Advanced Options), so linking a rig whose behaviour *is* a parent constraint destroys it without a word, and no check catches it. Clear the flag, or anchor that rig another way.
- **`Armature Link` renames linked bones at build.** Each linked bone is wrapped as `[VF###] BoneName` and the original object becomes `Original Object` inside the wrapper (`ArmatureLinkService`). Authored hierarchy names do not survive into play mode — a name-search for the bone you authored finds the wrapper, not the functional node. Navigate under the link's target bone in the avatar armature, not by the authored name.
- **An `ArmatureLink` built by reflection or script is not the inspector's behaviour**, and two of its defaults put the prop somewhere you did not ask for. `linkTo` ships **already holding one entry, `HumanBodyBones.Hips`**, and the list is a first-resolvable-wins fallback chain, so an appended entry never runs and the prop links to Hips: clear the list before adding to it, and **pin the component's `version` to the model's current one** (`GetLatestVersion()`) so `Upgrade()` cannot repopulate it out of the obsolete `boneOnAvatar`. Alignment lives in `alignPosition`/`alignRotation`/`alignScale`; `keepBoneOffsets2` is `[Obsolete]`, read only by the version upgrade, so a component built fresh at the current version never consults it and setting it to `No` snaps nothing — the prop stays wherever you left it. Seat the prop bone on the target bone's **rest pose** while authoring regardless, so any offset the link retains is identity.

## Tooling implications

- Transplant/owning tools work on the **authoring layer** and must preserve non-destructiveness: reproduce Modular-Avatar-as-Modular-Avatar and VRCFury-as-VRCFury. Never flatten, bake, or re-author.
- **Copy from the standalone vendor prefab**, not one already placed on an avatar — a placed component carries cached avatar-relative state a blind copy mis-resolves.
- **Don't lean on MA/VRCFury to move an armature into alignment**; the two apply it differently, so the result isn't predictable across systems. Measure the seam with **`CheckSeam`** instead, and make any genuine correction as a transform edit **in code**.

See `unity-tools.md` for the transplant/owning tool contracts (controllers: `animator.md`) and `workflow.md` for when to own vs. compose.
