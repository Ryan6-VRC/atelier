<#
  Resolves the Unity.exe that belongs to a given Unity project. Dot-source it; it defines one function
  and does nothing on its own.

  Shared because there are two consumers in two repos: tools/run-editmode-tests.ps1 here, and
  vrc-patterns/tools/gate.ps1, which reaches this file through the Atelier root it already resolves.
  Both previously hardcoded the same "C:/Program Files/Unity/Hub/Editor/<pinned>/Editor/Unity.exe" —
  the shape test-venue-common.ps1 exists to end, arrived at independently a second time.

  The ladder is docs/unity.md's, not a new one: the Unity Hub registry (which covers custom install
  dirs), then Hub's default install dir. Read it there for why an agent bringing an editor up by hand
  follows the same order.
#>

<#
  .SYNOPSIS
  The editor version a Unity project is pinned to, or $null when it cannot be read.

  .DESCRIPTION
  Separate from Resolve-UnityEditor because callers need the bare version too — the runner compares
  a venue's against its source project's. Returns $null for BOTH "no such file" and "no such line",
  so a caller can treat an unreadable project as one condition and write its own refusal.
#>
function Get-UnityProjectVersion([string]$Project) {
  $pv = Join-Path $Project "ProjectSettings/ProjectVersion.txt"
  if (-not (Test-Path -LiteralPath $pv)) { return $null }
  # Select-String emits NOTHING on no match, so $m.Matches would be $null and $null.Groups[1] throws
  # "Cannot index into a null array" (measured) before any guard could read the result. Test $m first.
  $m = Get-Content -LiteralPath $pv | Select-String '^m_EditorVersion:\s*(\S+)'
  if (-not $m) { return $null }
  return $m[0].Matches[0].Groups[1].Value
}

<#
  .SYNOPSIS
  Absolute path of the Unity.exe matching $Project's pinned editor version.

  .DESCRIPTION
  The version comes from the PROJECT, never from a parameter: opening a Unity project with a
  mismatched editor silently upgrades it, and in batchmode that happens with nobody watching. A
  caller who genuinely needs a different binary passes it in and skips this function entirely.

  Every path test is -LiteralPath. Test-Path treats its argument as a WILDCARD pattern, so a real
  Unity.exe under a directory containing [ ] or ? reads as absent (measured) — and a custom install
  directory is exactly what the registry branch exists to find, so the plain form fails hardest in
  the case this function was written for.

  Throws with the searched locations named, so a caller can report in its own vocabulary.
#>
function Resolve-UnityEditor([string]$Project) {
  $pv = Join-Path $Project "ProjectSettings/ProjectVersion.txt"
  $ver = Get-UnityProjectVersion $Project
  if (-not $ver) { throw "no readable m_EditorVersion in $pv — is $Project a Unity project?" }

  # Hub registry first. A Hub entry can be "manual":true (an editor registered from a custom
  # location), so the default path below is a fallback and never the authority.
  $reg = Join-Path $env:APPDATA "UnityHub/editors-v2.json"
  $tried = @()
  $regNote = ""
  if (Test-Path -LiteralPath $reg) {
    try {
      $data = (Get-Content -LiteralPath $reg -Raw | ConvertFrom-Json).data
      foreach ($e in @($data)) {
        # An EMPTY registry file reads as $null, and `$null | ConvertFrom-Json` returns nothing
        # without throwing (measured), so the catch never sees it — skip the empty entry here.
        if (-not $e -or $e.version -ne $ver) { continue }
        # `location` is an array in the schema but a bare string in older Hub writes; @() takes both.
        # Where-Object drops null entries: Test-Path on $null writes a raw error that the catch
        # cannot see (it is non-terminating), so one malformed entry would spray red and continue.
        foreach ($loc in @($e.location) | Where-Object { $_ }) {
          $tried += $loc
          if (Test-Path -LiteralPath $loc -PathType Leaf) { return $loc }
        }
      }
    } catch {
      # A corrupt or truncated registry is not fatal — the default path may still hold.
      $regNote = " (unreadable: $($_.Exception.Message))"
    }
  } else {
    $regNote = " (absent)"
  }
  # Named unconditionally, ahead of whatever it yielded: the registry can be perfectly readable and
  # still answer nothing — no entry for this version, or a schema change that moves .data — and a
  # refusal listing only the default path would misreport the registry as never consulted.
  $tried = @("$reg$regNote") + $tried

  # $env:ProgramFiles, not a literal C:/Program Files: the version was lifted out of the hardcoded
  # path and the root deserves the same treatment on a host that redirects it.
  $pf = if ($env:ProgramFiles) { $env:ProgramFiles } else { "C:/Program Files" }
  $default = Join-Path $pf "Unity/Hub/Editor/$ver/Editor/Unity.exe"
  $tried += $default
  if (Test-Path -LiteralPath $default -PathType Leaf) { return $default }

  throw "Unity $ver (pinned by $pv) not found — install it via Unity Hub. Searched: $($tried -join '; ')"
}
