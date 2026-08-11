---
name: dispatch
description: Use when launching a body of kickoff blocks onto worker sessions and coordinating them to reviewable PRs ("dispatch these", "run the wave") — the downstream half of `kickoff`. A single block is pasted into a fresh session directly — no skill, but the paster still points it at `docs/dispatched-work.md`.
disable-model-invocation: true
---

# Dispatch

You are the coordinator: author each launch prompt, sequence workers around the physical singletons, track the wave, reclaim state as workers finish. The campaign tracker is `docs/local/dispatch-plan.md`: this skill holds the process, the tracker holds the workspace state (standing constraints, venue roster, tried-and-rejected, handoffs) — adopt and update it, never re-author it per session. You run in the **main working tree** — `docs/local/` is gitignored and exists only there, which is why you, and not a worktree worker, can edit the tracker.

## The launch prompt

2–4 sentences wrapped around two pointers: the block (by file + ID — workers run at the workspace root, so don't paste it; paste only a block the worker genuinely cannot reach) and `docs/dispatched-work.md`, named as a read-before-planning prerequisite so the receipt gate covers it. Worker policy lives in that doc — the prompt adds only what is per-launch: the singleton/venue assignment, tier, and any provenance the block doesn't state.

Four checks, each a real failure compressed — run every assembled prompt, and every mid-wave resume message, against all four:

1. **The policy travels by pointer.** The prompt names `docs/dispatched-work.md` under the receipt clause and paraphrases none of it — a paraphrase is an unmanaged echo, and the in-hand version wins over the doc.
2. **Receipts checked at sign-off.** The plan quotes one load-bearing line from each named doc, `dispatched-work.md` included; no quotes, no sign-off.
3. **The edit gate is phrased as intent.** "No edit intended to survive into the PR", never "no edits" — the flat form outlaws the probes and spikes the worker doc sanctions.
4. **No merge-permission phrasing.** Scan the full prompt, block included, for "land it", "ship when ready", and kin — a casual resume message mid-wave re-triggers the self-merge failure the doc's terminal-state rule exists against.

## Coordinating

- Parallelism is bounded by the physical singletons (live Editors, the one machine, a serial test runner), not the dependency graph. Same repo + disjoint files runs concurrently for free; overlapping files is a merge you own.
- An **on-request**-gated block (kickoff skill vocabulary) never fills a wave slot on its own — it's launchable, but only when the operator names it by ID.
- Assigning singletons is your job, not the worker's — hosts of the same kind carry different state and capabilities. Name the assignment in the launch prompt; keep the roster's distinguishing traits in the tracker, and cite them rather than restating them.
- After presenting launch prompts, present the **singleton board**: each singleton and venue, who holds it, what's free, what launches now versus waits. The operator sequences from that board, not from prose above it.
- Tier is your call per block — cheaper tier for mechanical work, top tier for heavy design — recorded in the tracker, never a silent uniform default.
- Your own gates go to the operator per `docs/workflow.md` §No operator to ask? — a dispatch session is interactive, so the operator is always the channel; sequencing and tier are yours, launch/merge/drop decisions on contested blocks are not.
- Don't ground a block in coordinator context: one or two greps to see the premise is plausible, then the research belongs to the worker. One exception: a cheap check that might kill or invert the block earns its tokens.
- Don't mine PR bodies for bookkeeping — read the inbox file; review is a separate job you are not always doing.
- A worktree's green Python test run can lie (editable-install path aliasing — `docs/dispatched-work.md` §Worktree mechanics has the worker report the tested module's `__file__`): before trusting a pass count, check the reported path is the worktree's.

## Draining a repair queue

The queue line is not the unit of triage — the coherent repair is. Dedupe across the venue files first, then group lines sharing an underlying cause: several warnings aimed at one doc section are usually one section rewrite, often at a net line reduction. Cost the group, never the line.

Sort each repair by failure mode, which sets its default:

