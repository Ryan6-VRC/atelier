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
union-merged — `compare_armatures`, `blender.md`), which runs before Unity ever sees the asset.

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
- **The build-order mechanism behind that first rule.** MA passes run inside NDMF's preprocess hook
  (`callbackOrder -11000`); VRCFury applies at `-10000` and re-resolves every merged binding against
  the **post-MA** hierarchy by a nearest-match prefix walk up from the `FullController`'s object
  (`ClipRewritersService.CreateNearestMatchPathRewriter`) — it does not track objects across moves. A
  node moved *with* the module (its root MA-anchored) keeps a component-relative path and is safe; a
  binding pathing through a node MA moved *out* of the module subtree (an interior `BoneProxy`) finds
  no valid prefix and **silently vanishes from the merged FX** — no error, no warning. The reverse
  breaks symmetrically: an MA-merged clip pathing through a node VRCFury later moves (`ArmatureLink`)
  froze its paths at `-11000` and nothing repaths after. The same escape hits VRCFury's
  **parameter-name rewrite**: `FullControllerBuilder` prefixes the param fields of
  receivers/raycasts/physbones only within its own subtree, so a param-carrying component MA moved out
  keeps the bare name and its writes bridge to nothing (a receiver under a moved anchor reads 0
  forever). Hence behavior lives in VRCFury, MA touches only anchor nodes carrying no animated
  bindings, and a module **senses from inside** — constrain a sense point to the anchor GO, never
  parent it there.

## What you'll see when you inspect these components

These summaries orient; the **authority is the package source** — Modular Avatar under
`Packages/nadena.dev.modular-avatar/`, VRCFury under `Packages/com.vrcfury.vrcfury/`. For what a
component does to *your* case — a mechanism, an edge, an exact field — read it there or measure live;
don't assert a mechanism from the summary alone.

- **Modular Avatar** — the avatar-relative reference appears as a path string (plus a cached object that
  is trusted only while it still belongs to the current avatar). `Merge Armature` fuses an outfit
  armature into the avatar's by **bone-name match** under a target (prefix/suffix strip), and its two
  branches decide what an owned base should carry. A **matched** bone *zips*: the outfit's bone collapses and
  its references retarget onto the avatar's — unless it carries a Unity built-in constraint, which forces the
  kept branch under a scale-preserving intermediate parent. An **unmatched** bone is reparented into the
  avatar hierarchy and **kept** as the outfit's own — the ordinary case for outfit-specific chains (skirt,
  ribbon), not a defect. Children of a physbone root are skipped entirely, left on the outfit side, and
  **fatal** if one names a humanoid bone. The **phantom-bone** failure is a *whole-armature* mismatch:
  nothing zips, no error is reported (there is no zero-match diagnostic), and the outfit skins to a private
  copy of the armature the avatar never animates. Corollary for owning: a base retaining a chain it does not
  weight flips a mergeable from the kept branch to the zipped one, so whatever the base carries on those
  bones — constraints especially — inherits the mergeable's geometry. The merge is **identity-preserving**:
  it retargets bones exactly as they sit in the scene and reconciles nothing, so a mismatched rest pose
  bakes through unchanged — what you see pre-build is what ships. `Bone Proxy`
  attaches by **humanoid-bone enum** + subpath — the most portable seam. `Mesh Settings` / `Blendshape
  Sync` carry path refs. The **menu system** is an authoring GO subtree (installer / group / item /
  toggle) whose targets are path refs — it *adds to* the avatar's descriptor-borne menu
  (`expressionsMenu`/`expressionParameters`/FX), not the sole menu source; a `Menu Item` toggle with `automaticValue` + empty parameter
  **mints one synced bool** at build, named `__MA/AutoParam/<GOName>$<hash>` (a hashed internal name,
  **not** the GameObject name), and the **reactive components**
  (`Object Toggle` / `Shape Changer` / `Material Setter`) fire from their host GO's active state —
  one menu bool drives a mesh toggle plus any number of declared reactions, all compiled into FX
  layers at build, no controller authored (the menu-authoring model: `menus.md`). `Merge Animator` carries a readable `pathMode`
  (`Relative`|`Absolute`) that sets the merged clips' **binding frame**: `Relative` ⇒ paths resolve
  against `relativePathRoot` (its `targetObject`, else `referencePath`, **empty ⇒ the component's own
  GameObject**); `Absolute` ⇒ avatar-root-relative.
- **VRCFury** — one feature per component. `Full Controller` merges a controller + menu + params
  (asset refs, GUID-safe); it **auto-detects each binding's frame** — prop-root vs avatar-root per
  binding, **preferring the prop (mount) root on ties**. `Armature Link` mirrors Merge Armature: the avatar side is a bone-enum/path
  (hardenable), the **prop side is a raw ref**; its analogous align-to-base options apply **at build**,
  not in edit mode, so MA's "what you see is what bakes" invariant does not hold for VRCFury. Toggles / object & material actions reference scene
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
- **Don't lean on MA/VRCFury to move an armature into alignment.** The two apply it differently — MA as a
  one-shot edit-mode action, VRCFury at build — so the result isn't predictable across systems. Measure the
  seam mechanically instead: **`CheckSeam`** (`unity-tools.md`) reflects the seam mapping and gates world-space
  coincidence of the **weighted humanoid bones** — the bones with a knowable "must be zero" contract, since
  a correct mergeable duplicates the base armature (correct fits land ≤~0.01mm, a real misfit tens of mm).
  Non-humanoid bones — physbone/collider tips — legitimately deviate up to ~75mm on a correct fit and are
  never a fit signal. A PASS is therefore evidence about the humanoid seam alone, and says nothing about
  clothing and helper chains — where a merge's structural surprises actually live. Where a genuine
  misalignment needs correcting, make the transform edit **in code**; framework auto-align is an operator
  convenience, not an agent's alignment path.
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

See `unity-tools.md` for the transplant/owning tool contracts (controllers: `animator.md`) and
`workflow.md` for when to own vs. compose.
