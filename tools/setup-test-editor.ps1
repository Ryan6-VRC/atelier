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
  # AvatarProject inside the main checkout", resolved below rather than written out here: it is
  # untracked, so a worktree's own root does not carry it and script-relative cannot reach it.
  [string]$SourceProject = "",
  # TestEditor lives beside this script's repo root → worktree-local by default.
  [string]$Dest      = (Join-Path $PSScriptRoot "../TestEditor"),
  # Where the com.ryan6vrc.* packages under test live. Pass a worktree to verify its edits; the
  # generated manifest repoints the file: refs at this root (absolute), so TestEditor is never tied
  # to the main checkout's own layout. Empty resolves the same way as $SourceProject.
  [string]$ToolsRoot = "",
  [switch]$Sync
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "test-venue-common.ps1")
if ([string]::IsNullOrWhiteSpace($SourceProject)) { $SourceProject = Resolve-AtelierChild "AvatarProject" "SourceProject" }
if ([string]::IsNullOrWhiteSpace($ToolsRoot))     { $ToolsRoot     = Resolve-AtelierChild "vrc-unity-tools" "ToolsRoot" }
# Canonicalize once. The manifest bakes the RESOLVED path, so a relative -ToolsRoot compared raw
# against a baked ref reports a mismatch between two spellings of the same directory — and -Sync,
# the remedy the refusal names, re-bakes the identical absolute path, so the next run refuses again.
if (Test-Path $ToolsRoot) { $ToolsRoot = (Resolve-Path $ToolsRoot).Path }

# Provisioned once from $SourceProject: the VRChat-pinned SDK plus the community packages the test
# assemblies compile against. Both lists, and the fixture list below, live in test-venue-common.ps1
# because run-editmode-tests.ps1 version-syncs the same sets on every run.
$sdk = $TestVenueSdk + $TestVenueCommunity
$fixtures = $TestVenueFixtures

if ((Test-Path $Dest) -and -not $Sync) {
  # -ToolsRoot is baked into the venue's manifest at PROVISIONING time, so an existing venue keeps
  # pointing wherever it was first pointed and this early return would drop the argument in silence
  # under a success exit. That is the trap this refusal exists for: a worktree worker passes
  # -ToolsRoot, reads "already exists" + exit 0 as provisioned-as-asked, runs the suite against the
  # MAIN checkout's sources, and reads the green as evidence about their own edits. A supplied
  # argument that changes nothing must say so.
  #
  # Silent only when the venue AGREES with the request, which is the ordinary re-run. Every other
  # branch here exits NON-ZERO: each one is a state where -ToolsRoot could not be honored, and a
  # caller chaining setup -> tests on $LASTEXITCODE must not walk into the wrong-tree run.
  #
  # Shadow first, matching Unity's own precedence. An embedded Packages/<name>/ copy wins over the
  # manifest, and Get-VenueToolsRoot excludes embedded entries — so a venue with one package
  # embedded and another pointing at the main checkout would otherwise hit the mismatch below and
  # assert a $baked root that is false for the shadowed package, while never naming the shadow.
  # -Sync would not help either: it rewrites the manifest and never deletes a stray folder.
  $shadowed = @(Get-VenueToolPackageRoots $Dest | Where-Object { $_.Source -eq "embedded" })
  if ($shadowed.Count -gt 0) {
    throw ("TestEditor at $Dest carries EMBEDDED copies of " + ($shadowed.Package -join ", ") +
           " under Packages/, which shadow the manifest — Unity loads those, so -ToolsRoot cannot " +
           "reach them and -Sync will not remove them. Delete those folders, or provision a venue " +
           "of your own with -Dest <path> -ToolsRoot $ToolsRoot.")
  }
  $baked = Get-VenueToolsRoot $Dest
  if ($null -eq $baked) {
    # Unreadable is not agreement: no manifest refs, an unparseable ref, or refs spanning two
    # checkouts (see Get-VenueToolsRoot). None of them may pass as "points where you asked".
    throw ("TestEditor at $Dest has no readable com.ryan6vrc.* package pointer — it names no root, " +
           "or more than one, so what a run against it would compile cannot be established. " +
           "Re-provision with -Sync, or with -Dest <path> -ToolsRoot $ToolsRoot.")
  }
  if ((ConvertTo-ComparablePath $baked) -ne (ConvertTo-ComparablePath $ToolsRoot)) {
    throw ("TestEditor at $Dest compiles the com.ryan6vrc.* packages at $baked, not the requested " +
           "$ToolsRoot — a run against it would say nothing about $ToolsRoot. Re-point it with -Sync, " +
           "or provision a venue of your own with -Dest <path> -ToolsRoot $ToolsRoot.")
  }
  Write-Host "TestEditor already exists at $Dest (packages: $baked). Use -Sync to refresh its SDK + manifest."
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
