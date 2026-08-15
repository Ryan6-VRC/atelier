---
name: venue-ignore-audit
description: Use when a Unity venue's search visibility is in question — auditing what `Grep`/ripgrep cannot see under a venue's `Assets/`, seeding or repairing a venue's `.ignore` ("why did that grep find nothing", "check the venue's ignore files", "did my search actually cover Vendor?"), or as the last step of standing up a new venue. Run it after any edit to a venue's `.gitignore` or `.ignore`. Not prose governance over tracked markdown (`check_prose.py`), and not the venue bring-up itself (`docs/new-project.md` owns that runbook; this skill owns its ignore-file step).
---

# Audit a venue's search visibility

A venue's `.gitignore` decides what `Grep` can see, because ripgrep honors it wherever a `.git` sits in an ancestor directory — which every venue under the workspace root inherits by accident of where it sits. The venue's own `.ignore` is the only file that can re-include what it drops. The mechanics live in `docs/unity.md` §Sharp edges and `docs/new-project.md` step 1; this skill owns the audit and its judgment calls.

The failure is silent and self-concealing: a sweep over a hidden tree returns a confident zero, and nothing inside the search result says a tree was skipped. Measured on both live venues, a venue missing its `.ignore` re-includes hides over 90% of its files from every search. That is why this runs on a schedule of suspicion rather than on a verdict — no check fires it.

**No operator to ask?** `docs/workflow.md` §No operator to ask? owns the protocol. The derivable default is to report the audit and change nothing: an `.ignore` edit silently redefines what every later agent can see, so it is never an unattended call.

## The flow

### 1. Discover the venues

A directory is a venue iff it holds `ProjectSettings/ProjectVersion.txt`, `Assets/`, and `Packages/vpm-manifest.json`. Scan the workspace root's immediate children for that signature and never name a venue in tracked code (`CLAUDE.md` §Layout) — venues are the operator's alone.

List with `ls`, not `Grep`/`Glob`: the workspace root's own `.ignore` deliberately leaves an added venue hidden from ripgrep, so an rg-based discovery finds the sample venue and silently misses every personal one. From a worktree the venues are absent entirely — resolve the root from `git rev-parse --git-common-dir`'s parent, and audit there.

### 2. Measure what is hidden

Two passes per venue, **rooted at the venue directory** — ripgrep applies an ignore file above the named search root only to entries at depth 1 beneath it, so rooting at `Assets/` reports paths a real workspace-level `Grep` cannot reach:

```
rg --files . ; rg --files --no-ignore-dot --no-ignore-vcs .
```

Diff the two. Measure, never infer from reading the two ignore files against each other — a textual pairing looks covered in exactly the cases that are blind (step 3's trap is one, and it is live in both venues today).

Report a `.gitignore` or `.ignore` found *below* the venue root as a finding in its own right: a deeper ignore file outranks the venue's root `.ignore` regardless of type, and a vendor `.unitypackage` can ship one.

### 3. Judge the residue

Split the hidden set by whether an agent searching the venue would be misled:

- **Text-bearing files must be visible.** Scenes, prefabs, materials, controllers, `.meta` sidecars, JSON, shaders, scripts. A hidden one is the confident-zero failure.
- **Binary payloads may stay hidden, but the loss is enumeration, not just content.** ripgrep skips binary *content* either way; what hiding also costs is `rg --files` — "does texture X exist" then answers falsely. Accept that trade deliberately per venue, don't assume it.
- **Generated output is a real hide.** Shader-lock output and similar regenerated trees are noise an agent should not be reading.

**The trap that survives a careless fix:** a `!`-rule naming a *directory* un-prunes that directory, and then every child is re-tested individually against the remaining rules. So `!/Assets/Agent/RunLogs/` does not cover a `.gitignore` rule of `/Assets/Agent/RunLogs/*` — the directory is walked and every file in it is hidden anyway. Match the exclusion's granularity: a `/*` or glob exclusion needs a `!` that matches those same files (`!/Assets/Agent/RunLogs/*`).

### 4. Propose, gate, apply

Bring the operator the hidden text-bearing paths, the `.ignore` lines that would re-include them, and what you propose to leave hidden with the reason. **The `.ignore` edit is the operator's sign-off** — it changes what every later agent in that venue can see.

The edit lands in an untracked venue file, so no PR carries it and git holds no history of it; say so when you report, and keep the audit's before/after counts in your own transcript as the only record.

### 5. Verify

Re-run step 2 and show the hidden set shrank to exactly what step 3 declared should stay hidden. A count alone is not the check — name the residue. Re-running with the venue's `.ignore` temporarily moved aside reproduces the unfixed state and proves the file is what is doing the work.
