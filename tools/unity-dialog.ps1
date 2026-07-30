<#
  unity-dialog.ps1 — see and press Unity's blocking modal dialogs from OUTSIDE the editor process.

  While a modal is up Unity's main thread sits in the dialog's own message loop: EditorApplication.update
  stops, the MCP queue stops draining, and every in-editor tool is unreachable — so the recovery path
  cannot live inside Unity. It doesn't have to: EditorUtility's dialogs are native Win32 (#32770) windows
  with real Button children, readable and pressable via user32.

  SAFETY DOCTRINE — never dismisses, never picks a default, never guesses. -Click requires the exact
  -Title AND the exact -Button (case-sensitive, no substring); any ambiguity is a refusal; there is no
  -Force and no -DismissAll. VRCFury's Write-Defaults prompt offers "Skip and stop asking", which
  PERSISTS a component onto the avatar — a tool that dismissed "whatever is up" would eventually make
  that decision itself. Naming the button is the caller stating intent.

  Usage:
    unity-dialog.ps1 -List [-Instance <ProjectName> | -ProcessId <pid>] [-Json]
    unity-dialog.ps1 -Click -Title <exact> -Button <exact> -ExpectHwnd <n> [-Instance <n> | -ProcessId <pid>]
  -List prints the ready-made -Click line with -ExpectHwnd filled in.

  Exit codes: 0 ok · 2 no Unity matched · 3 no such dialog · 4 ambiguous dialog · 5 no such button
              6 ambiguous button · 7 button disabled · 8 clicked but dialog still up · 9 hwnd moved
              10 interop failed to compile (the tool cannot see — never read as "no dialogs")
  These honour the caller's $ErrorActionPreference: an inherited 'Stop' terminates on Write-Error before
  the exit. Check output, not just $LASTEXITCODE.
#>
[CmdletBinding(DefaultParameterSetName = 'List')]
param(
  [Parameter(ParameterSetName = 'List')]  [switch]$List,
  [Parameter(ParameterSetName = 'Click')] [switch]$Click,
  [Parameter(ParameterSetName = 'Click', Mandatory = $true)] [string]$Title,
  [Parameter(ParameterSetName = 'Click', Mandatory = $true)] [string]$Button,
  # Pins the click to the window -List reported: that dialog can close and a same-titled one take its
  # place, and title+button exactness cannot tell two identical VRCFury WD prompts apart.
  [Parameter(ParameterSetName = 'Click', Mandatory = $true)] [int64]$ExpectHwnd,
  [int]$ProcessId = 0,
  [string]$Instance,
  [switch]$Json
)

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class UD {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int m);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr h, uint c);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)]
  public static extern IntPtr SendMessageTimeout(IntPtr h, uint msg, IntPtr wp, StringBuilder lp, uint flags, uint ms, out IntPtr res);
  [DllImport("user32.dll", EntryPoint="SendMessageTimeout")]
  public static extern IntPtr SendMsgTimeout(IntPtr h, uint msg, IntPtr wp, IntPtr lp, uint flags, uint ms, out IntPtr res);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
  public static string Cls(IntPtr h){ var s=new StringBuilder(256); GetClassName(h,s,256); return s.ToString(); }
  // WM_GETTEXT (0x0D), not GetWindowText: GetWindowText does NOT read child controls across a process
  // boundary — it returned the literal "Static" for a dialog's body. SMTO_ABORTIFHUNG (0x2) so a truly
  // dead editor times out instead of hanging the agent.
  public static string Txt(IntPtr h){
    var s=new StringBuilder(8192); IntPtr res;
    SendMessageTimeout(h, 0x0D, (IntPtr)8192, s, 0x2, 3000, out res);
    return s.ToString();
  }
}
"@

# Never -ErrorAction SilentlyContinue this Add-Type: a swallowed compile error leaves the enumeration
# finding nothing, so the tool prints "No modal dialogs" and exits 0 — a confident all-clear from a tool
# that never looked. Each run is a fresh process, so there is no re-Add-Type collision to suppress.
if (-not ('UD' -as [type])) {
  Write-Error "REFUSED: user32 interop failed to compile — this tool cannot see dialogs, and its silence must not be read as 'none'."
  exit 10
}

