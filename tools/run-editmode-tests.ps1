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
  [string]$SourceProject = "C:/Users/Ryan/Documents/Atelier/AvatarProject",
  [string]$Assemblies = "Ryan6VRC.AvatarTools.Tests;Ryan6VRC.AgentTools.Tests",
  [string]$Filter     = "",
  [Parameter(Mandatory=$true)][string]$Tag,
  [int]$TimeoutSec    = 540
)
$editor = "C:/Program Files/Unity/Hub/Editor/2022.3.22f1/Editor/Unity.exe"
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
# would train reflexive re-sync. Re-copy on mismatch so TestEditor always tests current. The compose
# trio is what CheckSeam reflects; emulator/GestureManager are the real types PlayGateCoreTests builds.
# Absence IS fatal here: the test assemblies compile against these types, so the venue is broken.
foreach ($pkg in @("nadena.dev.ndmf", "nadena.dev.modular-avatar", "com.vrcfury.vrcfury",
                   "lyuma.av3emulator", "vrchat.blackstartx.gesture-manager")) {
  $a = Get-SdkVersion $SourceProject $pkg
  $t = Get-SdkVersion $Project $pkg
  if ($null -eq $a) { Write-Host "OUTCOME=RUN_ERROR $SourceProject missing $pkg — run 'vrc-get resolve' there"; exit 5 }
  if ($a -ne $t) {
    Write-Host "[runner] auto-sync $pkg  source=$a TestEditor=$t"
    Copy-PackageIn $pkg
    if ((Get-SdkVersion $Project $pkg) -ne $a) { Write-Host "OUTCOME=RUN_ERROR $pkg post-sync version mismatch"; exit 5 }
  }
}
# --- Fixture packages (soft) --- keep in step with setup-test-editor.ps1's $fixtures. A test READS an
# asset out of these rather than compiling against their types, so absence degrades ONE case instead of
# breaking the venue: that case self-Ignores and the skip is named in the OUTCOME block below. Never
# fatal — a single non-redistributable vendor package must not be able to stop the whole suite — and
# never DELETES a copy this venue already has, so a venue provisioned from a project carrying the
# fixture survives a later run whose $SourceProject does not.
foreach ($pkg in @("gogoloco")) {
  $a = Get-SdkVersion $SourceProject $pkg
  $t = Get-SdkVersion $Project $pkg
  if ($null -eq $a) {
    if ($null -eq $t) { Write-Host "[runner] fixture $pkg absent both sides — its cases self-Ignore" }
    else { Write-Host "[runner] fixture $pkg absent from source — keeping this venue's copy ($t)" }
    continue
  }
  if ($a -ne $t) { Write-Host "[runner] fixture sync $pkg  source=$a TestEditor=$t"; Copy-PackageIn $pkg -Soft }
}

function Invoke-Run([string]$tag) {
  $xml = Join-Path $out "results-$tag.xml"
  $log = Join-Path $out "run-$tag.log"
  Remove-Item $xml, $log -ErrorAction SilentlyContinue
  $args = @("-runTests","-batchmode","-projectPath",$Project,"-testPlatform","EditMode",
            "-assemblyNames",$Assemblies,"-testResults",$xml,"-logFile",$log)
  if ($Filter -ne "") { $args += @("-testFilter",$Filter) }
  $p = Start-Process -FilePath $editor -ArgumentList $args -PassThru -NoNewWindow
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

if ($r.outcome -eq "TIMEOUT") { Write-Host "OUTCOME=TIMEOUT"; exit 3 }

# CRASH = native fault: the log crash signature, or a negative native-fault exit code (e.g. 0xC0000005
# → -1073741819) even when a results XML was flushed. Checked FIRST so a segfault-after-flush is never
# misread as COMPLETED. Unity's normal exits are non-negative (0 pass / 2 failures / 3 run-error).
$crashed = (Test-Path $r.log) -and (Select-String -Path $r.log -Pattern "Native Crash Reporting|Received signal SIGSEGV|Crash!!!" -Quiet)
if ($null -ne $r.code -and $r.code -lt 0) { $crashed = $true }
$haveXml = Test-Path $r.xml

if ($crashed) {
  Write-Host "OUTCOME=CRASH exit=$($r.code) xml=$haveXml"; exit 1
} elseif ($compileErr) {
  # Persistent compile failure: any XML present is from the prior assembly — not trustworthy.
  Write-Host "OUTCOME=COMPILE_ERROR exit=$($r.code) (see $($r.log))"; exit 7
} elseif ($haveXml) {
  [xml]$x = Get-Content $r.xml; $tr = $x.'test-run'
  Write-Host ("OUTCOME=COMPLETED exit={0} total={1} passed={2} failed={3} skipped={4}" -f $r.code,$tr.total,$tr.passed,$tr.failed,$tr.skipped)
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
  Write-Host "OUTCOME=RUN_ERROR exit=$($r.code) (bad -Assemblies/-Filter or project load? see $($r.log))"; exit 5
} else {
  Write-Host "OUTCOME=UNKNOWN exit=$($r.code) xml=$haveXml (see $($r.log))"; exit 2
}
