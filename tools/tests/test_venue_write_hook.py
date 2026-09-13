# tools/tests/test_venue_write_hook.py
"""The hook's risk is entirely in its three detection arms, and each rests on a different
measured fact: where a write tool puts its path, that a Unity root is exactly the directory
holding ProjectSettings/ProjectVersion.txt, and which UnityMCP tools mutate. None of those is
a documented contract, so they rot silently.

Every fixture builds its own venue tree and points CLAUDE_PROJECT_DIR and HOME at temp dirs,
so a run never depends on which Editors this machine happens to have — and never fires on the
operator's real venues.

pwsh is required; without it the whole fixture skips rather than passing vacuously."""
import json
import os
import time
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "venue-write-hook.ps1"
PWSH = shutil.which("pwsh")

VENUE_DOC = "# Venue rules\n\nSENTINEL-BODY — with an em-dash.\n"


@unittest.skipUnless(PWSH, "pwsh not on PATH")
class VenueWriteHook(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="vwh-"))
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)
        self.proj = self.temp / "proj"
        (self.proj / "docs").mkdir(parents=True)
        (self.proj / "docs" / "VENUE.md").write_text(VENUE_DOC, encoding="utf-8")
        # A venue is a Unity project root: the marker file is the whole definition.
        self.venue = self.proj / "MyVenue"
        (self.venue / "ProjectSettings").mkdir(parents=True)
        (self.venue / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.22f1\n")
        (self.venue / "Assets").mkdir()
        self.markers = self.temp / "markers"
        self.markers.mkdir()
        self.home = self.temp / "home"  # no ~/.unity-mcp, so heartbeats contribute nothing
        self.home.mkdir()

    def fire(self, tool, tool_input, session="S", agent=None):
        """Returns the injected text, or None when the hook stayed silent. A nonzero exit is
        itself a failure: this hook must never block a write."""
        ev = {
            "session_id": session,
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "tool_input": tool_input,
        }
        if agent:
            ev["agent_id"] = agent
        env = {
            **os.environ,
            "TEMP": str(self.markers),
            "TMP": str(self.markers),
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "CLAUDE_PROJECT_DIR": str(self.proj),
        }
        p = subprocess.run(
            [PWSH, "-NoProfile", "-File", str(HOOK)],
            input=json.dumps(ev), capture_output=True, text=True,
            encoding="utf-8", env=env,
        )
        self.assertEqual(p.returncode, 0, f"hook must never block: {p.stderr}")
        if not p.stdout.strip():
            return None
        out = json.loads(p.stdout)
        return out["hookSpecificOutput"]["additionalContext"]

    # --- the Write|Edit arm: ancestor walk ---

    def test_write_inside_venue_fires(self):
        got = self.fire("Write", {"file_path": str(self.venue / "Assets" / "Owned" / "x.prefab")})
        self.assertIsNotNone(got)

    def test_dump_is_the_whole_file_not_a_summary(self):
        got = self.fire("Write", {"file_path": str(self.venue / "Assets" / "x.prefab")})
        self.assertIn("SENTINEL-BODY", got)
        # The em-dash is the canary for pwsh's stdout encoding: a mangled one means the agent
        # reads a different document than the file on disk.
        self.assertIn("—", got)

    def test_write_outside_venue_is_silent(self):
        self.assertIsNone(self.fire("Write", {"file_path": str(self.proj / "docs" / "unity.md")}))

    def test_edit_and_notebook_paths_are_read(self):
        self.assertIsNotNone(self.fire("Edit", {"file_path": str(self.venue / "Assets" / "a.mat")}, session="e"))
        self.assertIsNotNone(
            self.fire("NotebookEdit", {"notebook_path": str(self.venue / "Assets" / "n.ipynb")}, session="n")
        )

    # --- the Bash arm: substring match against discovered roots ---

    def test_bash_naming_a_venue_root_fires(self):
        cmd = f"cp a.png {self.venue.as_posix()}/Assets/x.png"
        self.assertIsNotNone(self.fire("Bash", {"command": cmd}, session="b1"))

    def test_bash_with_backslashes_fires(self):
        cmd = f"rm {str(self.venue)}\\Assets\\x.png"
        self.assertIsNotNone(self.fire("Bash", {"command": cmd}, session="b2"))

    def test_bash_workspace_relative_path_fires(self):
        """`cp a.png MyVenue/Assets/x.png` from the workspace root carries no absolute path and is
        the commonest shape there is."""
        self.assertIsNotNone(self.fire("Bash", {"command": "cp a.png MyVenue/Assets/x.png"}, session="b4"))
        self.assertIsNotNone(self.fire("Bash", {"command": "cp a.png ./MyVenue/Assets/x.png"}, session="b6"))

    def test_bare_venue_name_without_a_separator_is_a_known_miss(self):
        """The segment guard requires a following path separator, so prose does not fire — and
        neither does `<vcs> -C MyVenue <subcommand>`, which IS a venue write. Pinned as a known
        miss rather than left to be rediscovered: loosening the guard to bare-name would fire on
        every sentence mentioning a venue. This is the net, not the fence."""
        self.assertIsNone(self.fire("Bash", {"command": "echo 'MyVenue is the venue'"}, session="b7"))

    def test_bash_not_naming_a_venue_is_silent(self):
        self.assertIsNone(self.fire("Bash", {"command": "git status"}, session="b3"))

    # --- the UnityMCP arm: mutators only ---

    def test_unity_mutator_fires_with_no_path(self):
        self.assertIsNotNone(self.fire("mcp__UnityMCP__manage_asset", {}, session="m1"))

    def test_non_kit_read_tools_are_silent(self):
        """Only the non-kit read tools stay silent. NOT "read-only doors stay silent" — every
        agent-tools/avatar-tools door is invoked through execute_code, so a pure read like
        CheckAvatar fires this hook. The leaf name carries no mutation information; that
        false-positive side was chosen over missing the main mutation path."""
        self.assertIsNone(self.fire("mcp__UnityMCP__find_gameobjects", {}, session="m2"))
        self.assertIsNone(self.fire("mcp__UnityMCP__unity_reflect", {}, session="m3"))

    def test_execute_code_fires_even_for_a_read_only_door(self):
        """Pins the known false positive, so nobody "fixes" it into missing real mutation."""
        body = {"code": "return Ryan6Vrc.AgentTools.Editor.CheckAvatar.Run();"}
        self.assertIsNotNone(self.fire("mcp__UnityMCP__execute_code", body, session="m4"))

    def test_manage_camera_fires(self):
        """It writes PNGs and their .meta into the venue's Assets/ — real undisclosed litter."""
        self.assertIsNotNone(
            self.fire("mcp__UnityMCP__manage_camera", {"action": "screenshot"}, session="m5")
        )

    # --- dedupe ---

    def test_fires_once_per_session(self):
        a = self.fire("Write", {"file_path": str(self.venue / "Assets" / "a.prefab")}, session="d")
        b = self.fire("Write", {"file_path": str(self.venue / "Assets" / "b.prefab")}, session="d")
        self.assertIsNotNone(a)
        self.assertIsNone(b)

    def test_subagent_gets_its_own_dump(self):
        """A parent's fire must not leave the subagent doing the venue work with nothing."""
        self.assertIsNotNone(self.fire("Write", {"file_path": str(self.venue / "Assets" / "a.prefab")}, session="d2"))
        self.assertIsNotNone(
            self.fire("Write", {"file_path": str(self.venue / "Assets" / "b.prefab")}, session="d2", agent="sub")
        )

    def test_stale_marker_dumps_again(self):
        """Compaction drops injected context but leaves the session id, so a never-expiring marker
        would run a long venue session permanently without the rules. 45 min, per the sibling hook."""
        self.fire("Write", {"file_path": str(self.venue / "Assets" / "a.prefab")}, session="stale")
        marker = self.markers / "claude-venue-write-hook" / "stale.marker"
        old = time.time() - 60 * 60
        os.utime(marker, (old, old))
        self.assertIsNotNone(self.fire("Write", {"file_path": str(self.venue / "Assets" / "b.prefab")}, session="stale"))

    # --- the heartbeat arm: the only one that reaches a venue outside the workspace ---

    def _heartbeat(self, name, project_path, age_seconds=0):
        d = self.home / ".unity-mcp"
        d.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
        (d / f"unity-mcp-status-{name}.json").write_text(json.dumps({
            "project_name": name, "unity_port": 6400,
            "project_path": project_path,
            "last_heartbeat": stamp.isoformat().replace("+00:00", "Z"),
        }), encoding="utf-8")

    def test_heartbeat_root_outside_the_workspace_fires(self):
        outside = self.temp / "Elsewhere" / "OtherVenue"
        (outside / "Assets").mkdir(parents=True)
        self._heartbeat("Other", outside.as_posix() + "/Assets")
        self.assertIsNotNone(
            self.fire("Bash", {"command": f"rm {outside.as_posix()}/Assets/x.png"}, session="h1")
        )

    def test_stale_heartbeat_is_not_a_root(self):
        outside = self.temp / "Gone" / "DeadVenue"
        (outside / "Assets").mkdir(parents=True)
        self._heartbeat("Dead", outside.as_posix() + "/Assets", age_seconds=9999)
        self.assertIsNone(
            self.fire("Bash", {"command": f"rm {outside.as_posix()}/Assets/x.png"}, session="h2")
        )

    def test_corrupt_heartbeat_drops_only_itself(self):
        """unity-instances-hook.sh's contract for the same files: a bad entry drops itself, never
        the whole table. A Unity crash mid-write is the trigger."""
        (self.home / ".unity-mcp").mkdir(exist_ok=True)
        (self.home / ".unity-mcp" / "unity-mcp-status-bad.json").write_text("{truncated", encoding="utf-8")
        outside = self.temp / "Live" / "LiveVenue"
        (outside / "Assets").mkdir(parents=True)
        self._heartbeat("Live", outside.as_posix() + "/Assets")
        self.assertIsNotNone(
            self.fire("Bash", {"command": f"rm {outside.as_posix()}/Assets/x.png"}, session="h3")
        )

    def test_venue_doc_fits_the_host_additional_context_cap(self):
        """The host truncates additionalContext at 8000 chars / 200 lines, silently. "Dump it whole"
        with a silently truncated dump is the exact failure this hook exists to prevent, so the real
        doc's size is asserted here rather than left to be discovered."""
        real = Path(__file__).resolve().parent.parent.parent / "docs" / "VENUE.md"
        text = real.read_text(encoding="utf-8")
        self.assertLess(len(text), 7000, "VENUE.md is approaching the 8000-char additionalContext cap")
        self.assertLess(len(text.splitlines()), 180, "VENUE.md is approaching the 200-line cap")

    # --- never block ---

    def test_missing_venue_doc_still_routes(self):
        (self.proj / "docs" / "VENUE.md").unlink()
        got = self.fire("Write", {"file_path": str(self.venue / "Assets" / "x.prefab")}, session="miss")
        self.assertIsNotNone(got)
        self.assertIn("VENUE.md", got)

    def test_garbage_payload_exits_clean(self):
        p = subprocess.run(
            [PWSH, "-NoProfile", "-File", str(HOOK)],
            input="not json at all", capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
