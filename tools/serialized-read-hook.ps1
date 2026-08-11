# PostToolUse hook on Read|Grep|Glob. One job: when a read lands on serialized Unity YAML, inject one
# line routing to docs/unity.md §Reading serialized assets and the doors that read the composed scope.
#
# This is a prompt, not a check. The trap it addresses is a negative existence claim ("broken",
# "disabled", "null", "never fires") emitted at artifact scope about behavior that is only decidable
# at composed scope — and claim EMISSION is not machine-detectable. The read is a proxy several turns
# upstream, so this is best-effort context injection; docs/verify.md's rule is what carries the load
# at assertion time. Do not oversell it anywhere as coverage.
# Two holes are structural, not bugs to fix: a read through Bash (`cat`, `rg`) reaches no tool matcher
# at all, and a file already in context is re-reasoned over without any tool call.
#
# Path extraction has three arms because the three tools disagree about where result paths live, and
# one of them hides them (measured against the live payload, not the docs):
#   Read  -> tool_response.file.filePath, absolute.
#   Glob, Grep output_mode=files_with_matches|count -> tool_response.filenames[], cwd-relative.
#   Grep output_mode=content -> filenames is ALWAYS EMPTY and numFiles is 0; the paths exist only as
#     `path:line:` prefixes inside the content string, and a grep already scoped to a single file
#     emits no prefix at all. That last shape is the commonest incident — a repo-wide `Grep "Damp"`
#     whose input names no extension — so an implementation that reads filenames[] alone never fires
#     on the case this hook exists for. Hence the prefix parse plus the tool_input.path fallback.
# The prefix regex is non-greedy from the start of the line, which is what makes an absolute Windows
# path safe: `C:` cannot satisfy `:\d+:`, so the match advances past the drive letter on its own.
# A `-C` context line separates with `-` rather than `:`, hence the second pattern — tried only after
# the colon form fails, because a path segment like `Foo-2-x` satisfies the dash form early and would
# truncate the name. Costs nothing in practice: rg emits every MATCH line in colon form, so a context
# result names its file either way, and a misparse yields silence rather than a wrong route.
#
# Dedupe is per TARGET CLASS, not per session and not per file. A single fire spent on an incidental
# `.asset` read would otherwise leave the real misread — a `.controller` hand-read three turns later —
# uncovered, while per-file dedupe would fire on every hit of a repo-wide grep. The 45-minute expiry
# is prose-hook.ps1's, for its reason: compaction drops injected context but leaves the session id.
# agent_id joins the key because hooks fire inside subagents and a parent's fire would mask theirs;
# it is absent on the main thread, where session_id alone is the scope.
#
# Never block: every path out exits 0, and a marker store that cannot be read or written nudges
# anyway. The worst case of every failure mode here is one missing or one duplicated line of advice.

$ErrorActionPreference = 'Stop'

