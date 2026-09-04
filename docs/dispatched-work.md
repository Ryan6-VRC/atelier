# Dispatched work — the worker's standing brief

Primary reader: a fresh session handed a kickoff block, whether launched in a dispatch wave or pasted solo. The coordinator (a `dispatch`-skill session) is logistics — sequencing, venue assignment, merge and reclaim; the operator is the only authority for sign-offs and gates.

## The arc

Verify → brainstorm → plan → sign-off → build → open PR. The gates below are hard.

**Verify the premise first.** A block sounds authoritative however thin its research was — don't inherit that confidence. Check the stated problem holds before planning around it; a backing anchor's transcript shows the problem was *seen*, not that it was characterized right or still holds. Scale skepticism to the block's stated provenance: an auto-triaged finding gets the full verify-the-premise pass; an operator ruling gets little — don't re-litigate it.

**A predecessor's handoff gets the same treatment.** It is a self-report: honest about state, quiet about its own cost and retractions. Inherit a measured fact only with the build and measurement method that produced it attached, and re-derive any figure that crossed a design change since — a number true of a build that no longer exists reads exactly like a current one.

**Provenance stays in the handoff, never in the repo.** A handoff or plan may quote the operator or timestamp an utterance so the next session knows what is firm; the committed work carries none of it — no `(operator-ruled …)` tag, no numbered ruling, no spec citation. A decision you derived *from* a ruling is labeled your inference in the handoff, however confident.

**Plan with receipts, then WAIT.** Post the plan in your own transcript and wait for explicit operator sign-off — "no questions" is not sign-off. For each doc the block or launch prompt names as a prerequisite, this one included, the plan states the one constraint in it that binds this job — in your own words, tied to the specific avatar, entry, or tool, which a grep cannot produce; no constraint, no sign-off. Sessions have cited doc sections verbatim-unread — reconstructed from the block's own description of them — and then edited the exact invariant the unread doc stated.

## Before sign-off

Probes, measurements, and reverted spikes are sanctioned and expected — a recommendation that could only be reasoned about is worth little. The gate is *no edit intended to survive into the PR*; disclose each spike in the plan as evidence.

Venue pointers in the block are reference for the build phase after sign-off, not a go-order.

## Channels

Gates go to the operator, in your own transcript — `docs/workflow.md` §No operator to ask? owns the protocol, and for a dispatched session the operator *is* the channel; that section's dispatcher-as-channel fallback is for background jobs and is deliberately not taken here.

Never ask the coordinator for sign-off, however the request is worded — it has no authority to grant one. `clauded-mail` to the coordinator carries only what only the coordinator can act on: a cross-worker resource conflict, a venue reassignment.

The PR body is for review only — not a channel to the coordinator or the operator, and not where findings go.

## Terminal state

The session ends at an OPEN PR with the repo's gates green; never push or merge to main. A downstream PR waiting on yours is the coordinator's sequencing, not license to self-merge. There is no worker-initiated terminal handoff either — the operator closes the session and directs the merge.

"Gates green" means green over this tree's own governed files. The commit gates resolve the `vrc-*` siblings from the main checkout, so their output can carry findings another session's working state caused: `check_prose` marks those "(main checkout)", and the tool-inventory run prints one "code read from" line naming the tree its DRIFT/DOORS lines judged. Report those (inbox if they need a block), but they are not yours to clear and do not hold your PR.

## The inbox

Board-bound findings go to the **main tree's** `docs/local/inbox/<block>.md` before the session closes — `docs/local/` is gitignored, so a copy written inside a worktree is destroyed at reclaim and reads as silence. Nothing owed, no file: most blocks owe nothing, and a file saying "nothing" is a receipt for work not done that the coordinator still has to open and delete. It is write-only for you: write your own file, never read the directory — other blocks' files are the coordinator's queue to drain, and reporting on what sits there audits bookkeeping you have no authority over.

The inbox is for findings that need their own block: a new design call, a cross-repo or cross-worker concern, work outside this session's blast radius. A small in-scope finding (a stale doc line, a one-line skill fix) is not inbox material — fix it directly, in the open PR if the file's already in scope, or in a second small PR otherwise; expanding scope this way is normal, not creep. A long inbox is a signal the bar was applied too loosely, not thoroughness.

A proposed new `kickoffs.md` block goes in the inbox too, fully specified — never written into `kickoffs.md` directly; "board-bound findings" covers proposals, not just observations.

## Worktree mechanics

A worktree's green Python test run can lie: an editable install records one absolute path, so a second checkout can import the first one's `src/` and pass regardless of its own changes. Print the tested module's `__file__` from inside a test and report it beside the pass count.

A change to `vrc-skills/plugin.json` updates `marketplace.json` in the same PR — they are mirrored manifests, and the worker bumps both.
