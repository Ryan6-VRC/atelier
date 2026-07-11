<#
  Generate (or -Sync refresh) a local, gitignored TestEditor carrying the VRChat SDK plus the
  compose packages CheckSeam reflects (Modular Avatar / VRCFury / NDMF).
  TestEditor is the headless runner's never-opened target. Its SDK payload + manifest are copied
  from AvatarProject so the SDK version tracks AvatarProject automatically (ALCOM updates it there).
  Not a repo — a local artifact. See docs/bootstrap.md.
#>
param(
  # AvatarProject is the SDK version source of truth — always the main checkout (a nested repo, absent
  # from any meta-repo worktree), so this default is absolute, not script-relative.
  [string]$Avatar    = "C:/Users/Ryan/Documents/Atelier/AvatarProject",
  # TestEditor lives beside this script's repo root → worktree-local by default.
  [string]$Dest      = (Join-Path $PSScriptRoot "../TestEditor"),
  # Where the com.ryan6vrc.* packages under test live. Pass a worktree to verify its edits; the
  # generated manifest repoints the file: refs at this root (absolute), so TestEditor is never tied
  # to the main checkout's sibling layout.
  [string]$ToolsRoot = "C:/Users/Ryan/Documents/Atelier/vrc-unity-tools",
  [switch]$Sync
)
$ErrorActionPreference = "Stop"
# Packages copied verbatim from AvatarProject as embedded folders (Unity auto-loads any Packages/<f>
# with a package.json; no manifest entry needed). SDK trio is VRChat-pinned; the compose trio is what
# CheckSeam reflects and is auto-synced by run-editmode-tests.ps1 (not manifest-pinned here).
$sdk = @("com.vrchat.base", "com.vrchat.avatars", "com.vrchat.core.bootstrap",
         "nadena.dev.ndmf", "nadena.dev.modular-avatar", "com.vrcfury.vrcfury")

if ((Test-Path $Dest) -and -not $Sync) {
  Write-Host "TestEditor already exists at $Dest. Use -Sync to refresh its SDK + manifest."
  exit 0
}
New-Item -ItemType Directory -Force -Path "$Dest/Assets", "$Dest/Packages" | Out-Null

# SDK payload — the version source of truth is AvatarProject's gitignored embedded folders.
foreach ($p in $sdk) {
  $src = Join-Path $Avatar "Packages/$p"
  if (-not (Test-Path $src)) {
    Write-Error "AvatarProject is missing $p. Run 'vrc-get resolve' in AvatarProject first."
  }
  $dstp = Join-Path $Dest "Packages/$p"
  if (Test-Path $dstp) { Remove-Item -Recurse -Force $dstp }
  Copy-Item -Recurse $src $dstp
}

# ProjectSettings — carries the pinned Unity version + VRChat layers.
$psDst = Join-Path $Dest "ProjectSettings"
if (Test-Path $psDst) { Remove-Item -Recurse -Force $psDst }
Copy-Item -Recurse (Join-Path $Avatar "ProjectSettings") $psDst

# Manifest = AvatarProject's, minus the MCP line (community VRChat packages aren't copied, so they're
# simply absent), with the two com.ryan6vrc.* file: refs repointed at $ToolsRoot as ABSOLUTE paths.
# AvatarProject's refs are relative (file:../../vrc-unity-tools/...) and resolve only for a sibling of
# AvatarProject; a worktree-local TestEditor is not that sibling, so rewrite to absolute.
$toolsFull = (Resolve-Path $ToolsRoot).Path -replace '\\', '/'
$manifest = Get-Content (Join-Path $Avatar "Packages/manifest.json") | ForEach-Object {
  if ($_ -match 'com\.coplaydev\.unity-mcp') { return }
  if ($_ -match 'com\.ryan6vrc\.patterns') { return }  # example library, not under test; absent from worktree trees
  $_ -replace 'file:[^"]*packages/(com\.ryan6vrc\.[^"/]+)', "file:$toolsFull/packages/`$1"
}
$manifest | Set-Content -Encoding UTF8 (Join-Path $Dest "Packages/manifest.json")

Write-Host "TestEditor ready at $Dest (SDK: $((Get-Content "$Dest/Packages/com.vrchat.avatars/package.json" -Raw | ConvertFrom-Json).version))"
