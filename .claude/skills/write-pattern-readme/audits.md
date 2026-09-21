# Subagent briefs for a pattern README

Six read-only briefs, each launched as its own subagent. Fill the placeholders before launching: `<atelier>` the metarepo main checkout, `<patterns>` the `vrc-patterns` checkout, `<entry>` the entry path within it, `<tier>` from the inventory, `<old-readme>` the committed README (`git -C <patterns> show HEAD:<entry>/README.md`) and `<draft>` the working-tree one. Every brief opens with this preamble, verbatim:

> Do not edit anything. Do not touch Unity or the MCP tools; every read is on disk. Read `<patterns>/CONVENTIONS.md` §The README first. Report with file:line anchors and classify each claim; do not summarize the entry.

Where a brief names an artifact the inventory says the entry lacks, the subagent states the absence once and moves on.

## Contents

- A. Code audit
- B. Prefab and assets audit
- C. Old-prose audit
- D. History audit
- E. Fact-check of the draft
- F. Readability review of the draft, two seats

## A. Code audit

Read every generator under `<entry>` in full (docstring, configuration, refusals, builders, documented checks), then every `controller.yaml` structurally (layers, parameters, states, transition conditions, what each shared parameter's writers are), `<atelier>/docs/animator-schema.md` as far as the YAML needs, then `<atelier>/docs/runtime.md` and `docs/gimmicks.md` for what the workspace already houses. Read `<old-readme>` last, if one exists.

Deliver: a mechanism brief in the entry's own terms, tagging each fact as derivable from the document, explained only by a generator comment, or asserted nowhere in code; every configuration key with the refusal that guards it and its direction; every documented check and the surface it guards; where an old README exists, its claim-by-claim audit (supported, unsupported-but-plausible, contradicted with both sides quoted, stale, restatement); every numeric value in prose that lives in configuration; and the shortlist of facts a reader cannot get anywhere but this entry.

## B. Prefab and assets audit

Read `<atelier>/docs/nondestructive.md`, and `docs/runtime.md`'s sections for the component types the prefab carries. Walk each committed prefab's YAML: the full hierarchy with each node's components; for each component type present, the fields a consumer or a check depends on (receiver tags, filters, locality, mode and parameter; constraint sources, weights, offsets and lock state; the VRCFury or MA seam components with their asset references, `globalParams` and toggle flags; particle systems, renderers and sub-emitter links); which nodes are inactive at rest; a variant prefab's removals, added components and modifications; `assets/` importer settings against CONVENTIONS' importer gate; `built/` `.meta` GUIDs and stamps. Run every check the generator documents, exactly as documented, and `git -C <patterns> status --short -- <entry>`; report both verbatim.

Deliver: the true hierarchy in the README's tree form; where an old README exists, the audit of every prefab, asset and install claim in it (confirmed with the YAML path, contradicted with both sides, unverifiable on disk); the check and status output; and what a fresh installer trips over that no README says.

## C. Old-prose audit

Read `<atelier>/CLAUDE.md` §Writing for agents, `docs/tool-design.md`, `<atelier>/.claude/skills/write-for-agents/SKILL.md`, CONVENTIONS §The README, the docs `<old-readme>` cites, two or three sibling READMEs for calibration, the first screen of any generator docstring, and the README's git history (`git -C <patterns> log -p --follow -- <entry>/README.md`), then `<old-readme>` in full.

Attack, quoting the offending sentence, naming the rule and giving the replacement: echoes of a workspace doc (with the one-line pointer that replaces each); restatements of the document or the prefab; configuration values in prose; verification-run residue and bare "(measured)" markers; accretion scars (history told as present tense, tombstones for removed designs); register and density (load-bearing paragraphs versus the author thinking aloud); what a fresh installer or editor needs that is missing; and a proposed skeleton with a word target per section. Say whether a full rewrite or a heavy edit is warranted, and why.

## D. History audit

Read every commit touching the entry with its body (`git -C <patterns> log --format='%h %ad %s%n%b' --date=short -- <entry>`); for each squash-merge subject carrying `(#N)`, the PR body (`gh pr view N --repo <owner/repo>` with the repo read from `git -C <patterns> remote -v`); the README's own `log -p`; and the configuration block's evolution across commits. Search `<atelier>/docs`, `TOOLS.md`, both skill trees, the other entries and `<atelier>/docs/local/` (main checkout only) for references to the entry.

Deliver: a dated mechanism timeline (what each change did to the rig, not the prose); the ghost sentences in `<old-readme>` with the commit that superseded each; the configuration evolution table; every external reference with its exact line and whether it names a heading that must survive; and every design reason recorded in a commit or PR body that neither the README nor the code carries.

## E. Fact-check of the draft

Authorities by claim class: generator and package source for mechanism; the serialized prefab and assets for authored state; a bounded measurement with its venue for runtime behaviour; the workspace docs for what they house; consumer call sites and history for intent. Go through `<draft>` sentence by sentence; mark each claim confirmed with an anchor, contradicted with the authority quoted, or unverifiable (and whether the draft bounds it as a measurement with its venue). Check every cross-reference both ways: the draft's `§` references against their targets, and every `README §` pointer in code against the draft's headings. Where the entry has them, check each knob row's refusal and direction, the component and layer counts, the change-procedure section's commands, each install discriminator's stated cause, every node and relation in the rig tree, and the consumer contract.

Where `<old-readme>` exists, diff it against `<draft>` for lost facts under a strict filter: a claim absent from the draft, absent from the code and the cited docs, and costing an hour to rediscover. Report contradictions first, then the lost-facts list, then a short confirmed summary.

## F. Readability review of the draft, two seats

Seat one, a competent VRChat avatar creator who has never seen the library, reading on GitHub: read the top half only (through the stats block). Name the first sentence that assumes something never told, every term of art without a defining clause at first use, every common noun that collides with a node name ambiguously, every sentence over about thirty-five words, whether the prefab choice is clear in the first screen, whether the install guide alone suffices, and whether the knob table (if any) is usable without the mechanism section.

Seat two, an agent with the repo open doing three tasks (composing the entry, changing its main knob or optional rig where it has one, diagnosing a broken install): for each, what is missing, what is in the wrong section, and what duplicates the generator docstring or a workspace doc. Apply the derivability test per sentence in the mechanism and traps sections; flag history residue, bare measurements, configuration values, and any sentence carrying more than two ideas. Check the stats block against `<atelier>/docs/optimization.md`'s rank table. Judge length section by section with the sentences to cut first.

For a second pass after the shape changes, restrict the brief to the top half and to new defects only.
