# PreToolUse hook on the write-capable tools. One job: the first time a session touches a Unity venue,
# dump docs/VENUE.md whole into context, so the rules that bind venue work are in the session rather
# than left to be discovered.
#
# WHAT IT CANNOT DO, stated first because the obvious reading of "PreToolUse" is wrong: this does not
# get the rules in before the write it fires on. The hook emits no permissionDecision, so the call
# proceeds, and additionalContext is delivered beside the tool RESULT — read on the next model
# request, after the write landed. Measured against the shipped binary, not inferred. So the honest
# contract is: the first venue touch is uncovered, and writes 2..N happen with the rules in context.
# Buying the first one back means denying it and allowing the retry, which is a gate; the operator
# asked for the rules in context, not a gate. If that trade is ever reopened, reopen it here.
#
# Whole file, not a summary, and deliberately: VENUE.md is short, it is the authority, and the
# operator asked for the whole thing. (docs/tool-design.md §Duplication would in fact PERMIT a
# compressed echo that names its canonical home — this is a stricter choice than the rule requires,
# not an application of it.) The file is read at fire time and never restated here.
#
# Never blocks. Every path out exits 0 with no permission decision, so the write proceeds; the worst
# case of any failure here is a missing or a duplicated dump.
#
# Detecting "inside a venue" has three arms, and the operator named the hard part up front: an agent
# has many ways to modify a file.
#   Write|Edit|NotebookEdit -> tool_input.file_path / .notebook_path, a concrete path. Walk its
#     ancestors for ProjectSettings/ProjectVersion.txt — that marker IS the definition of a Unity
#     project root, it needs no list of venues, it holds for a venue whose Editor is closed, and it
#     names no project in tracked code (CLAUDE.local.md's venues must never be named here).
#   Bash|PowerShell -> an arbitrary command string with no path field at all. There is no honest way
#     to parse every shape (`sed -i`, a heredoc, a python one-liner, a cp into a venue), so this arm
#     matches the command against known venue roots instead, in absolute and workspace-relative form
#     and in both slash flavours. Still a net, not a fence: a write through a path relative to a VENUE
#     cwd is invisible to it and always will be. Do not describe this hook anywhere as coverage.
#   mcp__UnityMCP__* mutators -> no path test at all; they address a venue by construction.
#     `execute_code` is on that list and that is not a clean call: EVERY agent-tools / avatar-tools
#     door is invoked through it (docs/unity.md, docs/unity-tools.md), so a pure read like CheckAvatar
#     fires this hook too. The leaf tool name carries no information about mutation and the C# body is
#     not something a hook should be parsing, so the false-positive side was chosen over missing the
#     main mutation path. Do not write "read-only doors stay silent" — only the non-kit read tools do.
#
# Dedupe is once per session scope, per the operator's ask, with serialized-read-hook.ps1's 45-minute
# expiry and for its reason: compaction drops injected context but leaves the session id, so a
# never-expiring marker would leave a long venue session running permanently without the rules.
# agent_id joins the key because hooks fire inside subagents and a parent's fire would leave a
# subagent — the thing actually doing venue work — with nothing.
#
# Cost is why the marker check comes FIRST, before any detection. This matcher covers Bash, the
# highest-frequency tool class there is: measured across 309 recorded sessions on this machine the
# median session makes 83 matched calls (mean 92, max 338), against a median 9 for the Read|Grep|Glob
# hook next door. Hoisting the marker and caching the roots took a full pass from ~285 ms to ~257 ms
# — and that small win is the finding: the cost is the pwsh SPAWN, not the work, so no amount of
# further optimisation inside this file matters. ~21 s per median session stands, against the ~3.5 s
# serialized-read-hook.ps1 budgets for itself in a comment naming the deciding factor: "N per session,
# not the spawn, is what would reopen this." N here is ~9x larger. The only real lever is dropping
# Bash|PowerShell from the matcher, which costs the `cp into a venue` net entirely — an operator
# trade, unmade and deliberately left visible here rather than decided quietly.

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

    # --- already fired for this scope? cheapest possible exit, so it comes before detection ---
    $sid = if ($ev.session_id) { $ev.session_id } else { 'nosession' }
    $scope = if ($ev.agent_id) { "$sid-$($ev.agent_id)" } else { $sid }
    $tempBase = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
    $markerRoot = [System.IO.Path]::Combine($tempBase, 'claude-venue-write-hook')
    $marker = [System.IO.Path]::Combine($markerRoot, "$scope.marker")
    # Only a marker that is demonstrably a fresh FILE suppresses; every other answer dumps again.
    try {
        $existing = Get-Item -LiteralPath $marker -ErrorAction SilentlyContinue
        if ($existing -and -not $existing.PSIsContainer -and
            $existing.LastWriteTime -gt (Get-Date).AddMinutes(-45)) { exit 0 }
    } catch { }

    # --- is this call touching a venue? ---
    $hitVenue = $false

    if ($tool -like 'mcp__UnityMCP__*') {
        # manage_camera is on this list because it writes PNGs and their .meta into the venue's
        # Assets/ — vrc-mcp-proxy's transform records real undisclosed litter from exactly that.
        $mutators = @('execute_code', 'execute_menu_item', 'manage_asset', 'manage_gameobject',
                      'manage_scene', 'manage_editor', 'manage_packages', 'manage_camera',
                      'refresh_unity')
        $leaf = $tool -replace '^mcp__UnityMCP__', ''
        if ($mutators -contains $leaf) { $hitVenue = $true }
    }
    elseif ($tool -eq 'Bash' -or $tool -eq 'PowerShell') {
        $cmd = [string]$ti.command
        if ($cmd) {
            # Roots are machine state, not session state, so the cache is shared and time-bounded.
            $cacheFile = [System.IO.Path]::Combine($markerRoot, 'roots.cache')
            $roots = $null
            try {
                $c = Get-Item -LiteralPath $cacheFile -ErrorAction SilentlyContinue
                if ($c -and -not $c.PSIsContainer -and $c.LastWriteTime -gt (Get-Date).AddMinutes(-10)) {
                    $roots = @(Get-Content -LiteralPath $cacheFile -ErrorAction Stop |
                               Where-Object { $_ })
                }
            } catch { $roots = $null }

            if ($null -eq $roots) {
                $found = New-Object System.Collections.Generic.List[string]
                # Live Editors, including venues outside the workspace. Per-file try/catch: a Unity
                # crash mid-write leaves a truncated heartbeat, and unity-instances-hook.sh's contract
                # for the same files is that a bad entry drops itself, never the whole table.
                Get-ChildItem -Path (Join-Path $HOME '.unity-mcp') -Filter 'unity-mcp-status-*.json' `
                    -ErrorAction SilentlyContinue | ForEach-Object {
                    try {
                        $j = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction Stop | ConvertFrom-Json
                        # ConvertFrom-Json already returns a DateTime with Kind=Utc, so the obvious
                        # [datetime]::Parse($j.last_heartbeat) re-reads the UTC wall-clock as LOCAL —
                        # measured. West of UTC that makes every stale heartbeat look fresh; east of
                        # it, every live heartbeat looks stale and this whole arm goes dark. Compare
                        # in UTC on both sides, and assume UTC for a stamp that carries no zone.
                        $hb = [datetime]$j.last_heartbeat
                        if ($hb.Kind -eq [System.DateTimeKind]::Unspecified) {
                            $hb = [datetime]::SpecifyKind($hb, [System.DateTimeKind]::Utc)
                        }
                        if ($j.project_path -and $hb.ToUniversalTime() -gt [datetime]::UtcNow.AddSeconds(-300)) {
                            $found.Add(($j.project_path -replace '[/\\]Assets$', ''))
                        }
                    } catch { }
                }
                # Venues with no Editor running. docs/tool-design.md: anything reading the untracked
                # working venues resolves the MAIN CHECKOUT first — a linked worktree carries only
                # tracked files, so $CLAUDE_PROJECT_DIR here would scan a tree with no venues in it.
                $ws = $null
                try {
                    . (Join-Path $PSScriptRoot 'test-venue-common.ps1')
                    $ws = Get-AtelierMainCheckout
                } catch { }
                # CLAUDE_PROJECT_DIR is scanned too, and only as well: it is the right answer when the
                # session is not in a worktree and the only answer a test can control, but on its own
                # it is the bug the rule above exists to prevent.
                $scanDirs = @($ws, $env:CLAUDE_PROJECT_DIR, (Get-Location).Path) |
                            Where-Object { $_ } | Sort-Object -Unique
                foreach ($d in $scanDirs) {
                    try {
                        Get-ChildItem -LiteralPath $d -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                            if (Test-Path -LiteralPath (Join-Path $_.FullName 'ProjectSettings/ProjectVersion.txt')) {
                                $found.Add($_.FullName)
                            }
                        }
                    } catch { }
                }
                $roots = @($found | Sort-Object -Unique)
                try {
                    New-Item -ItemType Directory -Force -Path $markerRoot | Out-Null
                    Set-Content -LiteralPath $cacheFile -Value $roots -ErrorAction Stop
                } catch { }
            }

            $hay = $cmd.ToLowerInvariant() -replace '\\', '/'
            foreach ($r in $roots) {
                $abs = ($r -replace '\\', '/').TrimEnd('/').ToLowerInvariant()
                if (-not $abs) { continue }
                if ($hay.Contains($abs)) { $hitVenue = $true; break }
                # `cp a.png AvatarProject/Assets/x.png` from the workspace root is the ordinary shape
                # and holds no absolute path. Match the bare leaf, but only where a path separator
                # follows, so prose mentioning the name does not fire. A false positive costs one
                # extra dump, which is the side of this trade the never-block design already takes.
                $leafName = [regex]::Escape(($abs -split '/')[-1])
                if ($leafName -and $hay -match "(^|[\s'`"=(:;&|/])$leafName/") { $hitVenue = $true; break }
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

    # --- the dump ---
    $projDir = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }
    $venueDoc = [System.IO.Path]::Combine($projDir, 'docs', 'VENUE.md')
    $body = $null
    try { $body = Get-Content -LiteralPath $venueDoc -Raw -ErrorAction Stop } catch { }
    # A missing VENUE.md still nudges: the route is worth more than silence, and silence here is
    # indistinguishable from "no rules apply".
    $msg = if ($body) {
        "You are touching a Unity venue. ``docs/VENUE.md`` binds; it is reproduced whole below so you " +
        "need not fetch it. Filing and tree structure are ``docs/LAYOUT.md``'s." +
        "`n`n" + $body
    }
    else {
        "You are touching a Unity venue. Read ``docs/VENUE.md`` (it binds) and ``docs/LAYOUT.md`` " +
        "(filing) — this hook could not read VENUE.md at $venueDoc."
    }

    try {
        New-Item -ItemType Directory -Force -Path $markerRoot | Out-Null
        New-Item -ItemType File -Path $marker -Force | Out-Null
        Get-ChildItem -LiteralPath $markerRoot -File -Filter '*.marker' -ErrorAction SilentlyContinue |
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
