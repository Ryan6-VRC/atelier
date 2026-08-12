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
  Absolute path of the Unity.exe matching $Project's pinned editor version.

  .DESCRIPTION
  The version comes from the PROJECT, never from a parameter: opening a Unity project with a
  mismatched editor silently upgrades it, and in batchmode that happens with nobody watching. A
  caller who genuinely needs a different binary passes it in and skips this function entirely.

  Throws with the searched locations named, so a caller can report in its own vocabulary.
#>
function Resolve-UnityEditor([string]$Project) {
  $pv = Join-Path $Project "ProjectSettings/ProjectVersion.txt"
  if (-not (Test-Path $pv)) { throw "no ProjectVersion.txt at $pv — is $Project a Unity project?" }
  # Select-String emits NOTHING on no match, so $m.Matches would be $null and $null.Groups[1] throws
  # "Cannot index into a null array" (measured) before any guard on $ver could read it. Test $m first.
  $m = Get-Content $pv | Select-String '^m_EditorVersion:\s*(\S+)'
  if (-not $m) { throw "no m_EditorVersion line in $pv" }
  $ver = $m[0].Matches[0].Groups[1].Value

  $tried = @()
  # Hub registry first. A Hub entry can be "manual":true (an editor registered from a custom
  # location), so the default path below is a fallback and never the authority.
  $reg = Join-Path $env:APPDATA "UnityHub/editors-v2.json"
  if (Test-Path $reg) {
    try {
      foreach ($e in (Get-Content $reg -Raw | ConvertFrom-Json).data) {
        if ($e.version -ne $ver) { continue }
        # `location` is an array in the schema but a bare string in older Hub writes; @() takes both.
        # Where-Object drops null entries: Test-Path on $null writes a raw error that the catch below
        # cannot see (it is non-terminating), so one malformed entry would spray red and continue.
        foreach ($loc in @($e.location) | Where-Object { $_ }) {
          $tried += $loc
          if (Test-Path $loc) { return $loc }
        }
      }
    } catch {
      # A corrupt, truncated or schema-changed registry is not fatal — the default path may still
      # hold. Name it in $tried so the refusal shows the registry was consulted and did not answer.
      $tried += "$reg (unreadable: $($_.Exception.Message))"
    }
  } else {
    $tried += "$reg (absent)"
  }

  $default = "C:/Program Files/Unity/Hub/Editor/$ver/Editor/Unity.exe"
  $tried += $default
  if (Test-Path $default) { return $default }

  throw "Unity $ver (pinned by $pv) not found — install it via Unity Hub. Searched: $($tried -join '; ')"
}