try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }
    $ev = $raw | ConvertFrom-Json

    $resp = $ev.tool_response
    if (-not $resp) { exit 0 }

    # --- collect candidate paths ---
    $paths = New-Object System.Collections.Generic.List[string]
    if ($resp.file -and $resp.file.filePath) { $paths.Add([string]$resp.file.filePath) }
    if ($resp.filenames) { foreach ($f in $resp.filenames) { if ($f) { $paths.Add([string]$f) } } }
    if ($resp.content -is [string] -and $resp.content) {
        $matched = $false
        foreach ($line in ($resp.content -split "`n")) {
            $m = [regex]::Match($line, '^(?<p>.*?):\d+[:-]')
            if (-not $m.Success) { $m = [regex]::Match($line, '^(?<p>.*?)-\d+-') }
            if ($m.Success) { $paths.Add($m.Groups['p'].Value); $matched = $true }
        }
        if (-not $matched -and $ev.tool_input.path) { $paths.Add([string]$ev.tool_input.path) }
    }
    if ($paths.Count -eq 0) { exit 0 }

    # --- classify into target classes ---
    # A route naming every door would be a false steer: a flat tool list steering a controller-reader
    # at CheckAvatar sends it to a door that cannot read a controller. Bare `.meta` is deliberately
    # not a class — it matches every asset in the project and would fire on noise.
    $routes = [ordered]@{
        asset    = 'Read it with the asset doors instead — `ReportController` for the graph, `CheckAnimator` for a verdict with the binding basis taken from the merge site (`docs/animator.md`).'
        scene    = 'Read the placed avatar with the scene doors instead — `CheckAvatar`, `ReportGimmick`, `AgentInspector` (`docs/unity-tools.md`). Modular Avatar components serialize by script GUID, so a name grep of the YAML finds nothing that is there.'
        importer = 'A humanoid mapping lives only in the ModelImporter''s human description, consistent with nothing else in the project — `CheckHumanoidRig` is what reads it.'
    }
    $hit = [ordered]@{}
    foreach ($p in $paths) {
        $lp = $p.ToLowerInvariant()
        $class = if ($lp.EndsWith('.fbx.meta')) { 'importer' }
                 elseif ($lp.EndsWith('.controller') -or $lp.EndsWith('.anim')) { 'asset' }
                 elseif ($lp.EndsWith('.prefab') -or $lp.EndsWith('.unity') -or $lp.EndsWith('.asset')) { 'scene' }
                 else { $null }
        if ($class) { $hit[$class] = $true }
    }
    if ($hit.Count -eq 0) { exit 0 }

    # --- per-class dedupe ---
    $sid = if ($ev.session_id) { $ev.session_id } else { 'nosession' }
    $scope = if ($ev.agent_id) { "$sid-$($ev.agent_id)" } else { $sid }
    $tempBase = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
    $markerRoot = [System.IO.Path]::Combine($tempBase, 'claude-serialized-read-hook')
    $dir = [System.IO.Path]::Combine($markerRoot, $scope)

    $fire = @()
    foreach ($class in $hit.Keys) {
        $marker = [System.IO.Path]::Combine($dir, $class)
        # Only a marker that is demonstrably a fresh FILE suppresses; every other answer nudges. One
        # read rather than Test-Path-then-Get-Item, so a concurrent prune cannot race the two steps.
        $fresh = $false
        try {
            $existing = Get-Item -LiteralPath $marker -ErrorAction SilentlyContinue
            if ($existing -and -not $existing.PSIsContainer -and
                $existing.LastWriteTime -gt (Get-Date).AddMinutes(-45)) { $fresh = $true }
        } catch { }
        if (-not $fresh) { $fire += $class }
    }
    if ($fire.Count -eq 0) { exit 0 }

    # Best-effort, so its failures stop here: an unwritable marker store costs a repeated line, while
    # letting it abort costs the line entirely.
    try {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        foreach ($class in $fire) {
            New-Item -ItemType File -Path ([System.IO.Path]::Combine($dir, $class)) -Force | Out-Null
        }
        Get-ChildItem -LiteralPath $markerRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    } catch { }

    # --- the message ---
    # A compressed echo of docs/unity.md §Reading serialized assets, which is its canon and is named
    # here so the two cannot drift into separate authorities (docs/tool-design.md §Diagnostics).
    $msg = 'Serialized Unity asset read. These files are partial views of a composed system: ' +
           '`fileID: 0` has benign generators, references complete in-scene and at build, and behavior ' +
           'spans merged controllers, menus, and the importer''s humanoid mapping. So "broken", ' +
           '"disabled", "null" and "never fires" are composed-scope claims — this read can only support ' +
           '"not visible from here". Canon: `docs/unity.md` §Reading serialized assets; the evidence ' +
           'rule is `docs/verify.md`.'
    foreach ($class in $fire) { $msg += ' ' + $routes[$class] }

    @{
        hookSpecificOutput = @{
            hookEventName     = 'PostToolUse'
            additionalContext = $msg
        }
    } | ConvertTo-Json -Depth 5 -Compress | Write-Output
    exit 0
}
catch { exit 0 }
