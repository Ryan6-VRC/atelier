# Non-destructive composition (NDMF / Modular Avatar / VRCFury)

How avatars are assembled here, and the reference-hardening facts every transplant/owning tool
depends on. This is the foundation: the avatar you edit is **authoring**, never the shipped product.

## An avatar is a base + mergeables

An avatar is an **avatar base** plus any number of **mergeables** that attach through one normalized
armature seam (matching bone names under a shared root). "Outfit", "hair", "tail", "accessory" are
human labels — the stack treats them identically; the base is just the mergeable that carries the
avatar descriptor. A base can be an untouched vendor body or one customized to any degree (down to a
head grafted onto another body); composition is indifferent to how much it was changed.

**Armature names at the seam.** A base's armature is exactly `Armature` (the owning merge enforces it);
a mergeable's is a distinctive `Armature.<Name>`, set in Blender when owning. The asymmetry is
deliberate: identical names collide when the mergeable attaches (VRCFury discourages armature-name
collisions), and the distinct name is what lets Blender-side tools scope to one rig in a two-armature
`.blend`. This **attach seam** — the MA/VRCFury component resolved at build — is a different check from
the Blender-side structural **merge seam** (do two skeletons' bone names/parents/positions line up to be
union-merged — `armature_compat`, `blender.md`), which runs before Unity ever sees the asset.

## The build is non-destructive, on a clone

The avatar in the scene is a recipe. The final avatar is produced at **build time on a throwaway
clone** — the VRChat SDK clones on upload; play mode runs on the transient play copy. **Vendor and
scene assets are never mutated** — non-destructiveness is structural, not our discipline.

- **Stay non-destructive until upload.** The live authoring stack *is* the avatar; don't bake-to-flatten
  as a workflow step. Baking is for inspecting the result, not producing a deliverable.
- **NDMF** is the framework. It runs ordered phases over the clone. **Modular Avatar is an NDMF plugin**
  (runs mid-stack); **VRCFury is its own SDK preprocessor that runs after Modular Avatar.** You never
  sequence them — they self-order.
- **A full build is the real correctness check.** A play-mode build exercises the entire
  stack at once, so it catches what no single tool's PASS/FAIL can. Treat it as the comprehensive
  gate for composition (behavior has its own ladder: `gimmicks.md`).
- The stack won't process a hierarchy that still holds prefab instances — a clone is unpacked first.

## Reference hardening — the fact tooling hinges on

The two frameworks store references differently, which decides what survives a copy to another hierarchy:

| | Asset refs (controllers, menus, params, materials) | Scene-object refs (bones, toggle targets, renderers) |
|---|---|---|
| **Modular Avatar** | direct | **path-hardened** — stored as an avatar-relative path, re-resolved at build |
| **VRCFury** | **GUID-hardened** (survive copying) | **raw pointers** — no hardening |

Consequences:

- **Modular Avatar copies itself.** Its scene refs are an avatar-relative path that re-resolves on
  whatever avatar the component lands on, so they **self-heal** across a copy. The one failure mode is a
  **renamed path segment** (e.g. a normalized `Body_base`→`Body_Base`): the lookup is exact, so it
  silently breaks. Repairing that is placement-time work, not a transplant tool's job.
