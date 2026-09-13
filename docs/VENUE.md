# Venue rules

These bind, on any write inside a Unity venue — a working venue under this workspace or any other Editor on this machine. `LAYOUT.md` owns where a thing is filed (the trees, durable-vs-disposable, the sanctioned `Vendor/` writes); this file owns what an agent may do once it is filing there. Anything conditional — which item, which route, which source trap — belongs to the venue's own intake prose, not here.

> [!CAUTION]
> ## NEVER COMMIT TO METAREPO `main` — BRANCH OR WORKTREE ONLY

> [!CAUTION]
> ## VENUE PROSE RECORDS THE ASSET AS IT IS. NEVER HOW IT GOT HERE.
>
> No past uploads, no divergence-from-live, no re-baked-after, no gate roll-calls, no legacy comparisons, no attempts, no dates, no findings. **No measurements** — if a door can re-derive the number, run the door; if it cannot, the number is history. A measurement is written down only when it is a standing constraint on the next edit, and then it is written as the constraint, not as the reading.

- **A source venue is read-only.** When a venue is built by curating from another Editor, nothing writes to that other Editor. The one sanctioned source write: unlocking locked Poiyomi materials on a hash-verified backup copy of their folder, restored afterwards.
- **One item at a time, and nothing it pulls in by default.** Name each dependency, classify it, and ask before bringing anything that is itself a system — a hair that drags in a whole ear/puppet rig is the standing shape.
- **Structure is the venue's (`LAYOUT.md`); content is copied as file + `.meta`** so GUIDs and every reference survive. Vendor content never crosses as files — re-import it from the vendor asset library through `import-vendor-asset`.
- **A fit done by hand in Unity is re-derived in Blender.** Prefab transform overrides on bones are a proportion edge in disguise: the reference measurement, never the thing copied.
- **Fit references are linked, not appended.** A costume or hair `.blend` needs the head or body only as a read-only fit target, so link the base's `Armature` and body meshes as **objects** — never a collection instance, which the exporter would expand into unrigged geometry — from the venue base `.blend` by relative `//` path. The avatarprep doors enforce this; one `.blend` per owned asset, in its bucket.
- **A vendor-GUID verdict is not proof the bytes are vendor.** A provenance check that short-circuits on the GUID never hashes, so a source file edited in place under a vendor GUID still classifies vendor. Byte-compare every such material an item depends on against the venue's vendor copy before declining to copy it.
- **Verify by the venue's doors:** `CheckPackage` after every import, `CheckAvatar` on anything placed, `CheckSeam` on any worn mergeable, a play-mode bake before calling a composed thing done (`verify.md`).
