---
name: write-for-agents
description: Use when writing or tightening prose an agent will read — docs, skills, runbooks, CONVENTIONS, handoffs, memory files, diagnostic message text — or when the prose hook fires on an .md edit. Not where a fact lives (docs/tool-design.md owns that); not human-only prose — though choosing that register is step 1 here.
---

# Write for agents

Declare the reader, then carve. Settle a fact's placement against `docs/tool-design.md` first; this skill is how the sentences get made once the home is chosen.

## 1. Declare the reader

Three registers; pick before writing, and a new standalone artifact states its choice (the CONVENTIONS files' "primary reader:" line is the pattern):

- **Agent-facing** — docs, skills, handoffs, diagnostics: the reader is a model at your own capability level with the repo open. Full-strength craft below.
- **Dual-register** — artifacts with a human lead and an agent body (pattern READMEs): one document ordered by depth, each fact once, on the audience gradient — never parallel human/agent halves (`vrc-patterns/CONVENTIONS.md` owns the shape).
- **Human-facing** — end-user READMEs, release notes: normal technical writing. None of the compression below applies; do not squish a human document into agent shorthand.

## 2. The craft (agent-facing)

Verbosity is audience miscalibration: the default imagined reader is a nervous junior who needs motivation, hedging, and restated context. Replace that reader with yourself, and cutting stops being a matter of taste:

- **The derivability test, per sentence.** Could the reader derive this from the artifacts in under a minute? Derivable → cut. What survives is the non-derivable core: the goal, decisions made (so they are not relitigated), constraints invisible from the artifacts, and the traps that would cost an hour.
- **Selection, not compression.** Full precise sentences, fewer of them. Fragments, arrow-chains, and abbreviations are lossy; the reader pays the decompression cost, possibly wrongly.
- **Every instruction is a delta from default behavior.** Before keeping a line: what wrong thing happens without it? No answer, no line.
- **Precision buys concision.** One exact term replaces a paragraph of approximation; most of the work is naming things correctly — speak the substrate's names.
- **An example earns its lines only where the rule under-determines the output.** One example at the trickiest juncture, not one per rule; an example the reader would produce from the rule is the derivability test failing in miniature.
- **Draft, then delete.** Models don't write tight in one pass; they edit tight well. When the piece matters, set a budget first ("one screen") — a cap forces selection where guidance merely suggests it.
- **Specifics rot.** Bias version-agnostic, outcome-based instructions — point at the enforcement mechanism, not a copied value that will drift. When a specific is load-bearing, say why.
- **Update documents, don't add to them.** Edit the line that is now wrong rather than appending a correction beside it; growing length should reflect a larger system, not accumulated amendments.
- **Omit, don't litigate.** Say what a thing *is*; frame the rule so edge cases fall out. Litigate only discipline junctures — a delegation seam or an irreversible act earns explicit loophole closure, because skipped-step defects cluster exactly there.
- **Completeness is the other edge.** A missing trap or unstated decision is a worse failure than a kept derivable sentence. The test cuts the derivable; it never licenses cutting the merely obvious-feeling.

## 3. Red flags

- A date, incident reference, or "previously/now" in a forward-facing instruction — git holds the journey; the reader needs the rule, not how it was learned.
- Sentences got shorter instead of fewer.
- A sentence restating what code, a spec, or a cited doc already says — route instead.
- A summary attached to material the reader can open directly.
- Two homes for one fact with no declared echo (`tool-design.md` §Duplication).
- A trap or decision cut because it felt obvious — obvious-to-you is not derivable-from-artifacts.

## 4. Form

One line per paragraph, no hard wrap (`tools/reflow_md.py --check` is the meter — advisory at pre-commit, doesn't block). Skills follow `vrc-skills/CONVENTIONS.md` and are gated by its `validate_skills.py`, whether they ship in that repo or as project skills under `.claude/skills/` — one anatomy, both enumerations; pattern entries follow `vrc-patterns/CONVENTIONS.md`.
