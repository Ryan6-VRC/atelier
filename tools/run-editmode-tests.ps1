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
  [string]$Avatar     = "C:/Users/Ryan/Documents/Atelier/AvatarProject",
  [string]$Assemblies = "Ryan6VRC.AvatarTools.Tests;Ryan6VRC.AgentTools.Tests",
  [string]$Filter     = "",
  [Parameter(Mandatory=$true)][string]$Tag,
  [int]$TimeoutSec    = 540
)
$editor = "C:/Program Files/Unity/Hub/Editor/2022.3.22f1/Editor/Unity.exe"
$out = $PSScriptRoot

function Get-SdkVersion($proj, $pkg) {
  $pj = Join-Path $proj "Packages/$pkg/package.json"
  if (-not (Test-Path $pj)) { return $null }
  return (Get-Content $pj -Raw | ConvertFrom-Json).version
}

# --- SDK parity guard --- (package set must match setup-test-editor.ps1 $sdk, else a drift in an
# unchecked package silently runs stale)
foreach ($pkg in @("com.vrchat.base", "com.vrchat.avatars", "com.vrchat.core.bootstrap")) {
  $a = Get-SdkVersion $Avatar $pkg
  $t = Get-SdkVersion $Project $pkg
  if ($a -ne $t) {
    Write-Host "OUTCOME=SDK_DRIFT $pkg AvatarProject=$a TestEditor=$t — re-sync: tools/setup-test-editor.ps1 -Sync"
    exit 4
  }
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
