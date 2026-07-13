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

## The FX controller is the authoritative map

The base's **FX layers and their animation clips** encode the coupling: the state that *hides* a
garment is the same state that drives its coupled body blendshapes to their garment-off values. That
graph — not a naming convention — is the source of truth for "what else moves when this mesh goes
away." Read it (`ReportController` / `ReportClip`): find the garment's off state, and statically apply
the body-blendshape values it sets when you disable the mesh.

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
