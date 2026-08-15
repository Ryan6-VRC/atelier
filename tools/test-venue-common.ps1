<#
  Shared between setup-test-editor.ps1 (provisions TestEditor) and run-editmode-tests.ps1 (runs against
  it). Dot-source it; it defines variables and two functions, and does nothing on its own.

  It exists for the two things the pair MUST agree on. Where the untracked working projects live inside
  the checkout, because the two scripts derived it independently and both hardcoded one operator's home
  directory into a public repo.
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
  AvatarProject and vrc-unity-tools sit INSIDE the main checkout (`Atelier/AvatarProject`), as untracked
  working venues and gitignored sibling clones. Being untracked is what makes $PSScriptRoot/.. wrong: from
  the main checkout that path is the checkout root and does resolve, but from a worktree it is the
  worktree root, which carries only tracked files and therefore has neither of them. That is why these
  defaults were absolute in the first place. --git-common-dir maps any worktree back to the main
  checkout's .git, so its parent is the main checkout.

  --path-format=absolute is load-bearing, not decoration: plain --git-common-dir answers a bare relative
  ".git" when run from the main checkout itself (measured, git 2.54), and joining ".." onto that resolves
  against the CALLER's working directory rather than the repo. -C anchors the query on the script rather
  than wherever the caller happens to be standing.

  Returns $null rather than throwing when git is absent or this is not a checkout, so each caller can
  refuse in its own vocabulary and name the parameter the operator should pass instead.
#>
function Get-AtelierMainCheckout {
  # setup-test-editor.ps1 sets $ErrorActionPreference = "Stop" before dot-sourcing this, a host profile
  # can set it anywhere, and PowerShell 7.4+ can then promote a native command's nonzero exit into a
  # terminating error ($PSNativeCommandUseErrorActionPreference, whose default has moved between
  # releases). Pin both locally so "git said no" reaches the $LASTEXITCODE check as a value to test.
  #
  # The try/catch is a SEPARATE failure mode, not belt-and-braces: if git is not on PATH at all, the
  # failure is command DISCOVERY (CommandNotFoundException), which is terminating regardless of either
  # preference — measured. Without the catch this function throws where its contract promises $null,
  # setup-test-editor.ps1 dies on a raw exception instead of naming -SourceProject, and
  # run-editmode-tests.ps1 reports RUN_ERROR with the actionable half of the message missing.
  $ErrorActionPreference = "Continue"
  $PSNativeCommandUseErrorActionPreference = $false
  try { $common = & git -C $PSScriptRoot rev-parse --path-format=absolute --git-common-dir 2>$null }
  catch { return $null }
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($common)) { return $null }
  $root = Join-Path $common ".."
  if (-not (Test-Path $root)) { return $null }
  return (Resolve-Path $root).Path
}

<#
  .SYNOPSIS
  Resolve a child of the main checkout by name, refusing loud with the parameter to pass instead.

  .DESCRIPTION
  Named for where it actually looks. "Sibling"/"beside" would send an operator reading the refusal to the
  main checkout's PARENT directory, where nothing is and where this never searches.
#>
function Resolve-AtelierChild([string]$Name, [string]$ParamName) {
  $main = Get-AtelierMainCheckout
  if ($null -eq $main) {
    throw "cannot locate the main checkout (git rev-parse failed here) — pass -$ParamName explicitly"
  }
  $path = Join-Path $main $Name
  if (-not (Test-Path $path)) {
    throw "$Name not found inside the main checkout at $main — pass -$ParamName explicitly"
  }
  return (Resolve-Path $path).Path
}

<#
  .SYNOPSIS
  One path form for comparing two roots that came from different producers.

  .DESCRIPTION
  A baked manifest ref is forward-slashed (setup-test-editor.ps1 writes it that way); anything from
  Resolve-Path is backslashed. Comparing them raw reports a mismatch between two spellings of the same
  directory, which would turn the provisioning guard into a refusal nobody can satisfy.
