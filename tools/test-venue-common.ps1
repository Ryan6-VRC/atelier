<#
  Shared between setup-test-editor.ps1 (provisions TestEditor) and run-editmode-tests.ps1 (runs against
  it). Dot-source it; it defines variables and one function, and does nothing on its own.

  It exists for the two things the pair MUST agree on. Where the sibling projects live, because the two
  scripts derived it independently and both hardcoded one operator's home directory into a public repo.
  And which packages the venue carries, because the runner re-lists the community set and the fixture set
  that setup already declares — a duplication the runner's own comment asks the reader to maintain by
  hand ("keep in step with setup-test-editor.ps1's $fixtures"), which is the shape that drifts.
#>

# Packages copied verbatim from the source project as embedded folders (Unity auto-loads any
# Packages/<f> with a package.json; no manifest entry needed).
#
# SDK: VRChat-pinned, provisioned once and left alone.
$TestVenueSdk = @("com.vrchat.base", "com.vrchat.avatars", "com.vrchat.core.bootstrap")

# COMMUNITY: the test assemblies COMPILE against these types (the compose trio CheckSeam reflects, plus
# the emulator and Gesture Manager PlayGateCoreTests builds as real types), so absence is fatal at run
# time and the runner version-syncs them on every run.
$TestVenueCommunity = @("nadena.dev.ndmf", "nadena.dev.modular-avatar", "com.vrcfury.vrcfury",
                        "lyuma.av3emulator", "vrchat.blackstartx.gesture-manager")

# FIXTURE: a test READS an asset out of these rather than compiling against their types, so a venue
# without one is degraded, not broken — the affected case self-Ignores and the runner names the skip.
# Required-tier treatment would let one non-redistributable vendor package stop the whole suite, which
# is strictly worse than an honest skip. Absence therefore never fails and never DELETES a copy the
# venue already has: a venue provisioned from a project carrying the fixture must survive a later run
# whose source project does not.
$TestVenueFixtures = @("gogoloco")

<#
  .SYNOPSIS
  Absolute path of this repo's MAIN checkout, or $null when that cannot be established.

  .DESCRIPTION
  AvatarProject and vrc-unity-tools are siblings of the main checkout, NOT of the calling script, so
  $PSScriptRoot/.. is wrong from a worktree — a meta-repo worktree has no such siblings, which is why
  these defaults were absolute in the first place. --git-common-dir maps any worktree back to the main
  checkout's .git, so its parent is the main checkout.

  --path-format=absolute is load-bearing, not decoration: plain --git-common-dir answers a bare relative
  ".git" when run from the main checkout itself (measured, git 2.54), and joining ".." onto that resolves
  against the CALLER's working directory rather than the repo. -C anchors the query on the script rather
  than wherever the caller happens to be standing.

  Returns $null rather than throwing when git is absent or this is not a checkout, so each caller can
  refuse in its own vocabulary and name the parameter the operator should pass instead.
#>
function Get-AtelierMainCheckout {
  # Both callers set $ErrorActionPreference = "Stop" before dot-sourcing this, and PowerShell 7.4+
  # can promote a native command's nonzero exit into a terminating error under it
  # ($PSNativeCommandUseErrorActionPreference, whose default has moved between releases and can be
  # set in a profile). Pin both locally so "git said no" reaches the $LASTEXITCODE check below as a
  # value to test rather than an exception, on any host.
  $ErrorActionPreference = "Continue"
  $PSNativeCommandUseErrorActionPreference = $false
  $common = & git -C $PSScriptRoot rev-parse --path-format=absolute --git-common-dir 2>$null
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($common)) { return $null }
  $root = Join-Path $common ".."
  if (-not (Test-Path $root)) { return $null }
  return (Resolve-Path $root).Path
}

<#
  .SYNOPSIS
  Resolve a sibling of the main checkout by name, refusing loud with the parameter to pass instead.
#>
function Resolve-AtelierSibling([string]$Name, [string]$ParamName) {
  $main = Get-AtelierMainCheckout
  if ($null -eq $main) {
    throw "cannot locate the main checkout (git rev-parse failed here) — pass -$ParamName explicitly"
  }
  $path = Join-Path $main $Name
  if (-not (Test-Path $path)) {
    throw "$Name not found beside the main checkout at $main — pass -$ParamName explicitly"
  }
  return (Resolve-Path $path).Path
}
