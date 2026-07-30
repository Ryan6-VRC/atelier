<#
  Generate (or -Sync refresh) a local, gitignored TestEditor carrying the VRChat SDK plus the
  community packages the EditMode tests build as real types (Modular Avatar / VRCFury / NDMF,
  Av3Emulator, Gesture Manager).
  TestEditor is the headless runner's never-opened target: self-contained at RUN time (packages are
  copied in as embedded folders, so no registry is consulted) but provisioned by copying from a real
  Unity project, so its SDK version tracks the project you actually build with.
  Not a repo — a local artifact. See docs/bootstrap.md.
#>
param(
  # The Unity project whose Packages/ payload is copied in, and the version baseline the runner's
  # SDK-parity guard compares against — NOT an avatar. Any real project works. Empty means "the
  # AvatarProject beside the main checkout", resolved below rather than written out here: it is a
  # sibling of the MAIN checkout, not of this script, so a worktree cannot reach it script-relative.
  [string]$SourceProject = "",
  # TestEditor lives beside this script's repo root → worktree-local by default.
  [string]$Dest      = (Join-Path $PSScriptRoot "../TestEditor"),
  # Where the com.ryan6vrc.* packages under test live. Pass a worktree to verify its edits; the
  # generated manifest repoints the file: refs at this root (absolute), so TestEditor is never tied
  # to the main checkout's sibling layout. Empty resolves the same way as $SourceProject.
  [string]$ToolsRoot = "",
  [switch]$Sync
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "test-venue-common.ps1")
if ([string]::IsNullOrWhiteSpace($SourceProject)) { $SourceProject = Resolve-AtelierSibling "AvatarProject" "SourceProject" }
if ([string]::IsNullOrWhiteSpace($ToolsRoot))     { $ToolsRoot     = Resolve-AtelierSibling "vrc-unity-tools" "ToolsRoot" }

# Provisioned once from $SourceProject: the VRChat-pinned SDK plus the community packages the test
# assemblies compile against. Both lists, and the fixture list below, live in test-venue-common.ps1
# because run-editmode-tests.ps1 version-syncs the same sets on every run.
$sdk = $TestVenueSdk + $TestVenueCommunity
$fixtures = $TestVenueFixtures

if ((Test-Path $Dest) -and -not $Sync) {
  Write-Host "TestEditor already exists at $Dest. Use -Sync to refresh its SDK + manifest."
  exit 0
}
New-Item -ItemType Directory -Force -Path "$Dest/Assets", "$Dest/Packages" | Out-Null

# SDK payload — the version baseline is $SourceProject's gitignored embedded folders.
foreach ($p in $sdk) {
  $src = Join-Path $SourceProject "Packages/$p"
  if (-not (Test-Path $src)) {
    Write-Error "$SourceProject is missing $p. Run 'vrc-get resolve' there first."
  }
  $dstp = Join-Path $Dest "Packages/$p"
  if (Test-Path $dstp) { Remove-Item -Recurse -Force $dstp }
  Copy-Item -Recurse $src $dstp
}

# Fixture payload — copy when present, say so when not, never remove. Reported either way so a venue's
# fixture coverage is visible at provision time rather than inferred from a skip later.
#
# Staged to a temp sibling then swapped, for the same reason the runner's Copy-PackageIn is: a mid-copy
# failure (and $ErrorActionPreference is Stop) must not leave a PARTIAL fixture behind. A partial one is
# worse than none, because package.json lands early — so the tree is incomplete while the version reads
# correct, the runner's version check then sees no mismatch and never repairs it, and the acceptance case
# self-Ignores. That is a green run with the theorem silently withdrawn: the failure this tier exists to
# make impossible.
foreach ($p in $fixtures) {
  $src  = Join-Path $SourceProject "Packages/$p"
  $dstp = Join-Path $Dest "Packages/$p"
  if (Test-Path $src) {
    $tmp = "$dstp.tmp"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    Copy-Item -Recurse $src $tmp
    if (Test-Path $dstp) { Remove-Item -Recurse -Force $dstp }
    Rename-Item $tmp (Split-Path $dstp -Leaf)
    Write-Host "[setup] fixture $p present"
  } elseif (Test-Path $dstp) {
    Write-Host "[setup] fixture $p absent from $SourceProject — KEEPING the copy already in this venue"
  } else {
    Write-Host "[setup] fixture $p absent — cases needing it will self-Ignore (the runner names the skip)"
  }
}

# ProjectSettings — carries the pinned Unity version + VRChat layers.
$psDst = Join-Path $Dest "ProjectSettings"
if (Test-Path $psDst) { Remove-Item -Recurse -Force $psDst }
Copy-Item -Recurse (Join-Path $SourceProject "ProjectSettings") $psDst

# Manifest = $SourceProject's, minus the MCP line (community VRChat packages aren't copied, so they're
# simply absent), with the two com.ryan6vrc.* file: refs repointed at $ToolsRoot as ABSOLUTE paths.
# A source project's refs are relative (file:../../vrc-unity-tools/...) and resolve only for a sibling
# of that project; a worktree-local TestEditor is not that sibling, so rewrite to absolute.
$toolsFull = (Resolve-Path $ToolsRoot).Path -replace '\\', '/'
$manifest = Get-Content (Join-Path $SourceProject "Packages/manifest.json") | ForEach-Object {
  if ($_ -match 'com\.coplaydev\.unity-mcp') { return }
  if ($_ -match 'com\.ryan6vrc\.patterns') { return }  # example library, not under test; absent from worktree trees
  $_ -replace 'file:[^"]*packages/(com\.ryan6vrc\.[^"/]+)', "file:$toolsFull/packages/`$1"
}
$manifest | Set-Content -Encoding UTF8 (Join-Path $Dest "Packages/manifest.json")

Write-Host "TestEditor ready at $Dest (SDK: $((Get-Content "$Dest/Packages/com.vrchat.avatars/package.json" -Raw | ConvertFrom-Json).version))"