#>
function ConvertTo-ComparablePath([string]$Path) {
  if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
  return ($Path -replace '\\', '/').TrimEnd('/')
}

<#
  .SYNOPSIS
  Where a venue's com.ryan6vrc.* packages actually come from — one entry per package, each naming the
  path Unity will load and which mechanism reached it.

  .DESCRIPTION
  Two mechanisms, returned in Unity's own precedence order. An EMBEDDED folder (Packages/<name>/ carrying
  a package.json) wins outright and the manifest entry for that name is never consulted — the SDK payload
  at the top of this file relies on exactly that behavior, so a stray embedded copy of a TOOL package
  would shadow the manifest silently and every manifest-derived report about it would be a confident lie.
  Checking embedded first is what keeps the answer honest.

  Returns an empty array when the venue carries neither, rather than throwing: callers report a named
  unknown instead of failing a provisioning step or a completed test run over a bookkeeping read.
#>
function Get-VenueToolPackageRoots([string]$Venue) {
  $found = @()
  $pkgDir = Join-Path $Venue "Packages"
  if (-not (Test-Path $pkgDir)) { return $found }

  $embedded = @{}
  foreach ($dir in (Get-ChildItem $pkgDir -Directory -Filter "com.ryan6vrc.*" -ErrorAction SilentlyContinue)) {
    if (-not (Test-Path (Join-Path $dir.FullName "package.json"))) { continue }
    $embedded[$dir.Name] = $true
    $found += [pscustomobject]@{ Package = $dir.Name; Path = $dir.FullName; Source = "embedded" }
  }

  # Parsed as JSON, not scanned line-wise: a regex per line captures at most one ref per line, so a
  # minified or hand-collapsed manifest would report a two-checkout venue as one root — defeating
  # the half-repointed-venue answer Get-VenueToolsRoot exists to give, and defeating it by producing
  # a confident wrong root rather than a refusal.
  $manifest = Join-Path $pkgDir "manifest.json"
  if (Test-Path $manifest) {
    $deps = $null
    # A malformed manifest is a named unknown (an empty list), never a throw: this read happens
    # inside a provisioning guard and at the end of a completed test run, and neither may die over it.
    try { $deps = (Get-Content $manifest -Raw -ErrorAction Stop | ConvertFrom-Json).dependencies }
    catch { $deps = $null }
    if ($null -ne $deps) {
      foreach ($prop in $deps.PSObject.Properties) {
        if ($prop.Name -notlike "com.ryan6vrc.*") { continue }
        if ($embedded.ContainsKey($prop.Name)) { continue }  # shadowed; the embedded copy is what loads
        if ($prop.Value -isnot [string] -or $prop.Value -notmatch '^file:(.+)$') { continue }
        $found += [pscustomobject]@{ Package = $prop.Name; Path = $Matches[1]; Source = "manifest" }
      }
    }
  }
  return $found
}

<#
  .SYNOPSIS
  The single vrc-unity-tools checkout a venue's manifest points at, or $null when that is not one
  unambiguous answer.

  .DESCRIPTION
  $null covers three genuinely different situations that share one remedy (re-provision with -Sync), and
  none of them may be reported as a root: no manifest refs at all, refs whose parent is not a `packages/`
  directory this can strip, and refs spanning MORE than one checkout — the last being a venue left
  half-repointed by an interrupted run, where naming either root would be a lie.

  Embedded entries are excluded deliberately: they have no tools-root to speak of, and a caller that needs
  to know about a shadow asks Get-VenueToolPackageRoots, which reports it as one.
#>
function Get-VenueToolsRoot([string]$Venue) {
  $roots = @()
  foreach ($entry in (Get-VenueToolPackageRoots $Venue)) {
    if ($entry.Source -ne "manifest") { continue }
    if ((ConvertTo-ComparablePath $entry.Path) -match '^(.*)/packages/com\.ryan6vrc\.[^/]+$') {
      $roots += $Matches[1]
    }
  }
  $unique = @($roots | Sort-Object -Unique)
  if ($unique.Count -eq 1) { return $unique[0] }
  return $null
}
