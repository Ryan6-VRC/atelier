<#
  Throwaway batchmode EditMode test runner. Launches a separate Unity process (crash-tolerant:
  a crash kills this process, never a live editor) against TestEditor, and classifies the outcome.
  Default target is TestEditor; the SDK-parity guard blocks a run when TestEditor's VRChat SDK has
  drifted from AvatarProject's (re-sync with tools/setup-test-editor.ps1 -Sync).

  The OUTCOME= stdout line is the authoritative contract; exit codes mirror it:
    0 COMPLETED (0 failures)  1 CRASH  2 UNKNOWN  3 TIMEOUT
    4 SDK_DRIFT  5 RUN_ERROR  6 COMPLETED (with test failures)  7 COMPILE_ERROR
#>
param(
  # TestEditor is beside this script's repo root → worktree-local by default (matches the generator).
  [string]$Project    = (Join-Path $PSScriptRoot "../TestEditor"),
  # The Unity project this venue's packages are kept in step with — the version baseline for the parity
  # guard below, NOT an avatar. Must match whatever was passed to setup-test-editor.ps1 -SourceProject.
  # Empty means "the AvatarProject inside the main checkout"; it is untracked, so a worktree's own root
  # does not carry it and script-relative cannot reach it. Resolved below.
  [string]$SourceProject = "",
  [string]$Assemblies = "Ryan6VRC.AvatarTools.Tests;Ryan6VRC.AgentTools.Tests",
  [string]$Filter     = "",
  [Parameter(Mandatory=$true)][string]$Tag,
  [int]$TimeoutSec    = 540,
  # Unity.exe for the run. Empty resolves it from $Project's own pinned version — unity-editor.ps1
  # owns the ladder. Pass one to override.
  [string]$Editor     = ""
)
. (Join-Path $PSScriptRoot "test-venue-common.ps1")
. (Join-Path $PSScriptRoot "unity-editor.ps1")
# This script does not set $ErrorActionPreference, so a dot-source that failed above (file missing,
# renamed, unreadable) only WROTE an error and carried on — measured on PowerShell 7. The package lists
# would then be $null, every `foreach ($pkg in $null)` would iterate zero times, and the community tier's
# absence-IS-fatal check would be skipped in silence: a green run against a venue whose test assemblies
# cannot compile. Inline literals could not be empty; a shared file can, so assert it loaded.
if (-not $TestVenueCommunity -or -not $TestVenueFixtures -or -not $TestVenueSdk) {
  Write-Host "OUTCOME=RUN_ERROR test-venue-common.ps1 did not load (package lists empty) — the venue guards cannot run"
  exit 5
}
# Same reasoning for the second dot-source: a missing Resolve-UnityEditor would otherwise surface as a
# CommandNotFoundException inside the resolve try/catch below, reported as if the EDITOR were missing.
if (-not (Get-Command Resolve-UnityEditor -ErrorAction SilentlyContinue)) {
  Write-Host "OUTCOME=RUN_ERROR unity-editor.ps1 did not load (Resolve-UnityEditor undefined) — cannot resolve the editor"
  exit 5
}
if ([string]::IsNullOrWhiteSpace($SourceProject)) {
  try { $SourceProject = Resolve-AtelierChild "AvatarProject" "SourceProject" }
  catch { Write-Host "OUTCOME=RUN_ERROR $($_.Exception.Message)"; exit 5 }
}
# Run-output goes to a disposable sibling of TestEditor, never into tracked tooling: gitignored
# wholesale, worktree-local, and safe to delete at any time. Pruned at 30 days because nothing
# reads an old run — output accrues one file per -Tag, so it grows with wave count, not runs.
$out = Join-Path $PSScriptRoot "../test-output"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$out = (Resolve-Path $out).Path
Get-ChildItem $out -File -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item -Force -ErrorAction SilentlyContinue

function Get-SdkVersion($proj, $pkg) {
  $pj = Join-Path $proj "Packages/$pkg/package.json"
  if (-not (Test-Path $pj)) { return $null }
  return (Get-Content $pj -Raw | ConvertFrom-Json).version
}