function Resolve-Targets {
  $unity = @(Get-Process -Name Unity -ErrorAction SilentlyContinue)
  if ($ProcessId -ne 0) { return @($unity | Where-Object { $_.Id -eq $ProcessId }) }
  if ($Instance) {
    # Unity's title is "<Project> - <Scene> - <Platform> - Unity <ver>". Key on the PROJECT segment
    # only — the scene segment drifts as scenes are opened, and it stays put while modal.
    return @($unity | Where-Object { ($_.MainWindowTitle -split ' - ')[0] -eq $Instance })
  }
  return $unity
}

function Get-Dialogs([int]$targetPid) {
  # A scriptblock used as a native callback does NOT close over this function's locals — the pid filter
  # silently matches nothing. Script scope is required.
  $script:wantPid = $targetPid
  $found = New-Object System.Collections.ArrayList
  $cb = [UD+EnumProc]{
    param($h, $l)
    $p = 0; [UD]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
    # Never filter on IsWindowVisible: Windows hides an owned dialog while its owner is minimized,
    # though it is live and still wedging — that filter reports "no dialogs" for a frozen editor.
    # The modal tell is the owner being DISABLED (below).
    if ($p -eq $script:wantPid -and [UD]::Cls($h) -eq '#32770') { $null = $found.Add($h) }
    return $true
  }
  [UD]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null

  $out = New-Object System.Collections.ArrayList
  foreach ($d in $found) {
    $buttons = New-Object System.Collections.ArrayList
    $bodies  = New-Object System.Collections.ArrayList
    $ccb = [UD+EnumProc]{
      param($ch, $cl)
      $cls = [UD]::Cls($ch)
      $t = [UD]::Txt($ch)
      $r = New-Object UD+RECT; [UD]::GetWindowRect($ch, [ref]$r) | Out-Null
      if ($cls -eq 'Button') {
        # Unity inserts accelerators and deconflicts them against sibling labels ("&Skip" vs
        # "S&kip and stop asking"), so raw text depends on which other buttons exist. '&&' is literal.
        $label = ($t -replace '&&', "`0") -replace '&', '' -replace "`0", '&'
        $null = $buttons.Add([pscustomobject]@{
          Label = $label; Raw = $t; HWND = [int64]$ch; CtrlId = [UD]::GetDlgCtrlID($ch)
          Enabled = [UD]::IsWindowEnabled($ch); X = $r.L
        })
      } elseif ($cls -eq 'Edit' -or $cls -eq 'Static') {
        if ($t.Trim()) { $null = $bodies.Add($t.Trim()) }
      }
      return $true
    }
    [UD]::EnumChildWindows($d, $ccb, [IntPtr]::Zero) | Out-Null
    $owner = [UD]::GetWindow($d, 4)  # GW_OWNER
    # IsWindowEnabled(NULL) is false, so an ownerless dialog would assert a wedge we never observed.
    $ownerBlocked = if ($owner -eq [IntPtr]::Zero) { 'unknown (no owner window)' }
                    else { -not [UD]::IsWindowEnabled($owner) }
    $null = $out.Add([pscustomobject]@{
      HWND         = [int64]$d
      Title        = [UD]::Txt($d)
      Body         = ($bodies -join "`n")
      # Sorted by screen X: enumeration order is neither display order nor the API argument order
      # (a 3-button ok/cancel/alt dialog enumerates ok, alt, cancel). Display only — never selection.
      Buttons      = @($buttons | Sort-Object X)
      OwnerTitle   = if ($owner -eq [IntPtr]::Zero) { '' } else { [UD]::Txt($owner) }
      OwnerBlocked = $ownerBlocked
    })
  }
  return $out
}

$targets = Resolve-Targets
if ($targets.Count -eq 0) { Write-Error "No Unity process matched (ProcessId=$ProcessId Instance='$Instance')."; exit 2 }

$report = @()
foreach ($t in $targets) {
  foreach ($d in (Get-Dialogs $t.Id)) {
    $report += [pscustomobject]@{
      ProcessId = $t.Id
      Project   = ($t.MainWindowTitle -split ' - ')[0]
      Dialog    = $d
    }
  }
}

