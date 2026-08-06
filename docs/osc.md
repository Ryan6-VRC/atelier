# OSC — the avatar parameter wire

Primary reader: agent.

VRChat's OSC interface as it applies to the avatars we build and the rigs that drive them: what addresses exist, what a value on the wire means, and where the emulator's implementation differs from the client's. `vrc-bridge` is a *product* built on this wire and its design record travels with it — `vrc-bridge/docs/design.md` owns that, including its address census and every mapping decision. This file owns the protocol both ends speak.

Routes out, so nothing below is a second copy: parameter-name hazards and the compile advisory that surfaces them are `animator-schema.md`; the ~0.1 s sync tick, 8-bit quantization, and OSC's local-precision exception are `runtime.md` §Parameters; driving and reading OSC inside a play session is `verify.md` §OSC.

## Address families

- **`/avatar/parameters/<Name>`** — an avatar's expression parameters, both directions. `<Name>` is the parameter name *after* the client's rewriting, which is why a name carrying a space is a hazard rather than a spelling choice (`animator-schema.md`).
- **`/input/<Name>`** — client input commands, **inbound only**. These are not avatar parameters and nothing echoes them back under the same address; their effects surface as built-in parameters instead, so `/input/Vertical` moves the player and reads back as `VelocityZ`.
- **`/avatar/change`** — **both directions**, carrying an avatar id as `,s`. Emitted when the worn avatar changes; sent *in*, it changes the worn avatar, accepting only ids in the player's favorites, recents, own uploads, or purchases. **Inbound carries no outcome**: the client re-emits the id it was *sent* within milliseconds, identically for an ineligible or malformed one, and never again when the avatar actually loads — so the echo proves receipt and a swap's success is not observable here — nor from the readable OSCQuery node of the same name, which reports the last id *requested* and adopts even one no avatar owns, whatever its `DESCRIPTION` claims (`verify.md` for what is). **The reference pages document the outbound direction alone**, so read the inbound half off VRChat's patch notes (2025.1.2, widened in 2025.4.2) and do not re-narrow this line from a reference page that omits it. Eligibility is the patch notes'; the echo and node behaviour is measured.

A bool travels as an OSC `T`/`F` type tag carrying no payload, an int as `,i`, a float as `,f`.

## OSCQuery serves the parameter surface, per node

The client's OSCQuery server (advertised over mDNS as `_oscjson._tcp`, floating HTTP port) answers a single-node GET per parameter: `/avatar/parameters/<Name>` returns a JSON node whose `VALUE` is the live value — unsynced parameters included, at full unclamped local precision (an unsynced Int default of 1000 reads back 1000). The tree is built from the generated config, so an animator-only parameter 404s, and it follows the worn avatar: while no worn avatar declares the parameter the node 404s rather than serving stale state, and after `/avatar/change` the new avatar's value was served within 0.14 s (one measurement, one client build, 2026-08-02). The emulator serves none of this (below). vrc-bridge's own served tree and its consumption of this surface are `vrc-bridge/docs/design.md`'s.

## Argument types are exact, and a mismatch is usually silent

**This is the rule that costs the most time when it is not known.** Inbound dispatch is on the argument's runtime type with no coercion anywhere: an int writes bool and int parameters and never a float, a float writes only floats. So `/avatar/parameters/MyFloat` sent an int `1` changes nothing at all. Sending `1` where `1.0` was meant is the single most common way for a correct-looking rig to do nothing.

Whether you are told depends on which path the parameter takes, and the quiet path is the one this channel is most useful for. A parameter declared in the expression-parameters asset is checked against the generated config and a mismatch is logged; an **animator-only** parameter — the kind reachable here and nowhere else — takes the unchecked path and the write is dropped in silence. `/input/` never warns at all: its float reader yields 0.0 for anything that is not a float and its bool reader yields false for anything that is not a bool or an int, so `/input/Vertical=1` reads as zero and `/input/Jump=1.0` as false.

Two mismatches throw instead of passing quietly, which at least makes them visible: `/input/Horizontal` unboxes its argument as a float directly where `Vertical` goes through the tolerant reader, and an int-typed parameter sent a bool casts a boxed bool to int.

