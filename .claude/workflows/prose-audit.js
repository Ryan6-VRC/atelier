export const meta = {
  name: 'prose-audit',
  description: 'Corpus audit of governed prose against docs/tool-design.md: domain-batched conformance, claims-index reduce, primary-text verification, adversarial refute, funnel report',
  whenToUse: 'Operator-run meter for the prose-governance system. Enumerate governed files first (git ls-files + untracked-not-ignored .md across the meta-repo and vrc-* siblings, minus the fence exclusions in tool-design.md) and pass as args: {files: [...]}, repo-relative. They resolve against the checkout you invoke from, so running this in a worktree audits that worktree; {root: "<path>"} pins a different one. For re-runs after a full pass, pass only files changed since the last audit (git log) plus the files they cite — the meter is differential by construction. Intermediates land in test-output/prose-audit/ (disposable). Report the funnel with a git-log denominator of governed-prose commits since the last run. A run with failed_units is INCOMPLETE, never a clean bill.',
  phases: [
    { title: 'Conformance', detail: 'one auditor per domain cluster; policy and neighborhoods amortized' },
    { title: 'Reduce', detail: 'mechanical claim grouping, then LLM judgment on collision buckets' },
    { title: 'Verify', detail: 'cross-file candidates re-read at the sources; findings refereed per unit' },
  ],
}

const CLAIMS = 'test-output/prose-audit/claims'

// args may arrive as a JSON-encoded string depending on the caller — accept both.
const a = typeof args === 'string' ? JSON.parse(args) : args
const files = (a && a.files) || []
if (!files.length) throw new Error('pass args {files: [...]} — enumerate the governed fence first (see whenToUse)')
// Model for every subagent. Omitted → inherits the session model; pass {model: "opus"}
// to run the audit a tier down — the judgment here survives that fine.
const MODEL = (a && a.model) || undefined
// Prefix for every path handed to a subagent. RELATIVE by default: a workflow subagent
// inherits the session's cwd (measured — its pwd is the session cwd, and a repo-relative
// Read resolves against it), so the audit follows the checkout it was invoked from. An
// absolute root here would silently audit that one instead: run from a worktree, it would
// report a confident funnel about the main checkout's prose rather than the edits under
// review, which is the failure this meter exists to catch in other people's work.
// {root: "<path>"} pins a specific checkout when that is what you actually want.
const ROOT = (a && a.root) || '.'
const POLICY = `${ROOT}/docs/tool-design.md`

// ---- group into domain clusters (token amortization: shared policy + neighborhoods) ----
// Fixed doc clusters mirror the corpus's own citation clusters; files not claimed
// by a fixed cluster fall through to generic buckets, so a differential run with
// three files still produces small, valid units.
//
// Membership is a hand list on purpose: CLAUDE.md's read-when index owns a different fact (which doc a
// class of work reads) and has no cluster structure to derive from, and the fence reaches vrc-* siblings
// and .claude/skills/ that the index never names. Decisions already made here, so they are not re-argued:
//  - Cross-citation counts are a TIEBREAKER, not a basis for moving a stable file: a basename mention is
//    a declared route, and the verify phase below treats route+guard pairs as refutations — so citation
//    density selects for already-adjudicated pairs and against the undeclared duplication phase 1 hunts.
//  - verify.md stays in docs-unity: measured both ways it is 8-out/6-in to EITHER home, so a move is churn.
//  - runtime.md ties to docs-animator (gimmicks 15) over docs-live (emulator 6).
//  - mochifitter.md stays in docs-meta, and docs-process is justified by unit balance, not by its one
//    dispatched-work->workflow citation, which is noise.
const CLUSTERS = [
  ['docs-animator', ['docs/animator.md', 'docs/animator-schema.md', 'docs/gimmicks.md', 'docs/runtime.md']],
  ['docs-unity', ['docs/unity.md', 'docs/unity-tools.md', 'docs/nondestructive.md', 'docs/verify.md', 'docs/LAYOUT.md']],
  ['docs-live', ['docs/emulator.md', 'docs/osc.md', 'docs/vrchat-client.md']],
  ['docs-meta', ['CLAUDE.md', 'README.md', 'TOOLS.md', 'docs/tool-design.md', 'docs/bootstrap.md', 'docs/new-project.md', 'docs/mochifitter.md']],
  ['docs-process', ['docs/workflow.md', 'docs/dispatched-work.md', '.claude/skills/dispatch/SKILL.md', '.claude/skills/kickoff/SKILL.md']],
  ['docs-rest', ['docs/blender.md', 'docs/menus.md', 'docs/outfits.md', '.claude/skills/write-for-agents/SKILL.md']],
]
// CLUSTERS is static config, so assert it here rather than inside take(): a file listed in two clusters
// is audited twice, and checking as files arrive would only catch it when both copies are in the run.
const declared = new Set()
for (const [id, fs] of CLUSTERS) for (const f of fs) {
  if (declared.has(f)) throw new Error(`CLUSTERS defect: "${f}" is listed in more than one cluster (again in ${id})`)
  declared.add(f)
}

