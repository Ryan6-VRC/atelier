# tools/tests/test_serialized_read_hook.py
"""The hook's risk is entirely in path extraction, and the shapes it extracts from are
measured facts about the Claude Code tool payloads rather than a documented contract — so
they rot silently. Every payload below is the real recorded shape, not a plausible one; the
Grep content-mode case in particular carries an EMPTY filenames list, which is what makes
the naive implementation fire on nothing.

pwsh is required; without it the whole fixture skips rather than passing vacuously."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "serialized-read-hook.ps1"
PWSH = shutil.which("pwsh")


def event(tool, tool_input, tool_response, session="S", agent=None):
    ev = {
        "session_id": session,
        "hook_event_name": "PostToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "tool_response": tool_response,
    }
    if agent:
        ev["agent_id"] = agent
    return ev


@unittest.skipUnless(PWSH, "pwsh not on PATH")
class SerializedReadHook(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.mkdtemp(prefix="srh-")
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)

    def fire(self, ev):
        """Returns the injected text, or None when the hook stayed silent. A nonzero exit is
        itself a failure: this hook must never block a read."""
        p = subprocess.run(
            [PWSH, "-NoProfile", "-File", str(HOOK)],
            input=json.dumps(ev), capture_output=True, text=True,
            env={**dict(__import__("os").environ), "TEMP": self.temp, "TMP": self.temp},
        )
        self.assertEqual(p.returncode, 0, f"hook exited {p.returncode}: {p.stderr}")
        out = p.stdout.strip()
        if not out:
            return None
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]

    # --- the three extraction arms ---

    def test_read_arm_uses_file_path(self):
        msg = self.fire(event("Read", {"file_path": r"C:\p\A.prefab"},
                              {"type": "text", "file": {"filePath": r"C:\p\A.prefab",
                                                        "content": "x", "numLines": 1,
                                                        "startLine": 1, "totalLines": 1}}))
        self.assertIn("CheckAvatar", msg)

    def test_filenames_arm_covers_glob_and_files_with_matches(self):
        for resp in (
            {"mode": "files_with_matches", "filenames": [r"A\Fx.controller"],
             "numFiles": 1, "totalFiles": 1},
            {"filenames": [r"A\Fx.controller"], "numFiles": 1, "truncated": False},
        ):
            with self.subTest(resp=resp.get("mode", "glob")):
                self.setUp()
                self.assertIn("ReportController", self.fire(event("Grep", {"pattern": "D"}, resp)))

    def test_grep_content_mode_hides_paths_in_the_content_string(self):
        """filenames is empty here — the whole point. Both classes must be recognized."""
        msg = self.fire(event("Grep", {"pattern": "Damp", "output_mode": "content"},
                              {"mode": "content", "numFiles": 0, "filenames": [],
                               "content": "A\\Foo.prefab:12:  m_Weight: 0\n"
                                          "B\\Fx.controller:88:  m_Name: Damping",
                               "numLines": 2, "totalLines": 2}))
        self.assertIn("CheckAvatar", msg)
        self.assertIn("ReportController", msg)

    def test_grep_content_context_lines_use_a_dash_separator(self):
        msg = self.fire(event("Grep", {"pattern": "Damp", "output_mode": "content", "-C": 1},
                              {"mode": "content", "numFiles": 0, "filenames": [],
                               "content": "B\\Fx.controller-86-  foo", "numLines": 1,
                               "totalLines": 1}))
        self.assertIn("ReportController", msg)

    def test_a_dashed_path_segment_does_not_truncate_the_colon_form(self):
        """`Foo-2-x` satisfies the context-line pattern, so the colon form must win first."""
        msg = self.fire(event("Grep", {"pattern": "Damp", "output_mode": "content"},
                              {"mode": "content", "numFiles": 0, "filenames": [],
                               "content": "A\\Foo-2-x\\Fx.controller:88:  x", "numLines": 1,
                               "totalLines": 1}))
        self.assertIn("ReportController", msg)

    def test_single_file_grep_falls_back_to_the_input_path(self):
        """A grep already scoped to one file emits no path prefix at all."""
        msg = self.fire(event("Grep", {"pattern": "Damp", "path": "B/Fx.controller",
                                       "output_mode": "content"},
                              {"mode": "content", "numFiles": 0, "filenames": [],
                               "content": "88:  m_Name: Damping", "numLines": 1,
                               "totalLines": 1}))
        self.assertIn("ReportController", msg)

    def test_absolute_windows_path_survives_the_prefix_parse(self):
        """The drive letter's colon must not be read as the line-number separator."""
        msg = self.fire(event("Grep", {"pattern": "Damp", "output_mode": "content"},
                              {"mode": "content", "numFiles": 0, "filenames": [],
                               "content": r"C:\p\Assets\A.prefab:12:  x", "numLines": 1,
                               "totalLines": 1}))
        self.assertIn("CheckAvatar", msg)

    # --- classification ---

    def test_fbx_meta_routes_to_the_importer_door(self):
        msg = self.fire(event("Read", {"file_path": r"C:\p\Base.fbx.meta"},
                              {"type": "text", "file": {"filePath": r"C:\p\Base.fbx.meta",
                                                        "content": "x", "numLines": 1,
                                                        "startLine": 1, "totalLines": 1}}))
        self.assertIn("CheckHumanoidRig", msg)
        self.assertNotIn("CheckAvatar", msg)

    def test_unrelated_extensions_stay_silent(self):
        for path in (r"C:\p\Foo.cs", r"C:\p\README.md", r"C:\p\Foo.png.meta"):
            with self.subTest(path=path):
                self.setUp()
                self.assertIsNone(self.fire(event(
                    "Read", {"file_path": path},
                    {"type": "text", "file": {"filePath": path, "content": "x", "numLines": 1,
                                              "startLine": 1, "totalLines": 1}})))

    def test_a_bash_read_is_structurally_uncovered(self):
        """Pinned as a known hole, not an aspiration: Bash carries no result paths, so the
        commonest bypass cannot be closed here and docs/verify.md carries that load."""
        self.assertIsNone(self.fire(event("Bash", {"command": "rg Damp"},
                                          {"stdout": "B/Fx.controller:88:x", "stderr": "",
                                           "interrupted": False, "isImage": False})))

    def test_malformed_payloads_never_block(self):
        for ev in ({}, {"tool_response": None}, {"tool_response": {"filenames": []}}):
            with self.subTest(ev=ev):
                self.assertIsNone(self.fire(ev))

    # --- dedupe ---

    def test_dedupe_is_per_class_not_per_session(self):
        ctrl = {"mode": "files_with_matches", "filenames": [r"A\Fx.controller"],
                "numFiles": 1, "totalFiles": 1}
        prefab = {"mode": "files_with_matches", "filenames": [r"A\Foo.prefab"],
                  "numFiles": 1, "totalFiles": 1}
        self.assertIsNotNone(self.fire(event("Grep", {"pattern": "D"}, ctrl)))
        self.assertIsNone(self.fire(event("Grep", {"pattern": "D"}, ctrl)))
        # A spent fire on one class must not cover another — the defect per-session dedupe has.
        self.assertIsNotNone(self.fire(event("Grep", {"pattern": "D"}, prefab)))

    def test_a_subagent_gets_its_own_scope(self):
        ctrl = {"mode": "files_with_matches", "filenames": [r"A\Fx.controller"],
                "numFiles": 1, "totalFiles": 1}
        self.assertIsNotNone(self.fire(event("Grep", {"pattern": "D"}, ctrl)))
        self.assertIsNotNone(self.fire(event("Grep", {"pattern": "D"}, ctrl, agent="sub7")))


if __name__ == "__main__":
    unittest.main()