- **A false assertion — repair by default.** A green verdict on a bad state, a round-trip that silently drops content, a doc sentence a measurement contradicts. This class outranks blockers: a block fails loud and costs bounded tokens, while a false verdict ships a defect under a green check — and a lie in a `Check*` door corrupts every future grade that leans on it, `fitting-session`'s included.
- **A loud block or expensive detour — costed, on evidence already in the queue.** The worker routed around it, so what matters is expected recurring cost: the transcript anchor prices the detour in measured tokens, and independent hit count prices recurrence — two independent sightings promote an item, one sighting on an exotic asset is presumptively a drop.
- **A complaint that still succeeded — drop by default.** A drop needs no justification; a fix must positively claim its factor — a net line reduction, a prose check lifted into code, a measured detour it retires.

Then price where the fix lands (`docs/tool-design.md`'s routing ladder owns the full argument): tool output is near-free, paid at invocation exactly when relevant; a narrow-readership doc is cheap, its only readers the agents it serves; an always-read doc taxes every future session; new gate or code carries maintenance plus standing friction on future work, and clears the highest bar.

Spend real analysis only on the contested middle — most items answer at a glance, and an analysis habit is its own token sink that drifts toward rationalized approvals.

The asymmetry that makes drop-by-default safe: a wrongly dropped defect re-surfaces in a later run and promotes itself on hit count, while a wrongly queued fix burns a wave slot, a worker session, and coordinator context with no equivalent recovery. Softness still applies — a queued repair is a hypothesis the worker's skeptical start may yet decline.

## Merge and reclaim

Reclaim as a step in the loop — on merge, on early-stop, on abandonment — not a batch at the end; early worker termination is normal, not an error. On merge: squash + `--delete-branch`, ff local main, remove the worktree, cross the block off with a one-sentence note (git holds the detail), transcribe the inbox file, hand-register any tool-index change a worktree-skipping hook missed, and confirm sibling manifests moved in lockstep (`plugin.json` ↔ `marketplace.json` — the worker doc has workers bump both; a PR that bumped only one is the miss to catch).

- Under worktree-by-default the local branch survives `--delete-branch` — gh deletes local refs only when the branch sits in the clone it merges from, and a worktree-held branch it cannot touch. Delete it by hand only after a diff proves main holds the branch's work: `git diff main <branch> --name-only -- $(git diff main...<branch> --name-only)` comes back empty. Operand order matters — branch-only files surface only when diffing *from* main; the pathspec restricts the check to files the branch touched so main's forward drift can't flood it; and no `--diff-filter=A`, which is blind to a branch whose whole contribution is edits. Diff, don't grep; spot-checking headings is how unmerged work gets mislabeled superseded.
- A worktree that won't remove is a tell — inspect, don't force: a session can end with an uncommitted follow-on pass invisible on main, and a stale local branch may predate the PR revisions that merged, so recover it as a semantic merge onto current main.
- `git -C <repo> worktree remove <relpath>` resolves the relative path against *your* cwd, not the `-C` repo — pass absolute paths. A remove failing on Windows path length is mechanical, not a reclaim hazard: verify clean (`status --short`, `log @{u}..HEAD`), then `Remove-Item -LiteralPath '\\?\C:\…' -Recurse -Force` and `git worktree prune`.
- Stacked PR (base = another PR's branch): merge the base WITHOUT `--delete-branch`, then rebase the child onto main (`git rebase --onto origin/main <base-tip> <child>` — already-upstream commits drop out), confirm the diff is only the child's own files, force-push, retarget, merge. A retargeted child does not auto-close and silently re-proposes the base's whole diff, because its merge-base predates the squash.

## Boundaries

`kickoff` authors one block; `docs/dispatched-work.md` is the worker's standing brief; dispatch launches and coordinates many. The worker owns its own brainstorm → plan → execute → open-PR; dispatch owns only the cross-worker layer.
