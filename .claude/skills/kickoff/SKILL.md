---
name: kickoff
description: Use when authoring a kickoff block that hands a problem to a fresh session to brainstorm — writing the brief, not doing the work ("write a kickoff", "mint a block", "spec this for a later session"). One block; launching a wave of them is `dispatch`.
---

# Kickoff

A kickoff block drops a context-less agent onto a problem with the facts firm and the solution open. The receiver is a model at your own capability level with the repo open — ground the problem precisely, name the prerequisites, offer hypotheses to stress-test, then get out of its way. If you've written the answer, you've written the wrong document.

Blocks live in `docs/local/kickoffs.md` — untracked, and main-working-tree only: `docs/local/` is gitignored, so it does not exist in a worktree. Shape: `## <ID> — <title>`, blank line, then `**Gate:** …` as the first body line, last line the terminal state (normally an open PR with the repo's gates green). `grep -A2 '^## '` is the board (`-A1` shows only the blank line). Gate vocabulary: launchable / blocked-on-X / operator-held, plus **on-request** — no technical blocker, but the work leans on the operator's own sustained attention (a design call only he can make, in-game time, wearing a live avatar), so a dispatch wave never auto-includes it; it launches only when he names it. However a block launches — dispatch wave or pasted solo — the launcher points the receiving session at `docs/dispatched-work.md`, the worker's standing brief; the block itself doesn't restate it.

## Sections

Include each that applies, in the shortest form that works:

- **Problem** — what's wrong and why it matters, grounded in `path:line` anchors and concrete facts; the receiver starts from zero and cannot see what you've seen. A problem observed in a recorded session also carries a **backing anchor**: a distinctive verbatim phrase to grep the session store for (an error string, a symbol, the observer's words), plus the session id if known. None recorded? Say so.
- **Read before planning** — the docs the worker may not plan without, closing with the receipt clause: *your plan quotes one load-bearing line from each*. Any block touching an avatar, pattern entry, or controller names `docs/nondestructive.md` and its domain doc here itself — the workspace-level read-first rule loses to a dense block under task pressure, so the block carries its own prerequisites.
- **Useful facts** — the non-derivable context that saves a rediscovery: half-made decisions, ruled-out paths and why, the worked precedent already in a repo.
- **Where to look** — reference surface beyond the prerequisites: files, non-code config, and the docs to keep honest.
- **Constraints** — the hard rails, stated firmly; they are the boundary, not a suggestion.
- **Direction, not prescription** — one or two paths explicitly framed as starting hypotheses; name the core tension and let the agent own approach, scope, and sequencing.

## Rules

**Point, never paraphrase.** Name a file, a section, and the question to answer there; do not restate what the section says. A described section reads as already-consumed — the worker cites it in plans and commit messages without opening it, and the invariant it held breaks unnoticed. The description is also an unmanaged echo of the doc (`docs/tool-design.md` §Duplication): it drifts, and the kickoff's version wins because it's the one in hand.

**Distinguish directive from hypothesis explicitly.** Operator rulings and measured facts are firm — say so, so the worker doesn't re-litigate them. Everything else is the worker's to stress-test, and a block that states a guess in a directive voice manufactures false confidence downstream.

Open by directing the agent to **brainstorm** — that's the job being handed off. Don't head the text with a `Kickoff:` label; a receiver reads that as a cue to author another kickoff instead of thinking. Keep the whole block short — a kickoff, not a design doc.
