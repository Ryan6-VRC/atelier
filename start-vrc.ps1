#Requires -Version 7
<#
.SYNOPSIS
    One-command startup for the AI-assisted VRChat workflow: brings up Unity + Blender
    (with their MCP bridges live), then hands the window off to Claude.

    Idempotent — re-running skips whatever is already healthy, so it doubles as a doctor.

.EXAMPLE
    .\start-vrc.ps1 AvatarProject
.EXAMPLE
    .\start-vrc.ps1 -Path ..\Projects\AnotherAvatarProject
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)] [string] $ProjectName,
    [string] $Path,
    [int] $TimeoutSec = 120
)

$ErrorActionPreference = 'Stop'
$WorkspaceRoot = Split-Path -Parent $PSCommandPath
$BlenderPort = 9876
$AppsDir     = Join-Path $env:USERPROFILE 'Apps'

# ---------------------------------------------------------------- helpers ----
function Write-Status($Symbol, $Color, $Text) { Write-Host " $Symbol " -ForegroundColor $Color -NoNewline; Write-Host $Text }
function Ok($t)   { Write-Status '+' Green   $t }
function Work($t) { Write-Status '>' Cyan    $t }
function Warn($t) { Write-Status '!' Yellow  $t }
function Fail($t) { Write-Status 'x' Red     $t }

function Test-Port([int]$Port) {
    $c = [System.Net.Sockets.TcpClient]::new()
    try { $c.Connect('127.0.0.1', $Port); $true } catch { $false } finally { $c.Dispose() }
}

# The Unity stdio bridge auto-starts on a cold Editor open and heartbeats into
# ~/.unity-mcp/unity-mcp-status-<hash>.json (port from 6400). Match by project path (hash-agnostic); a
# fresh, non-reloading heartbeat means the bridge is up and ready to serve — regardless of what the
# Editor's MCP window shows ("No Session" there is a cosmetic desync, not a down bridge).
function Test-UnityBridge([string]$ProjPath) {
    $dir = Join-Path $env:USERPROFILE '.unity-mcp'
    if (-not (Test-Path $dir)) { return $false }
    $assets = ((Join-Path $ProjPath 'Assets') -replace '\\', '/').TrimEnd('/')
    foreach ($f in Get-ChildItem $dir -Filter 'unity-mcp-status-*.json' -ErrorAction SilentlyContinue) {
        try { $s = Get-Content $f.FullName -Raw | ConvertFrom-Json } catch { continue }
        if ((("$($s.project_path)") -replace '\\', '/').TrimEnd('/') -ieq $assets) {
            try { $age = ([datetimeoffset]::UtcNow - [datetimeoffset]::Parse($s.last_heartbeat)).TotalSeconds } catch { continue }
            if ($age -lt 20 -and -not [bool]$s.reloading) { return $true }
        }
    }
    return $false
}

# UnityLockfile is held with an exclusive lock while the Editor has the project open.
function Test-ProjectOpen([string]$ProjPath) {
    $lf = Join-Path $ProjPath 'Temp\UnityLockfile'
    if (-not (Test-Path $lf)) { return $false }
    try { ([System.IO.File]::Open($lf, 'Open', 'Read', 'None')).Dispose(); $false } catch { $true }
}

# Roslyn DLLs enable modern C# in the MCP execute_code tool; absent, it falls back to a C# 6 compiler.
# Installed per Editor into Assets/Plugins/Roslyn (gitignored). Presence of the CSharp DLL is the proxy.
function Test-RoslynInstalled([string]$ProjPath) {
    Test-Path (Join-Path $ProjPath 'Assets\Plugins\Roslyn\Microsoft.CodeAnalysis.CSharp.dll')
}

function Get-ProjectEditorVersion([string]$ProjPath) {
    $line = Get-Content (Join-Path $ProjPath 'ProjectSettings\ProjectVersion.txt') |
        Where-Object { $_ -match '^m_EditorVersion:' } | Select-Object -First 1
    ($line -split ':\s*', 2)[1].Trim()
}

function Find-UnityEditor([string]$Version) {
    # Hub registry first (authoritative; handles custom install dirs), then the default path.
    $reg = Join-Path $env:APPDATA 'UnityHub\editors-v2.json'
    if (Test-Path $reg) {
        $hit = (Get-Content $reg -Raw | ConvertFrom-Json).data | Where-Object version -eq $Version | Select-Object -First 1
        if ($hit) { $loc = @($hit.location)[0]; if ($loc -and (Test-Path $loc)) { return $loc } }
    }
    $def = "C:\Program Files\Unity\Hub\Editor\$Version\Editor\Unity.exe"
    if (Test-Path $def) { return $def }
    return $null
}

function Find-Blender {
    # Newest portable under ~\Apps\blender-<ver>-windows-x64 (version-agnostic; survives the 5.2 move).
    # Use blender-launcher.exe, not blender.exe: the launcher starts Blender windowed with no debug
    # console — one less terminal window. Tradeoff: the suppressed console is where the MCP extension
    # prints startup errors, and the launcher exits immediately so Start-Process can't track the real
    # PID. We accept both (we health-check the :9876 port, not the process).
    Get-ChildItem $AppsDir -Directory -Filter 'blender-*-windows-x64' -ErrorAction SilentlyContinue |
        Sort-Object { [version](($_.Name -replace '^blender-', '') -replace '-windows-x64$', '') } -Descending |
        ForEach-Object { Join-Path $_.FullName 'blender-launcher.exe' } |
        Where-Object { Test-Path $_ } | Select-Object -First 1
}

