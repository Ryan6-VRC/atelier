# Subagent briefs for a pattern README

Six read-only briefs, each launched as its own subagent with the entry path substituted. Every brief opens with the same three lines: do not edit anything; do not touch Unity or the MCP tools; read `vrc-patterns/CONVENTIONS.md` §The README first. Reports carry file:line anchors throughout and classify rather than summarize.

## Contents

- A. Mechanism from code
- B. Prefab and install surface
- C. Adversarial prose review of the old README
- D. Design history from git and PR bodies
- E. Fact-check of the draft
- F. Readability review of the draft, two seats

## A. Mechanism from code

Read in this order: the generator in full (docstring, CONFIG, every lint, the per-state builders, `--check`), any variant generator, both `controller.yaml` files structurally (layers, parameters, states, transition conditions, which AAPs are written where), `docs/animator-schema.md` as far as the YAML needs, then `docs/runtime.md` and `docs/gimmicks.md` for what the workspace already houses, and the old README last. Re-emit the document to a temp file and diff it against the committed one, so the report says whether the code is the authority.

Deliver: a mechanism brief (state machine, shared layers, the readout formula in CONFIG names, the boot, pause and disabled paths, how each variant differs), tagging each fact as derivable from the document, explained only by the generator's comments, or asserted nowhere in code; every CONFIG key with the lint that guards it and the lint's direction; every `--check` assertion and the prefab surface it guards; a claim-by-claim audit of the old README (supported, unsupported-but-plausible, contradicted with both sides quoted, stale, restatement); every numeric value in prose that lives in CONFIG; and the shortlist of facts a reader cannot get anywhere but this entry.

## B. Prefab and install surface

Read `docs/nondestructive.md` and `docs/runtime.md` §Contacts and §Constraints for field semantics, then walk the committed prefab YAML: the full hierarchy with each node's components; every receiver's tags, filters, locality, mode, shape and parameter; every constraint's sources, weights, offsets and lock state; the VRCFury components on the root (controller and params GUIDs against `built/`, `globalParams`, the toggle's parameter, default, saved and synced flags); particle systems, their renderers and sub-emitter links; which nodes are inactive at rest; any variant prefab's removals, added components and modifications; the assets and their importer settings against CONVENTIONS' importer gate; the `built/` `.meta` GUIDs and stamps. Run every `--check` door and `git status` on the entry and report both verbatim.

Deliver: the true hierarchy in the README's tree form with corrections marked; the audit of every prefab, asset and install claim in the old README (confirmed with the YAML path, contradicted with both sides, or unverifiable on disk); the check and status output; and what a fresh installer trips over that the README does not say.

## C. Adversarial prose review of the old README

Read `CLAUDE.md` §Writing for agents, `docs/tool-design.md`, the `write-for-agents` skill, CONVENTIONS §The README, the docs the README cites, two or three sibling READMEs for calibration, the generator docstring's first screen, and the README's git history, then the README in full.

Attack on these fronts, quoting the offending sentence, naming the rule and giving the replacement: echoes of a workspace doc (with the one-line pointer that replaces each); restatements of the document or the prefab; CONFIG values in prose; verification-run residue and bare "(measured)" markers; accretion scars (history told as present tense, tombstones for removed designs); register and density (which paragraphs are load-bearing, which are the author thinking aloud); what a fresh installer or editor needs that is missing; and a proposed skeleton with a word target per section. Say whether a full rewrite or a heavy edit is warranted, and why.

## D. Design history from git and PR bodies

Read every commit touching the entry with its body, the PR bodies where a number is present (`gh pr view`), the README's own `log -p`, and the CONFIG dict's evolution across commits. Grep the metarepo docs, `TOOLS.md`, the skills, the other entries and `docs/local/` for references to the entry.

Deliver: a dated mechanism timeline (what each change did to the rig, not the prose); the ghost sentences in the current README with the commit that superseded each; the CONFIG evolution table; every external reference with its exact line and whether it names a heading that must survive; and every design reason recorded in a commit or PR body that neither the README nor the generator carries.

## E. Fact-check of the draft

Ground truth is the code: the generator and its checks, the variant generator, both documents, both prefabs, and the workspace docs the draft cites. Go through the draft sentence by sentence; mark each claim confirmed with an anchor, contradicted with the code quoted, or unverifiable (and whether the draft bounds it as a measurement with its venue). Pay particular attention to every section cross-reference in both directions (draft to docs, generator to draft headings), each knob row's lint and direction, receiver and layer counts, everything in `Changing it`, each install discriminator's stated cause, every node and relation in the rig tree, and the consumer contract.

Then diff the previous README against the draft for lost facts under a strict filter: a claim absent from the draft, absent from the generator and the cited docs, and costing an hour to rediscover. Report contradictions first, then the lost-facts list, then a short confirmed summary.

## F. Readability review of the draft, two seats

Seat one, a competent VRChat avatar creator who has never seen the library, reading on GitHub: read the top half only. Name the first sentence that assumes something never told, every term of art without a defining clause at first use, every word that collides with a node name, every sentence over about thirty-five words, whether the prefab choice is clear in the first screen, whether the install guide alone suffices, and whether the knob table is usable without the mechanism section.

Seat two, an agent with the repo open doing three tasks (composing the entry, changing its main knob or turning on its optional rig, diagnosing a broken install): for each, what is missing, what is in the wrong section, and what duplicates the generator docstring or a workspace doc. Apply the derivability test per sentence in the mechanism and traps sections; flag history residue, bare measurements, CONFIG values, and any sentence carrying more than two ideas. Check the stats block against `docs/optimization.md`'s rank table. Judge length section by section with the sentences to cut first.

For a second pass after the shape changes, restrict the brief to the top half and to new defects only.