const units = []
const claimed = new Set()
const take = (id, fs) => { const hit = fs.filter(f => files.includes(f)); if (hit.length) { units.push({ id, files: hit }); hit.forEach(f => claimed.add(f)) } }
for (const [id, fs] of CLUSTERS) take(id, fs)

const rest = (pred) => files.filter(f => !claimed.has(f) && pred(f))
const takeAll = (id, fs) => { if (fs.length) { units.push({ id, files: fs }); fs.forEach(f => claimed.add(f)) } }
// Every generic bucket chunks. A bucket handed whole to one auditor stops amortizing and starts
// crowding: vrc-patterns alone is 25 files / ~247 KB, which is a unit that cannot be read closely.
const CHUNK = 8
const takeChunked = (id, fs) => { for (let i = 0; i < fs.length; i += CHUNK) takeAll(`${id}-${1 + i / CHUNK}`, fs.slice(i, i + CHUNK)) }
takeChunked('skills', rest(f => /^vrc-skills\//.test(f)))
takeChunked('patterns', rest(f => /^vrc-patterns\//.test(f)))
takeChunked('subrepos', rest(f => /^vrc-/.test(f)))
// Whatever no cluster claimed. Reported by name in the return value: a governed file landing here is
// valid (that is what the bucket is for) but a DOC landing here has lost its citation neighborhood,
// which is how four docs went unclustered for three weeks without the funnel ever looking wrong.
const ungroupedFiles = rest(() => true)
takeChunked('ungrouped', ungroupedFiles)
log(`${units.length} units over ${files.length} files`)

// ---- schemas ----------------------------------------------------------------------
const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      kind: { type: 'string', enum: ['tier-misfit', 'unmanaged-duplication', 'undeclared-echo', 'contradiction', 'derivable-prose', 'dangling-route', 'route-without-guard', 'register-violation', 'gate-defect', 'lift-candidate', 'other'] },
      where: { type: 'string' }, claim: { type: 'string' }, evidence: { type: 'string' },
      policy_section: { type: 'string' }, suggested_fix: { type: 'string' },
    }, required: ['kind', 'where', 'claim', 'evidence', 'policy_section'] } },
  }, required: ['findings'],
}
const BUCKETS = { type: 'object', properties: { bucket_count: { type: 'number' }, buckets_path: { type: 'string' } }, required: ['bucket_count', 'buckets_path'] }
const CANDIDATES = { type: 'object', properties: { candidates: { type: 'array', items: { type: 'object', properties: {
  subject: { type: 'string' }, locations: { type: 'array', items: { type: 'string' } },
  klass: { type: 'string', enum: ['unmanaged-duplication', 'echo-drift', 'contradiction'] }, note: { type: 'string' },
}, required: ['subject', 'locations', 'klass'] } } }, required: ['candidates'] }
const VERDICT = { type: 'object', properties: { status: { type: 'string', enum: ['confirmed', 'refuted'] }, reason: { type: 'string' } }, required: ['status', 'reason'] }
const VERDICTS = { type: 'object', properties: { verdicts: { type: 'array', items: { type: 'object', properties: {
  index: { type: 'number' }, status: { type: 'string', enum: ['confirmed', 'refuted'] }, reason: { type: 'string' },
}, required: ['index', 'status', 'reason'] } } }, required: ['verdicts'] }