function Find-VrcGet {
    $g = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\anatawa12.vrc-get_*\vrc-get.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($g) { return $g.FullName }
    $cmd = Get-Command vrc-get -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Get-WorkspaceProjects {
    Get-ChildItem $WorkspaceRoot -Directory | Where-Object {
        Test-Path (Join-Path $_.FullName 'ProjectSettings\ProjectVersion.txt')
    }
}

# ------------------------------------------------------- 1. resolve project ----
if ($Path) {
    $projPath = (Resolve-Path $Path).Path
    if (-not (Test-Path (Join-Path $projPath 'ProjectSettings\ProjectVersion.txt'))) {
        Fail "Not a Unity project (no ProjectSettings\ProjectVersion.txt): $projPath"; exit 1
    }
}
else {
    $projects = Get-WorkspaceProjects
    if (-not $ProjectName) {
        Write-Host "Usage: start-vrc <ProjectName>  (or -Path <dir>)"
        Write-Host "Unity projects in this workspace:"
        $projects | ForEach-Object { Write-Host "  - $($_.Name)" }
        exit 0
    }
    $match = @($projects | Where-Object Name -ieq $ProjectName)
    if ($match.Count -eq 0) {
        Fail "No project named '$ProjectName'. Available:"
        $projects | ForEach-Object { Write-Host "  - $($_.Name)" }
        exit 1
    }
    if ($match.Count -gt 1) { Fail "Ambiguous: '$ProjectName' matches $($match.Count) folders."; exit 1 }
    $projPath = $match[0].FullName
}

$projName = Split-Path $projPath -Leaf
$version  = Get-ProjectEditorVersion $projPath
Write-Host ""
Work "Project: $projName  (Unity $version)"

# ------------------------------------------------- 2/3. ensure Unity + MCP ----
# Transport is stdio: each Editor hosts its own bridge and the client pins route by Name@hash identity,
# so projects coexist (no shared :8200 — that single-port conflict was an http-only limitation). Ports
# still default to 6400, so concurrent editors rely on distinct saved ports (e.g. project A 6400, project B 6401).
$mineOpen = Test-ProjectOpen $projPath

if ($mineOpen) {
    Ok "Unity: '$projName' already open"
}
else {
    $vg = Find-VrcGet
    if ($vg) { Work "Restoring packages (vrc-get resolve)…"; & $vg resolve -p $projPath | Out-Null }
    else { Warn "vrc-get not found — skipping package restore." }

    $editor = Find-UnityEditor $version
    if (-not $editor) { Fail "No Unity $version found (Hub registry or default path). Install it via Unity Hub."; exit 1 }
    Work "Launching Unity $version…"
    Start-Process $editor -ArgumentList '-projectPath', $projPath
}

# ----------------------------------------------------------- 4. ensure Blender ----
if (Test-Port $BlenderPort) {
    Ok "Blender MCP: already up"
}
else {
    $blender = Find-Blender
    if (-not $blender) { Fail "No portable Blender found under $AppsDir (blender-*-windows-x64)."; exit 1 }
    Work "Launching Blender ($((Split-Path (Split-Path $blender -Parent) -Leaf)))…"
    Start-Process $blender
}

# --------------------------------------------------------- 5. wait for ready ----
Write-Host ""
Work "Waiting for MCP bridges (timeout ${TimeoutSec}s)…"
$deadline = (Get-Date).AddSeconds($TimeoutSec)
$unityReady = $false; $blenderReady = $false
while ((Get-Date) -lt $deadline -and -not ($unityReady -and $blenderReady)) {
    if (-not $unityReady)   { $unityReady   = Test-UnityBridge $projPath }
    if (-not $blenderReady) { $blenderReady = Test-Port $BlenderPort }
    if ($unityReady -and $blenderReady) { break }
    Start-Sleep -Seconds 2
}

# ------------------------------------------------------- 6. report + hand off ----
Write-Host ""
if ($unityReady)   { Ok   "Unity MCP    stdio bridge ready" }   else { Fail "Unity MCP    stdio bridge NOT ready (Editor still loading, transport not stdio, or bridge down)" }
if (Test-RoslynInstalled $projPath) { Ok "Roslyn       execute_code uses modern C#" } else { Warn "Roslyn       not installed — execute_code falls back to C# 6 (MCP for Unity window -> Install; see bootstrap.md)" }
if ($blenderReady) { Ok   "Blender MCP  :$BlenderPort  ready" } else { Fail "Blender MCP  :$BlenderPort  NOT responding (check the 'mcp' extension is enabled + Allow Online Access)" }
Write-Host ""

if ($unityReady -and $blenderReady) { Ok "All services healthy." }
else { Warn "Some services aren't up — Claude may not see them. Continue anyway, or Ctrl+C to abort." }

Write-Host "Press any key to launch Claude (Ctrl+C to cancel)…" -ForegroundColor Cyan
[void][System.Console]::ReadKey($true)

Set-Location $WorkspaceRoot
claude --name VRChat
