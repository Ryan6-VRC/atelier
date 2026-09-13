# PreToolUse hook on the write-capable tools. One job: the first time a session is about to write
# inside a Unity venue, dump docs/VENUE.md whole into context, so the rules that bind venue work are
# in front of the agent before the write rather than discovered after it.
#
# Whole file, not a summary, and deliberately: VENUE.md is short, it is the authority, and a
# compressed echo of a rule that BINDS is the failure this hook exists to prevent (docs/tool-design.md
# §Diagnostics). It therefore reads the file at fire time and never restates it here.
#
# Never blocks. Every path out exits 0 with no permission decision, so the write proceeds; the worst
# case of any failure here is a missing or a duplicated dump. A PreToolUse that could deny would make
# a hook bug into a wedged session, and the operator asked for the rules in context, not a gate.
#
# Detecting "inside a venue" has three arms because the tools disagree about whether a path is even
# visible, and the operator named the hard part up front: an agent has many ways to modify a file.
#   Write|Edit|NotebookEdit -> tool_input.file_path / .notebook_path, a concrete path. Walk its
#     ancestors for ProjectSettings/ProjectVersion.txt — that marker IS the definition of a Unity
#     project root, it needs no list of venues, it holds for a venue whose Editor is closed, and it
#     names no project in tracked code (CLAUDE.local.md's venues must never be named here).
#   Bash|PowerShell -> an arbitrary command string with no path field at all. There is no honest way
#     to parse every shape (`sed -i`, a heredoc, a python one-liner, a cp into a venue), so this arm
#     substring-matches the command against known venue roots instead. Roots come from the live
#     ~/.unity-mcp heartbeats (the same source unity-instances-hook.sh reads, so nothing is hardcoded)
#     plus a shallow scan of the workspace for ProjectVersion.txt, matched in both slash forms.
#     This is a net, not a fence: a Bash write through a path relative to a venue cwd is invisible to
#     it and always will be. Do not describe this hook anywhere as coverage.
#   mcp__UnityMCP__* mutators -> no path test at all. Every one of them addresses a venue by
#     construction, so reaching for one IS the trigger. The read-only Unity doors are not matched:
#     they are how an agent observes before changing (CLAUDE.md rule 1) and must stay unobstructed.
#
# Dedupe is once per session scope, per the operator's ask. agent_id joins the key because hooks fire
# inside subagents and a parent's fire would leave a subagent — the thing actually doing venue work —
# with nothing; it is absent on the main thread, where session_id alone is the scope.

$ErrorActionPreference = 'Stop'
# VENUE.md is dumped verbatim and contains em-dashes; without this pwsh's default stdout encoding
# mangles them on the way into the JSON, so the agent reads a subtly different document than the file.
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }
    $ev = $raw | ConvertFrom-Json

    $tool = [string]$ev.tool_name
    if (-not $tool) { exit 0 }
    $ti = $ev.tool_input

    # --- is this call about to write inside a venue? ---
    $hitVenue = $false

    if ($tool -like 'mcp__UnityMCP__*') {
        $mutators = @('execute_code', 'execute_menu_item', 'manage_asset', 'manage_gameobject',
                      'manage_scene', 'manage_editor', 'manage_packages', 'refresh_unity')
        $leaf = $tool -replace '^mcp__UnityMCP__', ''
        if ($mutators -contains $leaf) { $hitVenue = $true }
    }
    elseif ($tool -eq 'Bash' -or $tool -eq 'PowerShell') {
        $cmd = [string]$ti.command
        if ($cmd) {
            $roots = New-Object System.Collections.Generic.List[string]
            try {
                Get-ChildItem -Path (Join-Path $HOME '.unity-mcp') -Filter 'unity-mcp-status-*.json' `
                    -ErrorAction SilentlyContinue | ForEach-Object {
                    $p = (Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json).project_path
                    if ($p) { $roots.Add(($p -replace '/Assets$', '')) }
                }
            } catch { }
            try {
                $proj = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }
                Get-ChildItem -LiteralPath $proj -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                    if (Test-Path -LiteralPath (Join-Path $_.FullName 'ProjectSettings/ProjectVersion.txt')) {
                        $roots.Add($_.FullName)
                    }
                }
            } catch { }
            $hay = $cmd.ToLowerInvariant() -replace '\\', '/'
            foreach ($r in $roots) {
                $needle = ($r -replace '\\', '/').TrimEnd('/').ToLowerInvariant()
                if (-not $needle) { continue }
                if ($hay.Contains($needle)) { $hitVenue = $true; break }
            }
        }
    }
    else {
        $path = if ($ti.file_path) { [string]$ti.file_path }
                elseif ($ti.notebook_path) { [string]$ti.notebook_path }
                else { $null }
        if ($path) {
            try {
                $dir = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($path))
                while ($dir) {
                    if (Test-Path -LiteralPath (Join-Path $dir 'ProjectSettings/ProjectVersion.txt')) {
                        $hitVenue = $true; break
                    }
                    $parent = [System.IO.Path]::GetDirectoryName($dir)
                    if ($parent -eq $dir) { break }
                    $dir = $parent
                }
            } catch { }
        }
    }
    if (-not $hitVenue) { exit 0 }

    # --- once per session scope ---
    $sid = if ($ev.session_id) { $ev.session_id } else { 'nosession' }
    $scope = if ($ev.agent_id) { "$sid-$($ev.agent_id)" } else { $sid }
    $tempBase = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
    $markerRoot = [System.IO.Path]::Combine($tempBase, 'claude-venue-write-hook')
    $marker = [System.IO.Path]::Combine($markerRoot, "$scope.marker")
    try {
        if (Test-Path -LiteralPath $marker -PathType Leaf) { exit 0 }
    } catch { }

    # --- the dump ---
    $projDir = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }
    $venueDoc = [System.IO.Path]::Combine($projDir, 'docs', 'VENUE.md')
    $body = $null
    try { $body = Get-Content -LiteralPath $venueDoc -Raw -ErrorAction Stop } catch { }
    # A missing VENUE.md still nudges: the route is worth more than silence, and silence here is
    # indistinguishable from "no rules apply".
    $msg = if ($body) {
        "You are about to write inside a Unity venue. ``docs/VENUE.md`` binds; it is reproduced whole " +
        "below so you need not fetch it. Filing and tree structure are ``docs/LAYOUT.md``'s." +
        "`n`n" + $body
    }
    else {
        "You are about to write inside a Unity venue. Read ``docs/VENUE.md`` (it binds) and " +
        "``docs/LAYOUT.md`` (filing) before this write — this hook could not read VENUE.md at $venueDoc."
    }

    try {
        New-Item -ItemType Directory -Force -Path $markerRoot | Out-Null
        New-Item -ItemType File -Path $marker -Force | Out-Null
        Get-ChildItem -LiteralPath $markerRoot -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } |
            Remove-Item -Force -ErrorAction SilentlyContinue
    }
    catch { }

    @{
        hookSpecificOutput = @{
            hookEventName     = 'PreToolUse'
            additionalContext = $msg
        }
    } | ConvertTo-Json -Depth 5 -Compress | Write-Output
    exit 0
}
catch { exit 0 }
