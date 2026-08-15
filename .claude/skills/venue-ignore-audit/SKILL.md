---
name: venue-ignore-audit
description: Use when a Unity venue's search visibility is in question — auditing what `Grep`/ripgrep cannot see under a venue's `Assets/`, seeding or repairing a venue's `.ignore` ("why did that grep find nothing", "check the venue's ignore files", "did my search actually cover Vendor?"), or as the closing move of a new venue's first setup step. Run it after any edit to a venue's `.gitignore` or `.ignore`. Not prose governance over tracked markdown (`check_prose.py`), and not the venue bring-up itself (`docs/new-project.md` owns that runbook; this skill owns its ignore-file step).
---

# Audit a venue's search visibility

A venue's `.gitignore` decides what `Grep` can see, because ripgrep honors it wherever a `.git` sits in an ancestor directory — which every venue under the workspace root inherits by accident of where it sits. The venue's own `.ignore` is the only file that can re-include what it drops. The mechanics live in `docs/unity.md` §Sharp edges and `docs/new-project.md` step 1; this skill owns the audit and its judgment calls.

The failure is silent and self-concealing: a sweep over a hidden tree returns a confident zero, and nothing inside the search result says a tree was skipped. Measured on both live venues, a venue missing its `.ignore` re-includes hides over 90% of everything under its `Assets/` from every search. That is why this runs on a schedule of suspicion rather than on a verdict — no check fires it.

**No operator to ask?** `docs/workflow.md` §No operator to ask? owns the protocol. The derivable default is to report the audit and change nothing: an `.ignore` edit silently redefines what every later agent can see, so it is never an unattended call.

## The flow

### 1. Discover the venues

A directory is a venue iff it holds `ProjectSettings/ProjectVersion.txt`, `Assets/`, and `Packages/vpm-manifest.json`. Scan the workspace root's immediate children for that signature and never name a venue in tracked code (`CLAUDE.md` §Layout) — venues are the operator's alone.

List with `ls`, not `Grep`/`Glob`: the workspace root's own `.ignore` deliberately leaves an added venue hidden from ripgrep, so an rg-based discovery finds the sample venue and silently misses every personal one. From a worktree the venues are absent entirely — resolve the main checkout (`python tools/atelier_paths.py` prints it; that module owns the invariant), and audit there.

### 2. Measure what is hidden

Two passes per venue, **rooted at the venue directory**. Rooting at `Assets/` overreports: an ignore file *above* the root you name keeps only its **unanchored** rules at every depth below, while a rule anchored to that file's own directory stops applying past the first level beneath the named root — so an `Assets/`-rooted sweep still lists the `Agent/RunLogs/` and `Agent/Scratch/` that a real workspace-level `Grep` cannot reach.

```
rg --files . ; rg --files --no-ignore-vcs .
```

Diff the two. The second pass disables the `.gitignore` side **only**: the venue's `.ignore` keeps pruning `Library/`, `Temp/`, `Obj/`, `Logs/`, `UserSettings/`, which is deliberate. Disabling `.ignore` too (`--no-ignore-dot`, `--no-ignore`) drops those prunes back into the hidden set, where regenerated `Library/` content outnumbers everything else by roughly an order of magnitude — and step 3 then classifies `PackageCache`'s C# as text-bearing that must be re-included, walking the operator into signing off the exact regression the runbook's prunes prevent.

Measure, never infer from reading the two ignore files against each other — a textual pairing looks covered in exactly the cases that are blind, step 3's trap being that shape.

Assert the prune half too: pass 1 must list no `Library/`, `Temp/` or `Logs/` paths. An empty diff means nothing on a venue that never inherited a `.gitignore` at all — one placed outside the workspace root gets none, and its unpruned `Library/` times out every `Grep`. Report a venue with no `!` line in the *workspace* root's `.ignore` **or its untracked `.rgignore`** as the dominant finding whatever the diff says: it is invisible to every workspace-rooted search regardless of its own files. A personal venue can only be named in the `.rgignore`, since `CLAUDE.md` §Layout keeps it out of tracked code, so check that file rather than concluding from `.ignore` alone — and measure it, because a venue excluded by `.git/info/exclude` rather than by `.gitignore` is hidden just as completely and by a file neither of the step-2 passes reports.

Dot-prefixed paths need their own pass, because the counting passes above never list them:

```
rg --files --hidden --no-ignore -g '**/.gitignore' -g '**/.ignore' -g '**/.rgignore' .
```

Anything below the venue root is a finding in its own right: a deeper ignore file outranks the venue's root `.ignore` regardless of type, and a vendor `.unitypackage` can ship one.

### 3. Judge the residue

Split the hidden set by whether an agent searching the venue would be misled:

- **Text-bearing files must be visible.** Scenes, prefabs, materials, controllers, `.meta` sidecars, JSON, shaders, scripts. A hidden one is the confident-zero failure.
- **Binary payloads may stay hidden, but the loss is enumeration, not just content.** A content search stops at the first NUL byte either way, but hiding also costs `rg --files`, so "does texture X exist" answers falsely. Accept that trade deliberately per venue, don't assume it.
- **Generated output is a real hide.** Shader-lock output and similar regenerated trees are noise an agent should not be reading.

**The trap that survives a careless fix is a granularity mismatch, and it cuts both ways.** `!dir/` only stops `dir` being pruned; against a rule matching the files *inside* it (`/Assets/Agent/RunLogs/*`) the directory is walked and every file stays hidden, so the line reads as a re-include and contributes nothing — `!dir/*` is the form that answers such a rule. Against a rule pruning the directory itself (`/Assets/Agent/Scratch/`) the mapping inverts: `!dir/*` whitelists children ripgrep never descends to reach, and `!dir/` is the working form. Writing both is not a safe hedge — on a directory-pruning rule the `/*` line additionally overrides the venue's extension rules, dragging binaries back into the visible set that step 3 just declared should stay hidden. One form per rule, chosen by the rule's shape, and confirmed in the step-5 re-measure rather than by reading the pair.

### 4. Propose, gate, apply

Bring the operator the hidden text-bearing paths, the `.ignore` lines that would re-include them, and what you propose to leave hidden with the reason. **The `.ignore` edit is the operator's sign-off** — it changes what every later agent in that venue can see.

The edit lands in an untracked venue file, so no PR carries it and git holds no history of it; say so when you report, and keep the audit's before/after counts in your own transcript as the only record.

### 5. Verify

Re-run step 2 and show the hidden set shrank to exactly what step 3 declared should stay hidden. A count alone is not the check — name the residue. Re-running pass 1 with `--no-ignore-dot` shows the venue as if its `.ignore` were absent, proving the file is what is doing the work — never move it aside, which mutates a live venue into a state it was never in.
