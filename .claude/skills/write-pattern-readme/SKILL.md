---
name: write-pattern-readme
description: Use when writing or rewriting a `vrc-patterns` entry README — the first write-up after an entry is built, or a rewrite of one that has accreted ("rewrite the contact-radar readme", "this readme is unreadable", "write this entry up", "bring this README to the VRLabs shape", "humans complain about the readmes"). Owns the audits, the draft in the library's two-reader shape, the review loop and the PR. Not building the entry (author-gimmick), not generic agent prose (write-for-agents), not a doc under `docs/` (edit it directly).
---

# Write a pattern README

Produce an entry README a stranger can install from and an agent can change from, with every claim backed by the entry's own artifacts. The *shape* lives in `vrc-patterns/CONVENTIONS.md` §The README, with `vrc-patterns/contact-radar/README.md` as its worked example; the sentence craft is the `write-for-agents` skill; where a fact belongs is `docs/tool-design.md` §Where knowledge lives and §Duplication. This skill owns the process: what to establish before drafting, the audits that establish it, the review loop, and the closing checks. Read those three before step 1.

**No operator to ask?** Frame from the consumers you can find (step 1) and state the framing you chose in the PR body; surface anything the artifacts cannot settle with `needs input:` per `docs/workflow.md` §No operator to ask?. The terminal state is an open PR (`docs/dispatched-work.md` §Terminal state).

## 1. Frame

- **New or rewrite?** A fresh entry has no history to excavate and no old prose to attack; a rewrite has both, and the old README is the last thing you read, never the first. The depth of step 2 follows from this.
- **What is the entry for, as its consumers use it?** The shipped demo payload is not the answer. Find the real consumers (`grep -rl` the entry name across the workspace venues and `docs/local/`; ask the operator) and lead with what they build on. **Gate: the framing sentence is the operator's to confirm before you draft**; a README that leads with the demo reads wrong to everyone who has used the entry.
- **Which headings does code hard-code?** `grep -n "README §" <entry>/generate.py <entry>/*/generate.py`. Those section names survive, or the generator's pointer moves in the same change.
- **Which facts already have a home?** The runtime, animator-schema and gimmicks docs house the measurements a whole class of work needs, and often cite this entry as the venue. The README routes to them and never restates; what it keeps is the entry's own measurements (the ones `gimmicks.md` routes here), the design reasons, and the install discriminators.

## 2. Establish from the artifacts

Every fact in the README is asserted from code, prefab YAML, or a bounded measurement. Delegate the reading to read-only subagents, briefs in [audits.md](audits.md), on the model tier the task earns; run them in parallel and make no Unity call (everything is on disk).

- **Rewrite:** all four exploration audits (mechanism from code, prefab and install surface, adversarial prose review of the old README, design history from git and PR bodies).
- **New entry:** the mechanism and prefab audits only.

Each audit classifies claims (supported, contradicted with both sides quoted, stale, restatement, value leak, unverifiable-on-disk) with file:line anchors, and runs `--check` where the entry has one. Read the reports for contradictions first; those are what the draft must not carry over.

## 3. Settle before drafting

- Every contradiction between two homes (README versus generator comment versus lint), by derivation from the substrate model in `docs/runtime.md`, not by majority. The sign of a hysteresis distance is the classic case.
- The catalog row in `vrc-patterns/README.md`: it is the declared echo of the lead (`docs/tool-design.md` §Duplication), so it moves with the lead in the same change.
- Names for the regions and states the README will mention more than once; one term per concept, defined at first use, and never a word that is also a node name (`Boundary` the node against "the boundary" the zone).
- A word budget per section, set before writing. The top half (description through the stats block) is under a screen; the depth sections earn their length by mechanism count, not by history.

## 4. Draft

Write the whole file, top to bottom, in the CONVENTIONS shape. Rules the reviews keep finding broken:

- **Relations, never values.** A CONFIG constant appears as its name and its direction; a measurement that is itself the fact appears with its venue (`in av3emu` / `in-client`), and a bare "(measured)" appears nowhere.
- **K, and every term of art, is defined at first use.** The cold reader meets "slot", "collision step", "the front" before any section that assumes them.
- **The stats block carries every rank-gated count** the entry adds (`docs/optimization.md`'s table: contacts, particle systems, material slots, and whichever the entry pressures), as expressions in the entry's knob, with the shipped value in parentheses, and the notes say which gate the shipped configuration crosses.
- **The mechanism section routes the walk** to the generator docstring or `controller.yaml` and states only invariants and reasons. If a paragraph could be diffed against the docstring, cut it to the invariant line.
- **Install discriminators, not a test log.** `Verifying the install` says how a broken install looks different from a correct one and names what no check catches; the two or three behaviours only a recipe can exercise get that recipe, and nothing else from the author's session survives.
- **No history.** No "now", "old", "used to", "the fix", PR numbers, or a retained node explained by what replaced it.

## 5. Review loop

Two read-only subagents on the draft, in parallel, briefs in [audits.md](audits.md): a **fact-check** (claim by claim against code and prefab, every cross-reference resolved, plus a lost-facts diff against the previous README under a strict filter) and a **readability review** from two seats (a cold VRChat creator on the top half; an agent composing, changing a knob, and diagnosing a broken install). Apply both; then a short second readability pass on the top half if its shape changed. Never edit the file while a reviewer is reading it; sequence the passes.

## 6. Verify and land

- `python tools/reflow_md.py --check` on the README, the catalog and CONVENTIONS if touched; every `--check` door the entry ships; `python tools/check_prose.py` from the metarepo.
- `grep -o "§[A-Z][a-z ]*" <entry>/README.md` and confirm each target heading exists; re-run the generator grep from step 1.
- Regenerate the entry and confirm the diff is empty or line endings only (restore those with `git checkout`); a real diff means the README was written against a document the generator no longer emits.
- Commit on a branch, push, open the PR with a body under the repo's size budget (what changed, the errors the old README carried, checks run), and stop at the open PR unless the operator has asked for the merge.

## Traps

- **Unity YAML names components by script GUID.** A grep for a class name across a prefab finds nothing; count receivers, constraints and particle systems from the `--check` output or a scripted YAML walk.
- **The generator's own comments can be stale** (a receiver count, a section pointer); the prefab and the emitted document outrank them, and the fix rides in the same PR.
- **A subagent that read the old file reviews the old file.** Reports arrive minutes after launch; check which version each one read before applying its findings.
- **The PR-body hook** refuses a body over its budget; write what a reviewer needs and nothing else.
- **Both generators of a variant entry regenerate together**, and the variant's own `--check` may not cover geometry; say so in `Changing it` rather than trusting the reader to notice.