// ---- phase 1: conformance (also writes the claims digests) -------------------------
phase('Conformance')
const conformPrompt = (u) => `Prose-governance conformance auditor, Atelier workspace.
Policy first: read ${POLICY} — the sections from "Where knowledge lives" onward are the rules; cite the section in every finding.
Your unit "${u.id}" (read every file fully): ${u.files.map(f => `${ROOT}/${f}`).join(', ')}.
Neighborhood discipline (token budget is real): judge within your batch first — most citation neighbors are IN it. Open a file outside the batch only to verify a specific suspicion (a route you think dangles, a passage you think is duplicated), never for general orientation. No workspace-wide grepping.
Judge (judgment only — the mechanical linter owns anatomy presence checks like Use-when prefix, description length, no-operator pointer, terminal-Tools heading; skip those):
1. Tier fit — each fact class at its right rung? For docs: does CLAUDE.md's read-when line match the content?
2. Routes — pointers pair with a guard against restating? Dangling or wrong-target routes?
3. Duplication — passages restating what a citable doc owns (quote both); echoes without a declared canon.
4. Contradiction — files disagreeing on the same subject (quote both).
5. Register — serves its declared reader? Dual-register: audience gradient held?
6. Lift candidates — trap prose meeting BOTH conditions (machine-recognizable at an existing chokepoint + judgment-free); name the chokepoint.
7. Skills only: are the gates the right gates, is the required reading correctly named (vrc-skills/CONVENTIONS.md)?
ALSO write ONE claims digest for the whole unit to ${ROOT}/${CLAIMS}/${u.id}.md (create dirs), max ~40 lines, format exactly: subject-key | claim in <=20 words | file:line. subject-key = the substrate handle (tool/doc/param/mechanism name), lowercase-kebab. Prioritize claims another file might also carry — the digest exists to catch cross-file collisions, not to inventory the unit.
Findings: only defects you would defend to a skeptic; an empty list is a valid answer.`

const conform = await pipeline(units, u => agent(conformPrompt(u), { label: `conform:${u.id}`, phase: 'Conformance', schema: FINDINGS, model: MODEL }))
const failedUnits = units.filter((u, i) => !conform[i]).map(u => u.id)
const rawFindings = conform.flatMap((r, i) => (r ? r.findings.map(f => ({ ...f, unit: units[i].id })) : []))
log(`conformance: ${rawFindings.length} raw findings; ${failedUnits.length} unit(s) FAILED`)
// Fail loud, and don't spend the downstream phases on a broken base.
if (failedUnits.length > units.length / 4) {
  return { status: 'INCOMPLETE — do not treat as a clean audit', failed_units: failedUnits, ungrouped_files: ungroupedFiles, funnel: { units: units.length, units_failed: failedUnits.length, raw_conformance_findings: rawFindings.length } }
}

// ---- phase 2: reduce (barrier is genuine: grouping needs every digest) ---------------
phase('Reduce')
const grouper = await agent(`Run a Python one-off (script in test-output/prose-audit/ if needed, never tools/) that reads every file in ${ROOT}/${CLAIMS}/, parses "subject-key | claim | location" lines, normalizes keys (lowercase, strip plurals/punctuation), groups by key, and writes ${ROOT}/test-output/prose-audit/buckets.json as a JSON array of {subject, entries: [{claim, location, digest}]} keeping ONLY subjects spanning more than one digest file. Return the bucket count and path.`, { label: 'reduce:group', phase: 'Reduce', schema: BUCKETS, effort: 'low', model: MODEL })

let candidates = []
let reduceIncomplete = false
if (grouper && grouper.bucket_count > 0) {
  const JUDGES = Math.min(3, Math.max(1, Math.ceil(grouper.bucket_count / 30)))
  const judged = await parallel(Array.from({ length: JUDGES }, (_, j) => () =>
    agent(`Read ${ROOT}/test-output/prose-audit/buckets.json. Judge buckets with index % ${JUDGES} == ${j} (0-based). For each: same fact? If yes — declared echo of a named canon (flag only if drifted: echo-drift), unmanaged-duplication (no site owns it), or contradiction (entries disagree)? Policy: ${POLICY} §Duplication. Work from the quoted claims; open a source only when the claims cannot settle it. Drop same-word-different-fact noise.`,
      { label: `reduce:judge-${j}`, phase: 'Reduce', schema: CANDIDATES, model: MODEL })))
  reduceIncomplete = judged.some(r => !r)   // a dead judge left its share of buckets unjudged
  candidates = judged.filter(Boolean).flatMap(r => r.candidates)
}
log(`reduce: ${grouper ? grouper.bucket_count : 0} buckets → ${candidates.length} candidates`)