# The resolved parameter set, not the $Click switch: binding -Title/-Button already selects the Click
# set, so testing the switch lets a fumbled `-Title X -Button Y` fall through to the list path and
# exit 0 — indistinguishable from a click that happened.
if ($PSCmdlet.ParameterSetName -eq 'Click') {
  $m = @($report | Where-Object { $_.Dialog.Title -ceq $Title })
  if ($m.Count -eq 0) {
    Write-Error "REFUSED: no dialog titled '$Title'. Run -List to see what is actually up (titles are case-sensitive)."
    exit 3
  }
  if ($m.Count -gt 1) {
    Write-Error "REFUSED: $($m.Count) dialogs titled '$Title' (pids: $(($m.ProcessId | Sort-Object -Unique) -join ', ')). Disambiguate with -ProcessId."
    exit 4
  }
  $d = $m[0].Dialog
  if ($d.HWND -ne $ExpectHwnd) {
    Write-Error "REFUSED: dialog '$Title' is hwnd $($d.HWND), not the expected $ExpectHwnd — it closed and another took its place. Re-run -List."
    exit 9
  }
  $hits = @($d.Buttons | Where-Object { $_.Label -ceq $Button })
  if ($hits.Count -eq 0) {
    Write-Error "REFUSED: dialog '$Title' has no button labelled '$Button'. Actual: $(($d.Buttons.Label | ForEach-Object { "'$_'" }) -join ', ')"
    exit 5
  }
  if ($hits.Count -gt 1) { Write-Error "REFUSED: '$Button' is ambiguous ($($hits.Count) buttons share it)."; exit 6 }
  $b = $hits[0]
  if (-not $b.Enabled) { Write-Error "REFUSED: button '$Button' is disabled."; exit 7 }

  # BM_CLICK (0xF5), sent not posted — a modal loop can drop a post. The send times out on SUCCESS
  # (the dialog tears down inside the call), so success is the window going away, not the return.
  $res = [IntPtr]::Zero
  [UD]::SendMsgTimeout([IntPtr]$b.HWND, 0xF5, [IntPtr]::Zero, [IntPtr]::Zero, 0x2, 5000, [ref]$res) | Out-Null
  foreach ($i in 1..20) {
    Start-Sleep -Milliseconds 250
    if (-not [UD]::IsWindow([IntPtr]$d.HWND)) {
      "CLICKED: '$Button' on '$Title' (pid $($m[0].ProcessId)) — dialog closed."
      exit 0
    }
  }
  Write-Warning "Sent BM_CLICK to '$Button' on '$Title' but the dialog is still up — it may have spawned a follow-up, or that button does not close it. Re-run -List."
  exit 8
}

if ($Json) { $report | ConvertTo-Json -Depth 6; exit 0 }
if ($report.Count -eq 0) {
  "No modal dialogs in $($targets.Count) Unity process(es): $(($targets | ForEach-Object { "$(($_.MainWindowTitle -split ' - ')[0])($($_.Id))" }) -join ', ')"
  exit 0
}
foreach ($r in $report) {
  ""
  "=== pid $($r.ProcessId)  project '$($r.Project)'  hwnd $($r.Dialog.HWND)"
  "  Title  : $($r.Dialog.Title)"
  "  Body   : $($r.Dialog.Body -replace "`r`n|`n", "`n           ")"
  "  Wedged : editor main window disabled = $($r.Dialog.OwnerBlocked)"
  "  Buttons:"
  foreach ($b in $r.Dialog.Buttons) {
    "    - '{0}'{1}" -f $b.Label, $(if(-not $b.Enabled){' [DISABLED]'}else{''})
  }
  # Single-quoted, embedded ' doubled: this line is built from vendor-controlled window text and
  # exists to be copied and RUN — a title containing " or $(...) would break or inject.
  $qTitle = "'" + ($r.Dialog.Title -replace "'", "''") + "'"
  "  Press with: tools/unity-dialog.ps1 -Click -Title $qTitle -Button '<one of the above>' -ProcessId $($r.ProcessId) -ExpectHwnd $($r.Dialog.HWND)"
}
