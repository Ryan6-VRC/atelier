---
name: batch-venue-work
description: Use when the operator hands over a batch of venue asset work to build as one job under one orchestrator — "I want these six compositions", a set of vendor packages to import, own and compose, any multi-item run where the goal is the whole batch built fast and verified once at the end — and to close it ("/batch-venue-work close"). Not a wave of fresh sessions on metarepo or tooling work (dispatch), not one brief for a later session (kickoff), not the per-item asset skills, which this skill calls.
---

# Batch venue work

Invoking this skill switches the session into batch mode: the deliverable is the whole batch, built by as many subagents as it has work for, against one Editor, with verification and prose done once at the end. `tools/batch-mode-hook.ps1` holds the mode for the session by machine, not memory: it appends `.claude/skills/batch-venue-work/worker-rails.md` to every subagent brief, restates the batch rule on every prompt, and re-dumps this body after compaction. The per-item skills own the work; this skill owns sequencing, the brief, and the operator's instruction ledger.

**No operator to ask?** `workflow.md` §No operator to ask? — its batch form: work that does not depend on an answer proceeds, work that does is left undone and named, never guessed, and the questions surface in one block when the operator can see the scene. A subject left visibly wrong turns a question into a glance; a plausible value hides it.

## Mode

- **Unlimited fan-out against one Editor** — CLAUDE.md rule 9's carve-out. The Unity bridge queues every call onto the Editor's main thread in order, so agents serialise at the transport and collide only on content: disjoint buckets, nobody in play mode, and the scene saved by one live agent at a time are the whole safety condition. Spawn everything that is not blocked, now. Width is spent, never rationed, and a granted width is not re-asked.
- **Gates only.** Play mode, bakes and uploads are the operator's unless the batch says otherwise. State that default in the plan in one line; do not ask it.
- **No prose until close, yours included.** No skill authoring, no inbox notes, no record mid-batch; agents carry what the record needs in their reports, and no brief asks for a file.
- **You drive no Editor call yourself.** Your reads queue behind the fan-out while the operator waits on you. Dispatch reads too, on a cheap model.
- **Free text only.** Never `AskUserQuestion`; the operator answers a plan in prose.

## The flow

### 1. Survey — one agent, one bucket map back

Each item, its source, its bucket, what it pulls in. Two minutes of your own reading is the cap: a coordinator that surveys by hand plans from a partial read, and every wrong plan launches before the first agent does.

### 2. Plan — one screen

Items, buckets, agents, and which agents start now. Defaults stated, not asked. Launch on the operator's word.

### 3. Intake — serial, one agent

Bringing material in mutates project-wide state — import settings, category folders — that a second writer cannot see.

### 4. Own — parallel, one agent per item

Each item's source, working file and output prefab are disjoint; state the bucket and say the batch is parallel.

### 5. Compose — one scene agent

Exactly one live agent holds the scene and saves it; everyone else edits prefab assets and never saves. Test each new task against the buckets in flight; an overlap is sequenced, not parallelised.

### 6. The tail — dispatch, never carry

Every instruction line in an operator prompt becomes a live agent or a named blocker in the same turn; "queued" is not a state, and a todo carried across turns is the instruction that gets lost. When the operator reports a defect, inventory its whole class once — every mesh not on a toggle, every menu missing a leaf — and put the list to them, instead of one fix per turn. When the operator says do X, do X: relay no subagent's objection, offer no hypothesis in place of the work.

### 7. Close — `/batch-venue-work close`

Ends the mode. Then in parallel: one reviewer per composition against the finished state, one prose agent per bucket for the venue record (`docs/VENUE.md` binds), then commit. Verify happens here, once, and is never omitted.

## The brief

Under 250 words; the hook appends the rails, so do not paste them. End state; the bucket boundary as a sentence; the traps that fail silently; what not to fix; a few lines back. Name the file that adjudicates a fact rather than the fact, and mark anything relayed from another agent's report as a claim to verify. Nothing on method, nothing on how to confirm: a build agent is fast, and the scaffolding in its brief is what makes it slow.

## Out of scope by default

Blendshape-driven clips: the operator fixes them by hand faster than an agent reasons about them; leave the row at its fail-safe value and report. A visual defect the operator reports is on the composed, posed avatar in Unity and is measured in triangles; one pass, no loops.