// ---- phase 3: verify — candidates at the sources; findings refereed per unit ---------
phase('Verify')
const verifiedCandidates = await pipeline(candidates, c =>
  agent(`Verify a cross-file candidate. Subject: ${c.subject}. Class: ${c.klass}. Locations: ${c.locations.join('; ')}. Note: ${c.note || 'none'}.
Read the ACTUAL passages at every location (digests flatten nuance — the sources decide). Confirm only a real unmanaged duplication, drifted declared echo, or genuine contradiction per ${POLICY} §Duplication. Managed echoes in agreement, topical overlap, or route+guard pairs are refutations.`,
    { phase: 'Verify', label: `verify:${c.subject.slice(0, 30)}`, schema: VERDICT, model: MODEL })
    .then(v => ({ ...c, verdict: v })))

const byUnit = {}
rawFindings.forEach((f, i) => { (byUnit[f.unit] = byUnit[f.unit] || []).push({ ...f, index: i }) })
const refereed = await pipeline(Object.entries(byUnit), ([unit, fs]) =>
  agent(`Adversarial referee for ${fs.length} prose-governance finding(s) in unit "${unit}". For EACH, read the primary source and the cited policy section in ${POLICY}, then verdict by index:
${fs.map(f => `[${f.index}] (${f.kind}) at ${f.where}: ${f.claim} — evidence: ${f.evidence} — policy: ${f.policy_section}`).join('\n')}
Honest verdicts — confirm real violations; refute misreadings, register mismatches with the policy's actual words, or defects the policy tolerates (declared echoes, routes with guards, human-facing register). Neither killing nor keeping is the goal; being right is.`,
    { phase: 'Verify', label: `referee:${unit}`, schema: VERDICTS, model: MODEL }))

const verdictByIndex = {}
refereed.filter(Boolean).flatMap(r => r.verdicts).forEach(v => { verdictByIndex[v.index] = v })
const confirmedFindings = rawFindings.map((f, i) => ({ ...f, verdict: verdictByIndex[i] })).filter(f => f.verdict && f.verdict.status === 'confirmed')
const refutedFindings = rawFindings.map((f, i) => ({ ...f, verdict: verdictByIndex[i] })).filter(f => f.verdict && f.verdict.status === 'refuted')
const confirmedCross = verifiedCandidates.filter(Boolean).filter(c => c.verdict && c.verdict.status === 'confirmed')

// Fail loud on a silently-partial run — the skill's contract is "never a clean bill on a
// partial". A dead grouper skips cross-file detection outright; a dead judge leaves buckets
// unjudged; an unrefereed finding never got adjudicated. None of these is 'complete', yet
// each collapses to a benign-looking funnel count a reader can't distinguish from a clean pass.
const unrefereed = rawFindings.length - confirmedFindings.length - refutedFindings.length
const incomplete = []
if (failedUnits.length) incomplete.push(`${failedUnits.length} conformance unit(s) failed`)
if (!grouper) incomplete.push('reduce grouper failed (cross-file detection did not run)')
else if (reduceIncomplete) incomplete.push('a reduce judge failed (some buckets unjudged)')
if (unrefereed) incomplete.push(`${unrefereed} finding(s) unrefereed`)

return {
  status: incomplete.length ? `INCOMPLETE — ${incomplete.join('; ')}` : 'complete',
  failed_units: failedUnits,
  ungrouped_files: ungroupedFiles,
  funnel: {
    units: units.length,
    units_failed: failedUnits.length,
    raw_conformance_findings: rawFindings.length,
    confirmed_conformance_findings: confirmedFindings.length,
    refuted_conformance_findings: refutedFindings.length,
    unrefereed_findings: unrefereed,
    claim_collision_buckets: grouper ? grouper.bucket_count : 0,
    cross_file_candidates: candidates.length,
    confirmed_cross_file: confirmedCross.length,
  },
  confirmed_findings: confirmedFindings,
  confirmed_cross_file: confirmedCross,
  refuted_with_reasons: refutedFindings.map(f => ({ where: f.where, claim: f.claim, reason: f.verdict.reason })),
}
