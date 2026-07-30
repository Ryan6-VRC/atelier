# PostToolUse hook on Write|Edit. One job: when the agent authors markdown in this workspace or one
# of its worktrees, inject one line routing to the write-for-agents skill and the constitution.
# Scope is everything the agent writes — tracked or not, ignored or not. A file does not stop
# being worth writing well because git declines to store it, and this nudge is advice, not
# enforcement: the governed fence still decides what the commit-time form gate checks, and the
# two scopes are allowed to differ.
# One fire per file per agent per 45min. Repetition manufactures banner blindness; the expiry
# is what makes the line come back, since compaction drops injected context but leaves the
# session id. agent_id belongs in the key because hooks fire inside subagents, where most prose
# is written, and a parent's fire would otherwise mask theirs.
# Never block: every path out exits 0. Non-matching paths exit silently, so a normal edit pays no
# context cost — but a marker store that cannot be read or written nudges anyway. A repeated
# banner is a nuisance; a dropped one is a hole in the routing, and an unwritable TEMP would
# otherwise disable this hook for every edit, permanently, with no signal at all.
#
# The /bin/sh predecessor this replaces lost its whole defect class in the port — path-flavor
# conversion, cygpath, jq, cksum and find were the substrate every one of its bugs came from.
#
# Proportion, before hardening anything here: every failure mode this script has costs one missing
# or one duplicated banner and nothing else. The known gaps are documented, not defended —
# markdown written through Bash never reaches a Write|Edit hook, and a junction-reached path
# misses the scope compare. Weigh anything new against a worst case of one absent line of advice.

$ErrorActionPreference = 'Stop'

try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }
    $ev = $raw | ConvertFrom-Json

    $path = $ev.tool_input.file_path
    if (-not $path) { exit 0 }
    if ($path -notmatch '\.md$') { exit 0 }

    $full = [System.IO.Path]::GetFullPath($path)

    # --- scope gate ---
    # This workspace and its worktree siblings, resolved from $PSScriptRoot — the hook lives inside
    # the one tree it governs, so neither root needs configuration and a global install is not a
    # case to handle. The predecessor derived the root from $0 and needed `pwd -P` plus a self-check
    # to catch a path-flavor mismatch that silently un-governed everything; PowerShell has no such
    # failure, so that report is gone with the machinery that needed it.
    # `<root>-worktrees/` is the second base because a session rooted in the main tree does most of
    # its authoring inside a worktree there, and worktree prose is this workspace's prose. Both
    # bases demand the trailing separator, so a sibling named AtelierOther still cannot prefix-match
    # — that guard is what excluded the worktrees, not an accident of it.
    # The remaining unrouted prose is not a scope problem and cannot be fixed here: a session whose
    # project dir is a sibling `vrc-*` repo registers no hook at all, since none of them carries a
    # `.claude/settings.json`.
    $root = (Split-Path -Parent $PSScriptRoot).TrimEnd('\', '/')
    $sep = [System.IO.Path]::DirectorySeparatorChar
    $base = @($root, "$root-worktrees") | Where-Object {
        $full.StartsWith("$_$sep", [System.StringComparison]::OrdinalIgnoreCase)
    } | Select-Object -First 1
    if (-not $base) { exit 0 }

    $sid = if ($ev.session_id) { $ev.session_id } else { 'nosession' }
    $scope = if ($ev.agent_id) { "$sid-$($ev.agent_id)" } else { $sid }
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $key = [System.BitConverter]::ToString(
        $md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($full.ToLowerInvariant()))
    ) -replace '-', ''
    # [IO.Path]::Combine, not Join-Path: Join-Path resolves the PSDrive, so a TEMP pointing at an
    # unmounted drive throws before any of the best-effort handling below can absorb it. The base
    # is guarded because PowerShell binds a null env var to '', and Combine('', x) yields a
    # relative path — which would put the marker store in whatever directory the hook ran from.
    $tempBase = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
    $markerRoot = [System.IO.Path]::Combine($tempBase, 'claude-prose-hook')
    $dir = [System.IO.Path]::Combine($markerRoot, $scope)
    $marker = [System.IO.Path]::Combine($dir, $key)
    # Only a marker that is demonstrably a fresh FILE suppresses; every other answer nudges.
    # One read, not Test-Path-then-Get-Item, since the two-step races a concurrent prune. Its own
    # catch so a throw here cannot reach the outer catch and swallow the nudge. PSIsContainer
    # because a directory sitting on the marker path reads back with a perfectly fresh timestamp
    # and would otherwise silence the session outright.
    $fresh = $false
    try {
        $existing = Get-Item -LiteralPath $marker -ErrorAction SilentlyContinue
        if ($existing -and -not $existing.PSIsContainer -and
            $existing.LastWriteTime -gt (Get-Date).AddMinutes(-45)) { $fresh = $true }
    } catch { }
    if ($fresh) { exit 0 }

    # Dedup is best-effort, so its failures stop here instead of reaching the outer catch. An
    # unwritable marker store costs a repeated banner; letting it abort costs the nudge entirely.
    try {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        # -Force is the refresh: the marker is empty by design, so there is no content to truncate.
        New-Item -ItemType File -Path $marker -Force | Out-Null
        Get-ChildItem -LiteralPath $markerRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    } catch { }

    # --- the message ---
    # Labelled from the base that matched, so the line names the file as well as the rule and a
    # worktree path reads as its own tree rather than as a sibling of the main one.
    $rel = $full.Substring($base.Length).TrimStart('\', '/')
    $msg = "Markdown authored ($rel) — apply the write-for-agents skill (declare the reader, " +
           "then carve); where facts live is docs/tool-design.md (routing ladder, echoes, lifts)."
    @{
        hookSpecificOutput = @{
            hookEventName     = 'PostToolUse'
            additionalContext = $msg
        }
    } | ConvertTo-Json -Depth 5 -Compress | Write-Output
    exit 0
}
catch { exit 0 }
