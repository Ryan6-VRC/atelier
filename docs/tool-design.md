# Tool, skill & prose design for agents

A tool is a power tool the agent picks up and sets down inside a workshop it otherwise operates by hand — design for that handoff, not for isolation. The same lens covers prose: docs, skills, READMEs, and diagnostics are interfaces to knowledge for the same reader. An agent-directed artifact gives the outcome and the constraints, not the procedure. §Tools governs the tool surface, the sections after it where knowledge lives; how the sentences get made is the `write-for-agents` skill's (`.claude/skills/`): a rule about an artifact class lives here, a sentence-level rewrite move lives there.

## Tools

- **A tool earns its place where a script beats tokens.** The default is the agent operating the substrate directly; build for the repetitive, deterministic, or verify-heavy slice — not to wrap what the agent already does well by hand.
- **Pure core, UI-free.** Logic lives in directly-callable core functions, coupled to nothing — no selection, no window, no menu context. Every door (CLI, MCP, menu, UI) is a context-validating shim with zero logic: resolve inputs, call the core, return the result through the channel that invoked it. The **guarantee is that the core makes any door trivial to add**, not that every door exists. What must never happen is logic living behind a face.
- **Speak the substrate's names.** Inputs and outputs use the handles the agent uses by hand — GameObject paths, bone/blendshape names, asset GUIDs — so it can move between your tool and raw Unity/Blender mid-task with no translation. Never invent private handles that die the moment it drops back to the substrate.
- **Outputs chain into inputs.** A result carries the exact handles the next step needs, tool or raw editor call alike, so nothing is re-resolved. What a tool touched, it names.
- **Return what the agent can act on, windowed.** A PASS/FAIL verdict with named offenders, clean text, or images-as-images — addressable and capped, never a raw dump. A detail artifact (RunLog, snapshot, report) returns its path in-band with the summary.
- **One tool per intent.** Map a tool to what the agent is doing, not to endpoints or formats. Distinct intents are distinct tools naming each other, so the surface teaches its own navigation.
- **One grammar across the family.** Same concept, same name — across tools, parameters, result keys, menu paths, docs. Same kind of result, same envelope — one diagnostic shape, not one per tool. A new tool's interface should be guessable from the last one; rename to converge rather than alias; name a heuristic as a heuristic, not a fact. On an `[AgentTool]` class: **the primary door is always `Run`** — the class already carries the verb (`<Verb><Subject>`, below), so the door never repeats it — every other member is a secondary with its own subject, and the verdict **label** names the action rather than the door, which is the only thing telling a multi-door class's console lines apart. `tools/sync_tool_inventory.py` asserts the `Run` half.
- **The read-verb set is closed; route by observable output.** Every tool is `<Verb><Subject>` (Unity PascalCase, Blender `verb_noun`). Read tools pick their verb from what they *return*, not why they were called: `Report` (descriptive digest of one subject — may classify, never emits a verdict token), `Check` (a PASS/FAIL gate on whether a state holds), `Compare` (a two-subject diff payload; a bare two-subject go/no-go with no diff is a `Check`), `Render` (an image). Write tools use a specific action verb; that set is open. `AgentInspector` and `DecompileController` are a closed, enumerated pair of exceptions, not a category a new tool can qualify into. Dry-run is `whatIf` (bool); its `whatIf`/`whatif` casing is idiomatic per language.
- **The schema can't lie.** Descriptions and limits match real behavior; a misuse returns a refusal that names the fix — the error is part of the interface.
- **Legibility over edge-case cleverness.** An interface that is intuitive to drive and a diagnostic that can be *trusted* beat silently handling a rare case in a way that is hard to reason about.
- **A sub-repo reaches up only for what cannot ship.** The reach back takes only infrastructure with no version to publish (the test venue, its provisioner, the editor resolver, the scratch pile), through a root parameter that defaults by discovery and **refuses by name** when the workspace is absent — never a relative hop or a guessed fallback. Anything that *could* ship as a VPM package must, in `vrc-unity-tools`, where the seam is versioned. `vrc-patterns/tools/gate.ps1` is the sole instance.
- **Say it once.** Per-tool detail in the tool; cross-cutting guidance at one entry point; never advertise a dead path — an unused affordance is a false steer.

## Where knowledge lives — the routing ladder

Multi-rooted, defined by residency and trigger — not a single chain of hops:

