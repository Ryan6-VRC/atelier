---
name: write-pattern-readme
description: Use when writing or rewriting a `vrc-patterns` entry README — the first write-up after an entry is built, or a rewrite of one that has accreted ("rewrite the contact-radar readme", "this readme is unreadable", "write this entry up", "bring this README to the VRLabs shape", "humans complain about the readmes"). Not building or changing the entry itself (author-gimmick); `write-for-agents` co-runs for the sentence craft and is not a substitute; a doc under `docs/` is edited directly.
---

# Write a pattern README

Produce an entry README a stranger can install from and an agent can change from, with every claim traced to the source that owns it. The *shape* lives in `vrc-patterns/CONVENTIONS.md` §The README, with `vrc-patterns/contact-radar/README.md` as its worked example; the sentence craft is the `write-for-agents` skill; where a fact belongs is `docs/tool-design.md` §Where knowledge lives and §Duplication. This skill owns the process: the inventory that decides which audits run, what to settle before drafting, the review loop, and the closing checks. Read those three before step 1.

**No operator to ask?** The framing gate in step 1 is surfaced with `needs input:` and waited on whenever a channel exists (`docs/workflow.md` §No operator to ask?); only with no channel at all do you frame from the consumers you found and lead the PR body with that undecided call. The terminal state is an open PR (`docs/dispatched-work.md` §Terminal state).

Paths below are relative to the metarepo root; `<patterns>` is the `vrc-patterns` checkout beside it and `<entry>` the entry folder within it.

## 1. Frame and inventory

- **Inventory the entry.** Which of these exist: a generator (`generate.py`, at the entry root or in a variant subfolder) and what commands it documents; a hand-authored `controller.yaml`; `built/`; one or more prefabs; `assets/`; a previous README. CONVENTIONS §Tier is derived, not assigned reads the tier off the same files. The inventory selects the audits in step 2 and the checks in step 6.
- **What is the entry for, as its consumers use it?** The shipped demo payload is not the answer. Search the workspace for the entry's name (venues, `docs/local/`, other entries; sibling repos and `docs/local/` resolve through the main checkout, `tools/atelier_paths.py`), read how each consumer wires it, and lead with what they build on. **Gate: the framing sentence is the operator's to confirm before you draft.**
- **Which headings does code hard-code?** Search the entry's generators and comments for `README §`; each named section survives, or the pointer moves in the same change.
- **Which facts already have a home?** The runtime, animator-schema and gimmicks docs house the measurements a whole class of work needs and often cite the entry as the venue. The README routes to them; what it keeps is the entry's own measurements, its design reasons, and the install discriminators.

## 2. Establish from the sources

Each claim class has an authority: package or generator source for mechanism; the serialized asset for authored state; a bounded measurement (venue named) for runtime behaviour; the workspace docs for what they house; consumer call sites and the entry's history for intent and design reasons; the operator for unsettled intent. When two purported homes disagree, the audit reports both sides rather than picking one.

Delegate the reading to read-only subagents, briefs in [audits.md](audits.md), each launched with the placeholders filled and run in parallel; nothing touches Unity. Select by inventory:

- **Code audit** (A) when a generator or a `controller.yaml` exists.
- **Prefab and assets audit** (B) when a prefab exists. It runs every per-entry check the generator documents.
- **Old-prose audit** (C) when a previous README exists.
- **History audit** (D) when a previous README exists, or when the artifacts do not carry the design reasons.

Read the reports for contradictions first; those are what the draft must not carry over.

## 3. Settle before drafting

- Every contradiction the audits reported, by the authority for that claim class; a contradiction no authority settles is an operator question, not a coin toss.
- The catalog row in `<patterns>/README.md`: the declared echo of the lead (`docs/tool-design.md` §Duplication), so it moves with the lead in the same change.
- A glossary from the audits: one term per concept, defined at first use; where a common noun collides with a node name in a way that makes a sentence ambiguous, rename the noun.
- A length budget per section, set before writing; CONVENTIONS §The README owns the rule that length follows mechanism count.

## 4. Draft

Write the whole file, top to bottom, in the CONVENTIONS shape; `write-for-agents` §Red flags and CONVENTIONS §The README own the sentence rules (values, history, restatement). Process decisions the reviews keep finding missing:

- **The stats block carries every rank-gated count** the entry adds, per `docs/optimization.md`'s table: as an expression in the entry's scaling knob where one exists, else the literal shipped count, with the gate the shipped configuration crosses stated in the notes.
- **The mechanism section routes the walk** to the generator docstring or `controller.yaml` and keeps only invariants and reasons. A paragraph that could be diffed against the docstring is cut to its invariant line.
- **Install discriminators, not a test log.** State how a broken install looks different from a correct one, name what no check catches, and keep only the recipes for behaviours nothing else can exercise.

## 5. Review loop

Two read-only subagents on the draft, in parallel, briefs in [audits.md](audits.md): a **fact-check** (E: claim by claim against the authorities above, every cross-reference resolved both ways, plus a lost-facts diff against the previous README when one exists) and a **readability review** (F: a cold VRChat creator on the top half; an agent composing, changing a knob, and diagnosing a broken install). Apply both, then a short second F pass on the top half if its shape changed. Never edit the file while a reviewer is reading it.

## 6. Verify and land

- From the metarepo root: `python tools/reflow_md.py --check <patterns>/<entry>/README.md <patterns>/README.md` (add `<patterns>/CONVENTIONS.md` if touched), then `python tools/check_prose.py`.
- List every `§` reference in the README and confirm each names a heading in its target; repeat the `README §` search from step 1 against the new headings.
- Generator present: run it as it documents and read `git diff` in `<patterns>`; a diff that is line endings only is restored with `git checkout -- <paths>`, any other diff means the README was written against a document the generator no longer emits. Compiled entry: `<patterns>/tools/gate.ps1` if anything under `built/` or `controller.yaml` moved. Prefab-only entry: run the per-entry checks it documents, and nothing regenerates.
- Commit on a branch, push, open the PR (what changed, the errors the old README carried, checks run), and stop at the open PR unless the operator has asked for the merge.

## Traps

- **Unity YAML names components by script GUID.** A search for a class name across a prefab finds nothing; count receivers, constraints and particle systems from the check output or a scripted YAML walk.
- **The generator's own comments can be stale** (a count, a section pointer); the emitted document and the prefab outrank them, and the fix rides in the same PR.
- **A subagent that read the old file reviews the old file.** Reports arrive minutes after launch; check which version each one read before applying its findings.
- **Variant builds regenerate together**, and a variant's own check may cover less than the base's; the README's change section says what each covers.