- **VRCFury's scene refs are the only thing a transplant must actively repath.** Its asset refs are
  GUID-safe; its scene-object refs (ArmatureLink's prop bone, toggle/material/object targets, renderers)
  are raw pointers that **null out** when the component is copied or prefabbed across hierarchies. Only
  refs **inside the copy's reach** can be repathed; avatar-facing refs outside it are nulled by
  prefabbing and re-resolve when the prefab is later placed.
- **Which to reach for, composing a mergeable.** Modular Avatar by default — the self-heal makes it
  forgiving. VRCFury when a mergeable needs robust **animator merging**: the more it drives the avatar's
  FX (gestures moving ears, tail, expressions), the more VRCFury earns its place. Two hard rules: a
  module that both **moves** objects and **animates** them keeps both operations in one framework
  (cross-framework moves break clip paths); a module that may be **instanced more than once** needs
  VRCFury (per-instance parameter isolation by default).

## What you'll see when you inspect these components

- **Modular Avatar** — the avatar-relative reference appears as a path string (plus a cached object that
  is trusted only while it still belongs to the current avatar). `Merge Armature` fuses an outfit
  armature into the avatar's by **bone-name match** under a target (prefix/suffix strip); bones with no
  match are silently auto-created on the avatar (**phantom bones**), so a wrong-base merge reports no
  error while the outfit skins to bones that never move. `Bone Proxy`
  attaches by **humanoid-bone enum** + subpath — the most portable seam. `Mesh Settings` / `Blendshape
  Sync` carry path refs. The **menu system** is an authoring GO subtree (installer / group / item /
  toggle) whose targets are path refs; a `Menu Item` toggle with `automaticValue` + empty parameter
  **mints one synced bool named from its GameObject** at build, and the **reactive components**
  (`Object Toggle` / `Shape Changer` / `Material Setter`) fire from their host GO's active state —
  one menu bool drives a mesh toggle plus any number of declared reactions, all compiled into FX
  layers at build, no controller authored (the menu-authoring model: `menus.md`). `Merge Animator` carries a readable `pathMode`
  (`Relative`|`Absolute`) that sets the merged clips' **binding frame**: `Relative` ⇒ paths resolve
  against `relativePathRoot` (its `targetObject`, else `referencePath`, **empty ⇒ the component's own
  GameObject**); `Absolute` ⇒ avatar-root-relative.
- **VRCFury** — one feature per component. `Full Controller` merges a controller + menu + params
  (asset refs, GUID-safe); it **auto-detects each binding's frame** — prop-root vs avatar-root per
  binding, **preferring the prop (mount) root on ties**. `Armature Link` mirrors Merge Armature: the avatar side is a bone-enum/path
  (hardenable), the **prop side is a raw ref**. Toggles / object & material actions reference scene
  objects by **raw ref**. A `Toggle` feature generates the menu control, the parameter, *and* the FX
  layer at build from its declarative action list — VRCFury has **no reactive components**, so a
  toggle's side effects (hide the feet under shoes) stack as additional actions on that one Toggle,
  or as exclusive tags across several. A well-built prop is a **self-contained module** — own
  FX/menu/params + own logic, all-internal scene refs — attaching through a single Merge-Armature /
  Armature-Link / Bone-Proxy seam.

## Tooling implications

- Transplant/owning tools work on the **authoring layer** and must **preserve** non-destructiveness:
  reproduce Modular-Avatar-as-Modular-Avatar and VRCFury-as-VRCFury. Never flatten, bake, or re-author.
- **Copy from the standalone vendor prefab**, not an outfit already placed on an avatar — a placed
  component carries cached avatar-relative state that a blind copy would mis-resolve.
- A faithful copy reproduces the vendor's authoring so an owned (e.g. reproportioned) FBX is
  **drop-in-equivalent** to the vendor. Re-authoring discretion — cleaning up a messy prefab, customizing
  menus — is deliberate human work; placement itself is the `compose-mergeable` skill, which flags the
  menu/animator pass as a required follow-up outside its scope. Placing an **owned** mergeable also runs
  a provenance fit gate: `compose-mergeable` resolves the mergeable's stamped `(base, state)` (Blender's
  `avatarprep_` namespace) and compares it to the target base being composed onto — a mismatch, or either
  stamp missing, is a loud may-block **WARNING**, writes nothing, and routes back to `own-mergeable`
  (Decision 3), operator-overridable. Vendor/unstamped mergeables have no such stamp and fall back to
  bone-hit-rate instead. Repairing renamed paths splits
  by seam: **animation-clip bindings** on owned on-disk `.anim` assets are now in tooling scope
  (`RepathClips` / `OwnControllerClips`, directed by a caller that knows the moves), while the **Modular
  Avatar scene-ref** renamed-segment seam (above) stays in-scene placement/skill work.

See `unity.md` for the owning tool contracts and `workflow.md` for when to own vs. compose.
