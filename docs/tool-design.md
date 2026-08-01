# Tool, skill & prose design for agents

Here the agent drives Unity and Blender directly; tools step in only for the repetitive, deterministic, or error-prone slice where a script beats tokens. A tool is a power tool the agent picks up and sets down inside a workshop it otherwise operates by hand — design for that handoff, not for isolation. The same lens covers prose: docs, skills, READMEs, and diagnostics are interfaces to knowledge for the same reader. Capable models do their best work when given **tools and discretion** — an agent-directed artifact gives the outcome and the constraints, not the procedure. §Tools governs the tool surface, and the sections after it govern where knowledge lives; how the sentences get made is the `write-for-agents` skill's (`.claude/skills/`): a rule about an artifact class lives here, a sentence-level rewrite move lives there.

## Tools

- **A tool earns its place where a script beats tokens.** The default is the agent operating the substrate directly; build a tool for the repetitive, deterministic, or verify-heavy slice — not to wrap what the agent already does well by hand.
- **Pure core, UI-free.** Logic lives in directly-callable core functions, coupled to nothing — no selection, no window, no menu context. Every door (CLI, MCP, menu, UI) is a context-validating shim with zero logic: resolve inputs, call the core, return the result through the channel that invoked it. The **guarantee is that the core makes any door trivial to add**, not that every door exists — implement a door where someone reaches for it (a human-facing tool keeps its UI), and leave the rest unbuilt. What must never happen is logic living behind a face.
- **Speak the substrate's names.** Inputs and outputs use the handles the agent uses by hand — GameObject paths, bone/blendshape names, asset GUIDs — so it can move between your tool and raw Unity/Blender mid-task with no translation. Don't invent private handles that die the moment it drops back to the substrate.
- **Outputs chain into inputs.** A result carries the exact handles the next step needs — whether that step is another tool or a raw editor call — so the next moves are legible from the output itself and nothing is re-resolved. What a tool touched, it names.
- **Return what the agent can act on, windowed.** A PASS/FAIL verdict with named offenders, clean text, or images-as-images — addressable and capped, never a raw dump. A detail artifact (RunLog, snapshot, report) returns its path in-band with the summary. Representation matches intent; context is the budget.
- **One tool per intent.** Map a tool to what the agent is doing, not to endpoints or formats. Distinct intents are distinct tools that name each other, so the surface teaches its own navigation.
- **One grammar across the family.** Same concept, same name — across tools, parameters, result keys, menu paths, docs. Same kind of result, same envelope — one diagnostic shape, not one per tool. A new tool's interface should be guessable from the last one; rename to converge rather than alias; name a heuristic as a heuristic, not a fact.
- **The read-verb set is closed; route by observable output.** Every tool is `<Verb><Subject>` (Unity PascalCase, Blender `verb_noun`). Read tools pick their verb from what they *return*, not why they were called: `Report` (descriptive digest of one subject — may classify, never emits a verdict token), `Check` (a PASS/FAIL gate on whether a state holds), `Compare` (a two-subject diff payload; may carry a summary verdict — a bare two-subject go/no-go with no diff is a `Check`), `Render` (an image). Write tools use a specific action verb; that set is open. The only sanctioned exceptions are a closed, enumerated pair — `AgentInspector` (the generic, domain-blind walk) and `DecompileController` (emits re-editable YAML, the codec-inverse of `CompileController`) — not a category a new tool can qualify into. Dry-run is `whatIf` (bool); its `whatIf`/`whatif` casing is idiomatic per language.
- **The schema can't lie.** Descriptions and limits match real behavior; a misuse returns a refusal that names the fix — the error is part of the interface.
- **Legibility over edge-case cleverness.** Tools are read and driven by frontier models: an interface that's intuitive to drive and a diagnostic that can be *trusted* beat silently handling a rare case in a way that's hard to reason about.
- **Say it once.** Per-tool detail in the tool; cross-cutting guidance at one entry point; never advertise a dead path — an unused affordance is a false steer.

## Where knowledge lives — the routing ladder

Multi-rooted, defined by residency and trigger — not a single chain of hops:

