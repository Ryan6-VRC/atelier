# Base-body clothing (dress-up bases)

How a vendor avatar base is clothed — the regular vs. kisekae prefab split — and why hiding a base
garment is never just a mesh toggle. This is the domain the **`map-outfit-shapes`** skill executes and
the trap `compose-mergeable`'s quick de-conflict warns about. `menus.md` reuses the coupling model for
toggle authoring; `nondestructive.md` owns the framework mechanics.

## Regular base vs. kisekae base

A vendor base commonly ships as **two prefabs**: the **regular** base (`<Name>.prefab`) wearing a full
default costume, and a dedicated **kisekae** base (`<Name>_kisekae.prefab`) stripped to body +
underwear, no costume — sold to be dressed. Both share the same body. Some vendors ship only the
clothed base, or only **shader variants** of it (lilToon vs Poiyomi), all identically clothed — so
matching a base by shader still lands you on a dressed body.

**Compose onto the kisekae variant when the vendor ships one** — it is already undressed, so there is
little to de-conflict. Composing onto the **regular** base is **strip-then-dress**: disable the base
costume (and any underwear the outfit's own layer replaces), each with its coupled body shape. A
regular base's FX menu usually also carries an "undress" state that hides the costume — the same end
as the kisekae prefab, by a different route.

## The clothing↔blendshape coupling — the expensive trap

A base garment is frequently **coupled to blendshapes on the body mesh**: the body is authored
pre-collapsed under the garment so it can't clip through (shrink-the-limb shapes), and/or the garment
drives body shapes on when worn. **The mesh and its coupled shapes are one unit.** Disable the mesh
and leave the coupled shapes at their worn values and that body region stays deformed — **a missing
or mangled limb under the new outfit**, not a clean swap. A stocking mesh whose coupling shrinks the
legs, disabled without releasing that shape, leaves no legs.

The coupling is **not derivable from the mesh alone** and naming is only a hint — resolve it from the
FX graph.

**Shrink and hide travel together; over shared vertices they are almost never both on.** Two rules, each
sufficient: hiding a base mesh flips its paired `Shrink_*` off (mesh and shrink are one unit); and a
composed outfit that needed a base shape would drive it from its *own* `ShapeChanger`, so its absence
there means the base shape isn't wanted. Leave a base `Shrink_*` worn while a kept outfit `ShapeChanger`
shrinks the **same vertices** and the two subtractions stack into an **inverted mesh** — invisible to the
render sheet (the outfit covers it in T-pose) and to `CheckSeam`/`CheckAvatar` (neither reads coupling).
The shape map catches it by reasoning; `ReportShapeOverlap` measures the shared-vertex overlap that
confirms the stack once you have named the co-active shapes (the base worn `Shrink_*` and the outfit
`ShapeChanger`'s targets) — a `Report`, not a verdict: it locates the collision, you rule wanted-vs-defect.

**A foot-pose shape (a heel arch — `Heel_Feet`-style) is coupled to the worn footwear, not to a
garment mesh the graph names — resolve it declared-or-zero.** Ship the value the composed outfit's
own authoring declares (its `ShapeChanger` setting the heel pose); absent a declaration, 0 — the
fail-safe direction: an arched foot clips through a flat sole (visible from below), where a neutral
one merely under-fills an undeclared heel. Never classify footwear from a render — model vision
cannot tell a heel from a platform sole; an outfit that ships heels and declares no pose is residue
to name, not a render to read.

**Anti-clip has a second idiom: geometry deletion.** Beside the shrink-shape model this doc centers, an
outfit's MA `ShapeChanger` in **Delete** mode removes the overlapped base vertices outright — a live
idiom on real assets. Read the mode, not just the target (`ShapeChangeType` Delete=0/Set=1 —
`map-outfit-shapes`).

## The FX controller is the authoritative map

The base's **FX layers and their animation clips** encode the coupling: the state that *hides* a
garment is the same state that drives its coupled body blendshapes to their garment-off values. That
graph — not a naming convention — is the source of truth for "what else moves when this mesh goes
away." Read it (`ReportController` / `ReportClip`): find the garment's off state, and apply the values
it sets when you disable the mesh — **in the substrate that owns them at runtime**. An always-on
layer (weight 1, WD ON) gated on an expression parameter *re-applies* its param-selected state every
frame, so the shipped costume is the **expression-parameter defaults**, not the scene's static mesh
states: there the strip is a parameter-default flip, the same undress route the shipped menu drives.
Statics hold only where no runtime layer drives the property; on a driven one a static edit moves the
edit-time look and nothing else — how a double-dressed avatar passes every edit-time gate. A default
flip changes the shipped menu defaults: an operator call, authored per `menus.md`, verifiable only in
a play-mode read of the driven state.

Authority, high to low:

1. **The base's FX clips** for the garment's toggle — the declared coupling.
2. **Existing MA/VRCFury reactions** on the composed pieces reaching into the body mesh.
3. **Blendshape naming** (`Shrink_*`, `*_OFF`, a `(default)` suffix marking a ship-on shape) —
   *suggestive, never authoritative*; a hint to confirm against the graph, not to act on alone.
4. **Ask the user** — a mesh absent from the FX graph, or a base with no FX layer at all, has no
   declared coupling; the user is the reliable fallback. Do not guess a coupling into existence.

`RenderAvatar` can *confirm* a hypothesised coupling, but only by **before/after comparison** — grab the
region with the shape worn and again zeroed, and read the difference; never infer a coupling from a
single capture. A confirmation aid, not the basis for an edge.

## The menu is already there

These mesh+blendshape units are toggled as units by the base's **shipped FX layer and expression
menu**, carried on the `VRCAvatarDescriptor` (`expressionsMenu` / `expressionParameters` / the FX
playable layer) — a vendor base arrives menu-complete. Absent Modular Avatar / VRCFury components is
the **normal vendor state**, not a sign the avatar has no menu. Composing or de-conflicting an outfit
does not require authoring one; `author-menu` covers when new controls are actually warranted.