# Stage to a temp sibling then swap, so an interrupted or blocked copy can never leave a
# version-matching-but-partial $dst that a version check would then skip repairing. The outgoing copy is
# moved aside rather than deleted first: a failed Rename-Item would otherwise leave the venue with NO copy,
# which for a fixture breaks the tier's promise never to remove one it already had.
#
# -Soft is for the fixture tier: a copy hiccup on an OPTIONAL package (locked file, AV scan, open handle)
# must not take down a 638-case suite. Absence is soft, so a failed refresh of it has to be soft too — the
# venue keeps whatever it had and the affected case self-Ignores, named in the OUTCOME block.
function Copy-PackageIn($pkg, [switch]$Soft) {
  $src = Join-Path $SourceProject "Packages/$pkg"; $dst = Join-Path $Project "Packages/$pkg"
  $tmp = "$dst.tmp"; $old = "$dst.old"
  try {
    foreach ($stale in @($tmp, $old)) { if (Test-Path $stale) { Remove-Item -Recurse -Force $stale -ErrorAction Stop } }
    Copy-Item -Recurse $src $tmp -ErrorAction Stop
    if (Test-Path $dst) { Rename-Item $dst (Split-Path $old -Leaf) -ErrorAction Stop }
    Rename-Item $tmp (Split-Path $dst -Leaf) -ErrorAction Stop
    if (Test-Path $old) { Remove-Item -Recurse -Force $old -ErrorAction SilentlyContinue }
  } catch {
    # Restore the copy we moved aside before reporting, so a failure mid-swap is not also a removal.
    if (-not (Test-Path $dst) -and (Test-Path $old)) { Rename-Item $old (Split-Path $dst -Leaf) -ErrorAction SilentlyContinue }
    if ($Soft) {
      Write-Host "[runner] fixture $pkg sync failed: $($_.Exception.Message) — proceeding on the venue's existing copy"
      return
    }
    Write-Host "OUTCOME=RUN_ERROR sync $pkg failed: $($_.Exception.Message)"; exit 5
  }
}

# --- Editor-version parity (hard block) --- setup-test-editor.ps1 copies ProjectSettings wholesale from
# $SourceProject, so the two versions agree the day the venue is provisioned and can only diverge if the
# source is upgraded afterwards. That divergence matters more than a package drift: the editor is resolved
# from $Project below, so a stale venue would be tested by a stale editor against current packages, and
# pointing the NEW editor at it instead would silently upgrade the project in batchmode. Same remedy as an
# SDK drift, so it reuses that outcome token rather than inventing an eighth exit code.
# The parse itself is unity-editor.ps1's (dot-sourced above) — re-deriving it here would be the
# same duplication this PR removed from gate.ps1, two lines after centralising it.
$sv = Get-UnityProjectVersion $SourceProject
$tv = Get-UnityProjectVersion $Project
# The SOURCE side must be readable. Tolerating $null would skip the guard in silence exactly when the
# baseline is broken, and a check that could not run is not a check that passed (CLAUDE.md rule 7) —
# this file already refuses loudly for that class of defect on the source's packages below.
if ($null -eq $sv) {
  Write-Host "OUTCOME=RUN_ERROR $SourceProject has no readable ProjectSettings/ProjectVersion.txt — is it a Unity project?"
  exit 5
}
# $tv IS allowed to be null: an un-provisioned venue legitimately has no ProjectVersion.txt, and the
# package guards below already name that case with its remedy.
if ($null -ne $tv -and $sv -ne $tv) {
  Write-Host "OUTCOME=SDK_DRIFT m_EditorVersion source=$sv TestEditor=$tv — re-sync: tools/setup-test-editor.ps1 -Sync"
  exit 4
}

# --- SDK parity guard (hard block) --- SDK trio is VRChat-pinned; a drift is a real problem.
foreach ($pkg in @("com.vrchat.base", "com.vrchat.avatars", "com.vrchat.core.bootstrap")) {
  $a = Get-SdkVersion $SourceProject $pkg
  $t = Get-SdkVersion $Project $pkg
  if ($a -ne $t) {
    Write-Host "OUTCOME=SDK_DRIFT $pkg source=$a TestEditor=$t — re-sync: tools/setup-test-editor.ps1 -Sync"
    exit 4
  }
}
# --- Community packages (auto-sync, don't block) --- these bump on ALCOM's cadence; a hard block
# would train reflexive re-sync. Re-copy on mismatch so TestEditor always tests current. Absence IS
# fatal here: the test assemblies compile against these types, so the venue is broken. The list is
# shared with the provisioner (test-venue-common.ps1) — the two must agree, and a copy here drifted.
foreach ($pkg in $TestVenueCommunity) {
  $a = Get-SdkVersion $SourceProject $pkg
  $t = Get-SdkVersion $Project $pkg
  if ($null -eq $a) { Write-Host "OUTCOME=RUN_ERROR $SourceProject missing $pkg — run 'vrc-get resolve' there"; exit 5 }
  if ($a -ne $t) {
    Write-Host "[runner] auto-sync $pkg  source=$a TestEditor=$t"
    Copy-PackageIn $pkg
    if ((Get-SdkVersion $Project $pkg) -ne $a) { Write-Host "OUTCOME=RUN_ERROR $pkg post-sync version mismatch"; exit 5 }
  }
}
# --- Fixture packages (soft) --- a test READS an asset out of these rather than compiling against their
# types, so absence degrades ONE case instead of breaking the venue: that case self-Ignores and the skip
# is named in the OUTCOME block below. Never fatal — a single non-redistributable vendor package must not
# be able to stop the whole suite — and never DELETES a copy this venue already has, so a venue
# provisioned from a project carrying the fixture survives a later run whose $SourceProject does not.
foreach ($pkg in $TestVenueFixtures) {
  $a = Get-SdkVersion $SourceProject $pkg
  $t = Get-SdkVersion $Project $pkg
  if ($null -eq $a) {
    if ($null -eq $t) { Write-Host "[runner] fixture $pkg absent both sides — its cases self-Ignore" }
    else { Write-Host "[runner] fixture $pkg absent from source — keeping this venue's copy ($t)" }
    continue
  }
  if ($a -ne $t) { Write-Host "[runner] fixture sync $pkg  source=$a TestEditor=$t"; Copy-PackageIn $pkg -Soft }
}