**The unchecked path is not reliably reachable at all on the live client, and the emulator will not tell you.** Correctly-typed writes to an animator-only Int were dropped in silence on one avatar build (the parameter appeared only in transition conditions) and applied on another (drivers also wrote it) — mechanism unsettled, one client build, 2026-08-02 — while the emulator applies them unconditionally. So a parameter OSC must write gets declared in the expression parameters even when nothing syncs it (unsynced costs no sync bits); leave nothing OSC-written animator-only.

## Latching and momentary are opposite contracts

A **latching** parameter is driven both directions by something outside the consumer and stays where it was put; a **momentary** one returns to zero on its own. A consumer that acts on every transition is correct against a latch and double-acts against a momentary source, netting no change. Nothing on the wire distinguishes them, so the declaration travels with the parameter, per parameter rather than per rig. `design.md` §The muteproxy contract is the worked case.

## The emulator carries OSC, and this is the whole surface

Asserted from `AvatarProject/Packages/lyuma.av3emulator/` (MIT, © Lyuma) and confirmed by measurement against a running play session.

**The lever is `EnableAvatarOSC` on the local runtime** (`verify.md` §OSC has the call). Setting it adds and enables the OSC component on the emulator control object, opens the socket, and binds it to that avatar, with nothing to author in the scene first. It **self-clears** if the socket fails to open or the bound descriptor stops matching, so a rig that looks enabled and is silent is worth re-reading rather than re-sending.

It listens on **9000** and sends to **127.0.0.1:9001** — VRChat's own convention, so a client written against the real thing needs no change. **A live VRChat client running on the same desktop holds 9000 for as long as it runs**, so `EnableAvatarOSC` silently no-ops on that machine until the client closes — the common cause behind the self-clear above, not a separate failure mode. There is **no OSCQuery**: the package contains no service discovery of any kind, so nothing announces itself and a consumer must be pointed at the port.

- **Emission is change-only, per Unity frame.** A static parameter goes quiet rather than streaming; `resendAllParameters` forces a full re-send.
- **It emits more than its own config declares.** Parameters written through the SDK's animator-parameter-access path — contact-receiver and raycast outputs, measured — reach the wire even when absent from the generated config, so an animator-only parameter is observable without appearing in any expression-parameters asset.
- **Inbound writes land on the same value the `.expressionValue` drive route writes** (`verify.md` §Drive/observe). Two writers, one value; use one per session.
- **Addresses are built from the parameter name verbatim**, without the client's rewriting, so a name containing a space resolves one way here and another in game. Cross-check anything name-sensitive against a real client.
- **Every datagram received in a frame is applied, in order** — the socket's queue is drained whole. A burst that sets and clears within one frame therefore lands as two writes here, so drive a value once per frame and read the result rather than pulsing in a tight loop.
- **`/avatar/change` is outbound-only here.** The emulator builds it in `GetOSCDataInto` and implements no inbound handler for it, so an avatar swap driven over OSC cannot be round-tripped in this venue at all — and since the address is a client command rather than parameter traffic, `verify.md`'s exemption that keeps parameter claims out of the boot tier does not reach it. There is also nothing for it to switch *to*: the emulator runs the avatar in the scene.

No VRChat login is required; the config falls back to memory. With a login present the emulator writes a generated config file into the real VRChat OSC directory, alternating between two names per play entry — harmless, but a write outside the project.

`/input/` is implemented selectively, and the gaps do not follow the naming. **Acting:** `Vertical`, `Horizontal`, `LookHorizontal`, `MoveForward`, `MoveBackward`, `MoveLeft`, `MoveRight`, `LookLeft`, `LookRight`, `Jump`, `Run`, `Voice`. **Parsed and ignored:** `MoveHoldFB`, `SpinHoldCwCcw`, `SpinHoldUD`, `SpinHoldLR`, `UseAxisRight`, `GrabAxisRight`, `UseLeft`/`UseRight`, `GrabLeft`/`GrabRight`, `DropLeft`/`DropRight`, `ComfortLeft`/`ComfortRight`, `PanicButton`, `QuickMenuToggleLeft`/`QuickMenuToggleRight`. **Absent entirely**, reaching the unrecognized-command warning: `LookVertical`. `Voice` reproduces the client's mute semantics — the rising edge toggles `MuteSelf`, the falling edge is a no-op — which makes a latching-source mapping testable without a headset.
