# Tool & skill design for agents

Here the agent drives Unity and Blender directly; tools step in only for the repetitive,
deterministic, or error-prone slice where a script beats tokens. A tool is a power tool the agent
picks up and sets down inside a workshop it otherwise operates by hand — design for that handoff,
not for isolation.

- **A tool earns its place where a script beats tokens.** The default is the agent operating the
  substrate directly; build a tool for the repetitive, deterministic, or verify-heavy slice — not
  to wrap what the agent already does well by hand.
- **Pure core, UI-free.** Logic lives in directly-callable core functions, coupled to nothing —
  no selection, no window, no menu context. Every door (CLI, MCP, menu, UI) is a context-validating
  shim with zero logic: resolve inputs, call the core, return the result through the channel that
  invoked it. The **guarantee is that the core makes any door trivial to add**, not that every door
  exists — implement a door where someone reaches for it (a human-facing tool keeps its UI), and
  leave the rest unbuilt. What must never happen is logic living behind a face.
- **Speak the substrate's names.** Inputs and outputs use the handles the agent uses by hand —
  GameObject paths, bone/blendshape names, asset GUIDs — so it can move between your tool and raw
  Unity/Blender mid-task with no translation. Don't invent private handles that die the moment it
  drops back to the substrate.
- **Outputs chain into inputs.** A result carries the exact handles the next step needs — whether
  that step is another tool or a raw editor call — so the next moves are legible from the output
  itself and nothing is re-resolved. What a tool touched, it names.
- **Return what the agent can act on, windowed.** A PASS/FAIL verdict with named offenders, clean
  text, or images-as-images — addressable and capped, never a raw dump. A detail artifact
  (RunLog, snapshot, report) returns its path in-band with the summary. Representation matches
  intent; context is the budget.
- **One tool per intent.** Map a tool to what the agent is doing, not to endpoints or formats.
  Distinct intents are distinct tools that name each other, so the surface teaches its own
  navigation.
- **One grammar across the family.** Same concept, same name — across tools, parameters, result
  keys, menu paths, docs. Same kind of result, same envelope — one diagnostic shape, not one per
  tool. A new tool's interface should be guessable from the last one; rename to converge rather
  than alias; name a heuristic as a heuristic, not a fact.
- **The schema can't lie.** Descriptions and limits match real behavior; a misuse returns a
  refusal that names the fix — the error is part of the interface.
- **Say it once.** Per-tool detail in the tool; cross-cutting guidance at one entry point; never
  advertise a dead path — an unused affordance is a false steer.