# Resolved here, AFTER the venue guards: an un-provisioned TestEditor has no ProjectVersion.txt, and
# resolving earlier would answer that with "cannot find the editor" instead of the parity guards'
# accurate "re-sync the venue" — a refusal naming a fix that cannot work.
if ([string]::IsNullOrWhiteSpace($Editor)) {
  try { $Editor = Resolve-UnityEditor $Project }
  catch { Write-Host "OUTCOME=RUN_ERROR $($_.Exception.Message)"; exit 5 }
} elseif (-not (Test-Path -LiteralPath $Editor)) {
  Write-Host "OUTCOME=RUN_ERROR -Editor '$Editor' does not exist — pass a path to Unity.exe, or omit -Editor to resolve it from $Project"
  exit 5
}

function Invoke-Run([string]$tag) {
  $xml = Join-Path $out "results-$tag.xml"
  $log = Join-Path $out "run-$tag.log"
  Remove-Item $xml, $log -ErrorAction SilentlyContinue
  $args = @("-runTests","-batchmode","-projectPath",$Project,"-testPlatform","EditMode",
            "-assemblyNames",$Assemblies,"-testResults",$xml,"-logFile",$log)
  if ($Filter -ne "") { $args += @("-testFilter",$Filter) }
  $p = Start-Process -FilePath $Editor -ArgumentList $args -PassThru -NoNewWindow
  # A Start-Process that never started returns $null (measured). Without this the next line throws on
  # $null.WaitForExit, $p.ExitCode reads as $null, and the classifier below lands it in the run-error
  # bucket that blames -Assemblies/-Filter — steering diagnosis away from the process that never ran.
  if (-not $p) { return @{ outcome="NOSTART"; xml=$xml; log=$log; code=$null } }
  if (-not $p.WaitForExit($TimeoutSec * 1000)) { try { $p.Kill(); $p.WaitForExit(5000) } catch {}; return @{ outcome="TIMEOUT"; xml=$xml; log=$log; code=$null } }
  return @{ outcome=$null; xml=$xml; log=$log; code=$p.ExitCode }
}

function Test-CompileError($log) { (Test-Path $log) -and (Select-String -Path $log -Pattern "error CS" -Quiet) }

Write-Host "[runner] $Tag  filter='$Filter'"
$r = Invoke-Run $Tag
# stale-compile trap: the first batchmode run after a .cs edit can fail to compile and silently run the
# PREVIOUS assembly. Re-run once; if it STILL won't compile, the results XML is stale — don't trust it.
$compileErr = ($r.outcome -ne "TIMEOUT") -and (Test-CompileError $r.log)
if ($compileErr) {
  Write-Host "[runner] compile error detected — re-running once"
  $r = Invoke-Run $Tag
  $compileErr = ($r.outcome -ne "TIMEOUT") -and (Test-CompileError $r.log)
}