- **Resident** (in every session, paying rent every session): CLAUDE.md, skill *descriptions*, tool-emitted diagnostics. A resident line must earn its rent every session; rare-case depth here is a defect — lift it (§Lifting) or push it down the ladder.
- **One hop**: `docs/` domain files, routed by CLAUDE.md's read-when index. Knowledge a whole class of work needs lives in the doc that class always reads, and the read-when line must say so — corpus-wide doctrine in a conditionally-routed doc is invisible to most of the readers who need it. **Depth pays rent per reader, not per fact:** a component almost no session in that class touches earns only what changes *planning*, with the measured surface routed to the pattern entry that measured it (`VRCRaycast` in `runtime.md` is the worked demotion).
- **Trigger-gated**: skill *bodies* — the process, gates, and judgment for one task shape; loaded on task match, not reached by hops.
- **Deep**: pattern and reference entries — narrow precedent that never rose into docs; reached via catalog.
- **Machine-fired**: checks, for traps whose biting circumstance is detectable (§Lifting).

Every fact has one canonical home; every other mention is a **route** — "X owns Y", "Contract: `unity-tools.md`" — paired with a guard against restating ("links, not restates"). A route without a guard is where drift starts. A high-fan-out fact names its canon at every echo: three files citing three different homes for one claim is a defect even while the copies still agree.

## Duplication: managed echoes only

Unmanaged duplication — one fact grown into two homes, neither owning it — is a violation; route instead. Durable, salience-requiring content may be deliberately **echoed**: the echo names its canonical home, is intentionally the compressed form, and the pair's drift is checkable — by machine (README ↔ TOOLS.md, pre-commit-mirrored) or by a declared review invariant (vrc-patterns catalog row ↔ entry lead). Both criteria are required: churning content makes every echo a liability, and rare-but-important content fails salience by definition — it routes, never echoes. Verbatim strings (format strings, exact constants) are quoted once, at the canon; every other site routes to the quote.

## Lifting traps into checks

A prose trap is lifted into a tool-emitted check when both hold: the biting circumstance is machine-recognizable **at an existing chokepoint the agent already passes through** (compile, import, PlayGate, an MCP call, gate admission, a pre-commit), and the evaluation there is judgment-free — assert a state, never infer a purpose. The rarer and more conditional the trap, the stronger the lift: standing prose pays rent every session, while a check costs nothing until the circumstance arrives, then fires with perfect timing. Ratchet: the prose is deleted **only in the same change that lands the check**, and the check must cover the doors agents actually use — a check behind a door the agent bypasses is a dead affordance. After a lift, the check self-describes at fire time — the refusal names the fix and points into a doc where deeper context exists; the doc names the mechanism only where its existence changes planning (one clause, the tool name as the durable handle) and never restates what the check enforces. A pure-reaction trap gets no doc line at all.

## Diagnostics are governed prose

Audience defines governance, not file type: a check's emitted text is agent-directed prose at the resident tier — it rots, duplicates, and contradicts like any paragraph — while the logic around it stays code, governed by tests and review. Agent-facing strings are born only at a repo-declared, closed set of diagnostic carriers (refusal funnels, offender/lint fields, typed refusal exceptions, line grammars) — never at a raw log call — so carrier call sites are the extractable audit surface. A message that encodes domain knowledge is an echo of its doc and follows §Duplication: compressed, with the canon cited at the emit site.

## The governed fence and its constants

Governed prose = tracked `.md` under the fence below, plus agent-facing diagnostics. The fence is a predicate, not a path list; binding prose found outside it is a finding to surface, not a new tier. Mechanical checks read these constants — they never embed copies:

```yaml
# prose-policy constants — read by the workspace prose checks
governed_fence:
  roots: [".", "vrc-*"]          # the meta-repo and every vrc-* sibling
  not_ignored: true              # would-be-tracked: check-ignore, so files still being authored count
  glob: "**/*.md"
  exclude: [test-output/, references/, docs/local/]
docs_max_hops_from_claude_md: 1  # core knowledge sits at most one hop out
```

The fence bounds *enforcement*, not advice. `tools/prose-hook.ps1` nudges on any markdown the agent authors in the workspace — ignored and untracked files included, since a file does not stop being worth writing well because git declines to store it — and reads no constant here. A wider write-time reach than commit-time gate is the intent, not drift to reconcile.
