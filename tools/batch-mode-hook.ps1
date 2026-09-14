# Holds "batch mode" for a session, so the posture the batch-venue-work skill declares is enforced by
# machine rather than remembered by the model. A coordinator's posture decays over a long session
# (compaction, drift) and reaches its subagents only if every brief restates it. Measured on the batch
# the skill was drafted from: 27 of 32 briefs demanded prose and verification the operator had ruled
# out, and one operator instruction was carried for 79 minutes without being dispatched.
#
# The mode is a marker file keyed on session_id. Subagents share their parent's session_id, so every
# hook fire in the session sees the same answer without any per-agent bookkeeping.
#
# Arms, by hook_event_name:
#   PreToolUse/Skill   `batch-venue-work` turns the mode on; args containing `close` turn it off. Both
#                      answer with one line of context so the model knows which state it is in.
#   PreToolUse/Agent   mode on: worker-rails.md (beside the skill) is appended to the subagent's prompt
#                      through updatedInput, so the brief carries the rails whether or not the
#                      coordinator wrote them. Measured on the shipped binary: updatedInput reaches the
#                      subagent as its prompt. A prompt already carrying the rails is left alone.
#   PreToolUse/Write|Edit|NotebookEdit   mode on and the target is .md: DENIED, with the reason. This is
#                      the one arm that blocks, deliberately: mid-batch prose is the failure the mode
#                      exists against, and a nudge in briefs was already tried and ignored. Bash-side
#                      markdown writes are not caught; this is a fence on the tools that carry a path.
#   UserPromptSubmit   mode on: one line, the mode's age and the dispatch-or-name rule.
#   SessionStart       (matched to `compact` in settings) mode on: the skill body dumped whole, since
#                      compaction dropped it.
# Every other path exits 0 silently. Marker expiry is 12 hours: longer than any batch, short enough
# that a session that never closed cannot poison the next day's.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Emit($obj) { $obj | ConvertTo-Json -Depth 6 -Compress | Write-Output }

try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }
    $ev = $raw | ConvertFrom-Json
    $event = [string]$ev.hook_event_name
    if (-not $event -or -not $ev.session_id) { exit 0 }
    $sid = [string]$ev.session_id

    $tempBase = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
    $markerRoot = [System.IO.Path]::Combine($tempBase, 'claude-batch-mode')
    $marker = [System.IO.Path]::Combine($markerRoot, "$sid.marker")
    $projDir = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }
    $skillDir = [System.IO.Path]::Combine($projDir, '.claude', 'skills', 'batch-venue-work')

    $on = $false; $since = $null
    try {
        $m = Get-Item -LiteralPath $marker -ErrorAction SilentlyContinue
        if ($m -and -not $m.PSIsContainer) {
            if ($m.LastWriteTime -gt (Get-Date).AddHours(-12)) { $on = $true; $since = $m.LastWriteTime }
            else { Remove-Item -LiteralPath $marker -Force -ErrorAction SilentlyContinue }
        }
    } catch { }

    $tool = [string]$ev.tool_name
    $ti = $ev.tool_input

    if ($event -eq 'PreToolUse' -and $tool -eq 'Skill') {
        $skill = [string]$ti.skill
        if ($skill -notmatch '(^|:)batch-venue-work$') { exit 0 }
        $skillArgs = [string]$ti.args
        if ($skillArgs -match '(^|\s)close(\s|$)') {
            Remove-Item -LiteralPath $marker -Force -ErrorAction SilentlyContinue
            Emit @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; additionalContext =
                'Batch mode is OFF for this session: markdown writes are allowed again and subagent briefs no longer carry the worker rails. The closing pass runs now: reviewers, then the venue record, then commit.' } }
            exit 0
        }
        New-Item -ItemType Directory -Force -Path $markerRoot | Out-Null
        Set-Content -LiteralPath $marker -Value (Get-Date).ToString('o')
        Get-ChildItem -LiteralPath $markerRoot -File -Filter '*.marker' -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-2) } |
            Remove-Item -Force -ErrorAction SilentlyContinue
        Emit @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; additionalContext =
            'Batch mode is ON for this session (tools/batch-mode-hook.ps1): every subagent brief gets worker-rails.md appended, markdown writes are refused until `/batch-venue-work close`, and each prompt restates the dispatch-or-name rule.' } }
        exit 0
    }

    if (-not $on) { exit 0 }

    if ($event -eq 'PreToolUse') {
        if ($tool -eq 'Agent') {
            $prompt = [string]$ti.prompt
            if ($prompt -match 'Batch mode rails') { exit 0 }
            $rails = $null
            try { $rails = Get-Content -LiteralPath ([System.IO.Path]::Combine($skillDir, 'worker-rails.md')) -Raw -ErrorAction Stop } catch { }
            if (-not $rails) { $rails = 'Batch mode rails: read `.claude/skills/batch-venue-work/worker-rails.md` before doing anything; this hook could not read it.' }
            $updated = @{}
            foreach ($p in $ti.PSObject.Properties) { $updated[$p.Name] = $p.Value }
            $updated['prompt'] = $prompt.TrimEnd() + "`n`n" + $rails.TrimEnd() + "`n"
            Emit @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; permissionDecision = 'allow'; updatedInput = $updated } }
            exit 0
        }
        if ($tool -eq 'Write' -or $tool -eq 'Edit' -or $tool -eq 'NotebookEdit') {
            $path = if ($ti.file_path) { [string]$ti.file_path } elseif ($ti.notebook_path) { [string]$ti.notebook_path } else { $null }
            if ($path -and $path -match '\.md$') {
                Emit @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; permissionDecision = 'deny'; permissionDecisionReason =
                    'Batch mode: no prose until the batch closes. Markdown writes are refused until `/batch-venue-work close` has run. Carry the fact in your report; the closing pass writes the record once.' } }
                exit 0
            }
        }
        exit 0
    }

    if ($event -eq 'UserPromptSubmit') {
        $mins = [int]((Get-Date) - $since).TotalMinutes
        Emit @{ hookSpecificOutput = @{ hookEventName = 'UserPromptSubmit'; additionalContext =
            "Batch mode, on for $mins min. Every instruction in this prompt becomes a live agent or a named blocker in this turn; you drive no Editor call yourself; markdown writes are refused until ``/batch-venue-work close``." } }
        exit 0
    }

    if ($event -eq 'SessionStart') {
        $body = $null
        try { $body = Get-Content -LiteralPath ([System.IO.Path]::Combine($skillDir, 'SKILL.md')) -Raw -ErrorAction Stop } catch { }
        $msg = if ($body) { "Batch mode is still ON for this session after compaction. The batch-venue-work skill body follows whole.`n`n$body" }
               else { 'Batch mode is still ON after compaction; re-read .claude/skills/batch-venue-work/SKILL.md (this hook could not read it).' }
        Emit @{ hookSpecificOutput = @{ hookEventName = 'SessionStart'; additionalContext = $msg } }
        exit 0
    }
    exit 0
}
catch { exit 0 }