- **Resident** (in every session, paying rent every session): CLAUDE.md, skill *descriptions*, tool-emitted diagnostics. A resident line must earn its rent every session; rare-case depth here is a defect — lift it (§Lifting) or push it down the ladder.
- **One hop**: `docs/` domain files, routed by CLAUDE.md's read-when index. Knowledge a whole class of work needs lives in the doc that class always reads, and the read-when line must say so — corpus-wide doctrine in a conditionally-routed doc is invisible to most of its readers. **Depth pays rent per reader, not per fact:** a component almost no session in that class touches earns only what changes *planning*, the measured surface routed to the pattern entry that measured it (`VRCRaycast` in `runtime.md` is the worked demotion).
- **Trigger-gated**: skill *bodies* — the process, gates, and judgment for one task shape; loaded on task match, not reached by hops.
- **Deep**: pattern and reference entries — narrow precedent, usually narrow *because* it takes a working rig to express; routed from the doc that names it.
- **Machine-fired**: checks, for traps whose biting circumstance is detectable (§Lifting).

Every fact has one canonical home; every other mention links to it.

One standing route for the workspace's own checks: a linked worktree carries only tracked files, so anything reading the gitignored `vrc-*` siblings, the untracked working venues, or `docs/local/` resolves the **main checkout** first — canonical in `tools/atelier_paths.py` and `Get-AtelierMainCheckout` in `tools/test-venue-common.ps1`. A new check imports one of those, never a fresh `__file__`/`$PSScriptRoot` walk.

## Duplication: managed echoes only

Unmanaged duplication — one fact grown into two homes, neither owning it — is a violation; route instead. Durable, salience-requiring content may be deliberately **echoed**: the echo names its canonical home, is intentionally the compressed form, and the pair's drift is checkable — by machine (README ↔ TOOLS.md, pre-commit-mirrored) or by a declared review invariant (vrc-patterns catalog row ↔ entry lead). Both criteria are required, so churning content and rare-but-important content both route rather than echo. Verbatim strings (format strings, exact constants) are quoted once, at the canon; every other site routes to the quote.

## What the call already teaches

Audience defines governance, not file type: a check's emitted text is agent-directed prose at the resident tier — it rots, duplicates, and contradicts like any paragraph — while the logic around it stays code, governed by tests and review. Agent-facing strings are born only at a repo-declared, closed set of diagnostic carriers (refusal funnels, offender/lint fields, typed refusal exceptions, line grammars) — never at a raw log call — so carrier call sites are the extractable audit surface.

That emitted text is therefore prose with a declared home, and a doc line restating it is duplication under §Duplication — the economics being §Lifting's: prose pays rent every session, the emit fires only when it matters. Output shape is the tool's to declare and the doc's to omit: summary fields, column and cell text, legends, verdict tokens, refusal strings, artifact layout. A verbatim quote of an emitted string is the sharpest case, drifting silently because nothing checks the pair. What the doc keeps is what no call returns — which door, when to reach for it, and the traps where calling it *correctly* teaches the wrong thing.

## Sourcing: bound the claim, never the confidence

An unattributed claim here is asserted as known; that is the default and it is not hedged. An attribution earns its words only by bounding what the claim *covers* — the venue a runtime fact was established in, where another could disagree (`in-client` / `in play` / `in av3emu`), or a figure that is itself the fact. A bare `(measured)` bounds nothing and costs more than its word: marking one claim measured casts doubt on every neighbour carrying no mark. Where a claim is genuinely thin, write the unknown as a scope bound in the claim's own voice — "X holds; whether Y does is not established" — never as a confidence marker on X.

## Lifting traps into checks

A prose trap is lifted into a tool-emitted check when both hold: the biting circumstance is machine-recognizable **at an existing chokepoint the agent already passes through** (compile, import, PlayGate, an MCP call), and the evaluation there is judgment-free — assert a state, never infer a purpose. The rarer and more conditional the trap, the stronger the lift: standing prose pays rent every session, while a check costs nothing until the circumstance arrives, then fires with perfect timing. Ratchet: the prose is deleted **only in the same change that lands the check**, and the check must cover the doors agents actually use. After a lift the check self-describes at fire time, so the doc names the mechanism only where its existence changes planning (one clause, the tool name as the durable handle) and never restates what the check enforces. A pure-reaction trap gets no doc line at all.

## The governed fence and its constants

Governed prose = tracked `.md` under the fence below, plus agent-facing diagnostics. The fence is a predicate, not a path list; binding prose found outside it is a finding to surface, not a new tier. Mechanical checks read these constants — they never embed copies:

```yaml
# prose-policy constants — read by the workspace prose checks
governed_fence:
  roots:                # the meta-repo and every vrc-* sibling
    - "."
    - "vrc-*"
  not_ignored: true     # would-be-tracked: check-ignore, so files still being authored count
  glob: "**/*.md"
  exclude:
    - test-output/
    - references/
    - docs/local/
```

The fence bounds *enforcement*, not advice. `tools/prose-hook.ps1` nudges on any markdown the agent authors in the workspace — ignored and untracked files included — and reads no constant here. A wider write-time reach than commit-time gate is the intent, not drift to reconcile.
