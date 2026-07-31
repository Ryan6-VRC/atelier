# OSC — the avatar parameter wire

Primary reader: agent.

VRChat's OSC interface as it applies to the avatars we build and the rigs that drive them: what addresses exist, what a value on the wire means, and where the emulator's implementation differs from the client's. `vrc-bridge` is a *product* built on this wire and its design record travels with it — `vrc-bridge/docs/design.md` owns that, including its address census and every mapping decision. This file owns the protocol both ends speak.

Routes out, so nothing below is a second copy: parameter-name hazards and the compile advisory that surfaces them are `animator-schema.md`; the ~0.1 s sync tick, 8-bit quantization, and OSC's local-precision exception are `runtime.md` §Parameters; driving and reading OSC inside a play session is `verify.md` §OSC.

## Address families

- **`/avatar/parameters/<Name>`** — an avatar's expression parameters, both directions. `<Name>` is the parameter name *after* the client's rewriting, which is why a name carrying a space is a hazard rather than a spelling choice (`animator-schema.md`).
- **`/input/<Name>`** — client input commands, **inbound only**. These are not avatar parameters and nothing echoes them back under the same address; their effects surface as built-in parameters instead, so `/input/Vertical` moves the player and reads back as `VelocityZ`.
- **`/avatar/change`** — emitted with the avatar id when the worn avatar changes.

A bool travels as an OSC `T`/`F` type tag carrying no payload, an int as `,i`, a float as `,f`. A consumer that expects `0`/`1` ints for booleans silently sees no bools at all.

## Latching and momentary are opposite contracts, and a consumer cannot infer which it has

A **latching** parameter is driven in both directions by something outside the consumer and stays where it was put; a **momentary** one returns to zero on its own. The consumer's edge handling inverts between them: a mapping that acts on every transition is correct against a latch and double-acts against a momentary source, netting no change. Nothing on the wire distinguishes them — the value is a value — so the declaration has to travel with the parameter, per parameter rather than per rig. `design.md` §The muteproxy contract is the worked case, and the one that established the cost of leaving it unstated.

## The emulator carries OSC, and this is the whole surface

Everything here is asserted from `AvatarProject/Packages/lyuma.av3emulator/` (MIT, © Lyuma) and confirmed by measurement against a running play session.

**The lever is `LyumaAv3Runtime.EnableAvatarOSC = true`** on the local runtime, in play mode. Setting it adds and enables a `LyumaAv3Osc` component on the emulator control object, opens the socket, and binds it to that avatar. Nothing in the scene needs authoring first.

It listens on **9000** and sends to **127.0.0.1:9001** — VRChat's own convention, so a client written against the real thing needs no change. There is **no OSCQuery**: the package contains no service discovery of any kind, so nothing announces itself and nothing can be browsed for. Point at the port.

Four behaviours that shape anything built on it:

- **Emission is change-only, per Unity frame.** A value is sent when it differs from the last one sent for that address, so a static parameter goes quiet rather than streaming. `LyumaAv3Osc.resendAllParameters` forces a full re-send.
- **It emits more than its own config declares.** Parameters written through the SDK's animator-parameter-access path — contact-receiver and raycast outputs, measured — are pushed onto the wire even when absent from the generated OSC config, so an animator-only parameter is observable without appearing in any expression-parameters asset.
- **An inbound write lands on the same field as the `.expressionValue` drive route** (`verify.md` §Drive/observe). They are two writers to one value; use one or the other within a session, not both.
- **Addresses are built from the parameter name verbatim**, without the client's rewriting. So a name containing a space resolves one way here and another way in game, and it is exactly the names most likely to contain spaces — vendor and generated ones — that diverge. Cross-check anything name-sensitive against a real client.

No VRChat login is required; the config falls back to memory. When a login *is* present the emulator writes a generated config file into the real VRChat OSC directory, alternating between two names on each play entry — harmless, but it is a write outside the project.

`/input/` is implemented selectively. Movement and look (`Vertical`, `Horizontal`, `LookHorizontal`, the `Move*`/`Look*` bools), `Jump`, `Run` and `Voice` all act; `Use*`, `Grab*`, `Drop*`, `PanicButton`, `QuickMenu*` and `Comfort*` parse and do nothing. `Voice` reproduces the client's mute semantics — the rising edge toggles `MuteSelf`, the falling edge is a no-op — which makes a latching-source mapping testable without a headset.