# After the re-run, not before it: the re-run can ALSO fail to start, and with no log written
# $compileErr/$crashed/$haveXml are all false and $r.code is $null, so it would fall through to the
# bad -Assemblies/-Filter bucket — the exact misdiagnosis NOSTART exists to prevent.
# WHICH TREE THIS RUN COMPILED, reported on the authoritative OUTCOME= line rather than left to the
# reader to infer. $Project's package pointer is baked at provisioning time and a worktree does not get
# its own by default (setup-test-editor.ps1 resolves -ToolsRoot to the MAIN checkout), so a run launched
# from a sub-repo worktree can be green about sources the caller never edited. Nothing here can know
# which tree the caller MEANT — no parameter carries it — so this reports the fact and refuses to guess
# intent; setup-test-editor.ps1 owns the refusal, at the point the pointer is actually set.
#
# It rides COMPLETED, COMPILE_ERROR and RUN_ERROR because "which tree" is exactly as load-bearing when
# the compile failed as when the suite passed. A green run is when nobody reads the log body, so it goes
# on the line itself.
$roots = @(Get-VenueToolPackageRoots $Project)
$embedded = @($roots | Where-Object { $_.Source -eq "embedded" })
if ($embedded.Count -gt 0) {
  # An embedded copy wins over the manifest, so reporting the manifest ref here would name a path that
  # did not load — the one case where a confident answer is worse than none.
  $pkgNote = " packages=EMBEDDED:" + (($embedded.Package | Sort-Object) -join ",")
} elseif ($null -ne (Get-VenueToolsRoot $Project)) {
  $pkgNote = " packages=" + (Get-VenueToolsRoot $Project)
} else {
  $pkgNote = " packages=UNREADABLE"
}

if ($r.outcome -eq "NOSTART") {
  Write-Host "OUTCOME=RUN_ERROR Unity did not start from '$Editor' — the path resolved but the process could not be launched"
  exit 5
}
if ($r.outcome -eq "TIMEOUT") { Write-Host "OUTCOME=TIMEOUT$pkgNote"; exit 3 }

# CRASH = native fault: the log crash signature, or a negative native-fault exit code (e.g. 0xC0000005
# → -1073741819) even when a results XML was flushed. Checked FIRST so a segfault-after-flush is never
# misread as COMPLETED. Unity's normal exits are non-negative (0 pass / 2 failures / 3 run-error).
$crashed = (Test-Path $r.log) -and (Select-String -Path $r.log -Pattern "Native Crash Reporting|Received signal SIGSEGV|Crash!!!" -Quiet)
if ($null -ne $r.code -and $r.code -lt 0) { $crashed = $true }
$haveXml = Test-Path $r.xml


if ($crashed) {
  Write-Host "OUTCOME=CRASH exit=$($r.code) xml=$haveXml$pkgNote"; exit 1
} elseif ($compileErr) {
  # Persistent compile failure: any XML present is from the prior assembly — not trustworthy.
  Write-Host "OUTCOME=COMPILE_ERROR exit=$($r.code) (see $($r.log))$pkgNote"; exit 7
} elseif ($haveXml) {
  [xml]$x = Get-Content $r.xml; $tr = $x.'test-run'
  Write-Host ("OUTCOME=COMPLETED exit={0} total={1} passed={2} failed={3} skipped={4}{5}" -f $r.code,$tr.total,$tr.passed,$tr.failed,$tr.skipped,$pkgNote)
  # A skip is not a pass, and a bare `skipped=N` reads as green. The suite carries deliberate
  # not-fabricable gaps (documented in their reasons) alongside cases that self-Ignore when an EXTERNAL
  # vendor fixture is absent — the latter silently withdraw an acceptance theorem, which is the rule-7
  # failure a count alone hides. Name each one and its reason so the withdrawal is legible in the log.
  if ([int]$tr.skipped -gt 0) {
    foreach ($tc in $x.SelectNodes("//test-case[@result='Skipped']")) {
      $why = $tc.SelectSingleNode("reason/message")
      $txt = if ($why) { " -- " + (($why.InnerText -replace '\s+', ' ').Trim()) } else { "" }
      Write-Host ("[runner] SKIPPED {0}{1}" -f $tc.fullname, $txt)
    }
  }
  # exit 0 only when truly green; failures get a distinct nonzero so a CI/wrapper keying on exit status
  # isn't fooled (the OUTCOME= line is authoritative either way).
  if ([int]$tr.failed -gt 0) { exit 6 }
} elseif ($r.code -ne 0) {
  # Unity launched but could not execute tests (exit 3 run-error: bad -Assemblies/-Filter, project load
  # failure) — NOT a native crash. Distinct bucket so it doesn't steer diagnosis into the crash narrative.
  Write-Host "OUTCOME=RUN_ERROR exit=$($r.code) (bad -Assemblies/-Filter or project load? see $($r.log))$pkgNote"; exit 5
} else {
  Write-Host "OUTCOME=UNKNOWN exit=$($r.code) xml=$haveXml (see $($r.log))$pkgNote"; exit 2
}
