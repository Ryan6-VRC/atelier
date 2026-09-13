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
import shutil
import subprocess
import tempfile
import unittest
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

    def test_bash_not_naming_a_venue_is_silent(self):
        self.assertIsNone(self.fire("Bash", {"command": "git status"}, session="b3"))

    # --- the UnityMCP arm: mutators only ---

    def test_unity_mutator_fires_with_no_path(self):
        self.assertIsNotNone(self.fire("mcp__UnityMCP__manage_asset", {}, session="m1"))

    def test_unity_read_only_door_is_silent(self):
        """Observing before changing (CLAUDE.md rule 1) must not cost a wall of rules."""
        self.assertIsNone(self.fire("mcp__UnityMCP__find_gameobjects", {}, session="m2"))
        self.assertIsNone(self.fire("mcp__UnityMCP__unity_reflect", {}, session="m3"))

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
