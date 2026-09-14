# tools/tests/test_batch_mode_hook.py
"""The hook's contract is five arms keyed on one marker file. Each arm rests on a measured host
fact (updatedInput reaches the subagent; a Skill call fires PreToolUse with its args; a deny carries
its reason), none of which is a documented contract, so each is pinned here.

Every fixture points CLAUDE_PROJECT_DIR and TEMP at temp dirs, so a run never reads the real skill
or leaves a marker a live session could pick up. pwsh is required; without it the fixture skips."""
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "batch-mode-hook.ps1"
PWSH = shutil.which("pwsh")

SKILL_BODY = "# Batch venue work\n\nSKILL-SENTINEL — with an em-dash.\n"
RAILS_BODY = "--- Batch mode rails ---\n\nRAILS-SENTINEL — with an em-dash.\n"


@unittest.skipUnless(PWSH, "pwsh not on PATH")
class BatchModeHook(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="bmh-"))
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)
        self.proj = self.temp / "proj"
        self.skill = self.proj / ".claude" / "skills" / "batch-venue-work"
        self.skill.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text(SKILL_BODY, encoding="utf-8")
        (self.skill / "worker-rails.md").write_text(RAILS_BODY, encoding="utf-8")
        self.markers = self.temp / "markers"
        self.markers.mkdir()

    def fire(self, event, tool=None, tool_input=None, session="S", agent=None, extra=None):
        """Returns the parsed hookSpecificOutput, or None when the hook stayed silent. A nonzero
        exit is itself a failure: every path out of this hook exits 0."""
        ev = {"session_id": session, "hook_event_name": event}
        if tool:
            ev["tool_name"] = tool
            ev["tool_input"] = tool_input or {}
        if agent:
            ev["agent_id"] = agent
        if extra:
            ev.update(extra)
        env = {**os.environ, "TEMP": str(self.markers), "TMP": str(self.markers),
               "CLAUDE_PROJECT_DIR": str(self.proj)}
        p = subprocess.run([PWSH, "-NoProfile", "-File", str(HOOK)], input=json.dumps(ev),
                           capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(p.returncode, 0, f"hook must exit 0: {p.stderr}")
        if not p.stdout.strip():
            return None
        return json.loads(p.stdout)["hookSpecificOutput"]

    def on(self, session="S"):
        return self.fire("PreToolUse", "Skill", {"skill": "batch-venue-work", "args": ""}, session=session)

    def marker(self, session="S"):
        return self.markers / "claude-batch-mode" / f"{session}.marker"

    # --- the switch ---

    def test_invoking_the_skill_turns_the_mode_on(self):
        got = self.on()
        self.assertTrue(self.marker().exists())
        self.assertIn("ON", got["additionalContext"])

    def test_close_turns_it_off(self):
        self.on()
        got = self.fire("PreToolUse", "Skill", {"skill": "batch-venue-work", "args": "close"})
        self.assertFalse(self.marker().exists())
        self.assertIn("OFF", got["additionalContext"])

    def test_other_skills_are_silent_and_do_not_switch(self):
        self.assertIsNone(self.fire("PreToolUse", "Skill", {"skill": "compose-mergeable", "args": ""}))
        self.assertFalse(self.marker().exists())

    def test_plugin_prefixed_name_switches_too(self):
        self.fire("PreToolUse", "Skill", {"skill": "vrc-skills:batch-venue-work", "args": ""})
        self.assertTrue(self.marker().exists())

    def test_stale_marker_reads_as_off(self):
        self.on()
        old = time.time() - 13 * 3600
        os.utime(self.marker(), (old, old))
        self.assertIsNone(self.fire("UserPromptSubmit", extra={"prompt": "hi"}))
        self.assertFalse(self.marker().exists())

    # --- the Agent arm ---

    def test_agent_brief_gets_the_rails_appended(self):
        self.on()
        got = self.fire("PreToolUse", "Agent",
                        {"prompt": "Own the hat.", "subagent_type": "general-purpose", "model": "opus"})
        self.assertEqual(got["permissionDecision"], "allow")
        new = got["updatedInput"]
        self.assertTrue(new["prompt"].startswith("Own the hat."))
        # The rails are read as UTF-8 and re-emitted as UTF-8: the em-dash must round-trip.
        self.assertIn("RAILS-SENTINEL — with an em-dash.", new["prompt"])
        self.assertEqual(new["subagent_type"], "general-purpose")
        self.assertEqual(new["model"], "opus")

    def test_agent_brief_untouched_when_off(self):
        self.assertIsNone(self.fire("PreToolUse", "Agent", {"prompt": "Own the hat."}))

    def test_agent_brief_already_carrying_rails_is_left_alone(self):
        self.on()
        self.assertIsNone(self.fire("PreToolUse", "Agent",
                                    {"prompt": "x\n\n--- Batch mode rails ---\nRAILS-SENTINEL"}))

    def test_spawn_from_inside_a_subagent_gets_rails(self):
        self.on()
        got = self.fire("PreToolUse", "Agent", {"prompt": "nested"}, agent="A1")
        self.assertIn("RAILS-SENTINEL", got["updatedInput"]["prompt"])

    def test_missing_rails_file_still_routes(self):
        self.on()
        (self.skill / "worker-rails.md").unlink()
        got = self.fire("PreToolUse", "Agent", {"prompt": "x"})
        self.assertIn("worker-rails.md", got["updatedInput"]["prompt"])

    # --- the prose fence ---

    def test_markdown_write_is_denied_with_reason(self):
        self.on()
        got = self.fire("PreToolUse", "Write",
                        {"file_path": str(self.proj / "Venue" / "Assets" / "README.md")})
        self.assertEqual(got["permissionDecision"], "deny")
        self.assertIn("close", got["permissionDecisionReason"])

    def test_markdown_edit_and_notebook_are_denied(self):
        self.on()
        self.assertEqual(self.fire("PreToolUse", "Edit", {"file_path": "a/b.md"})["permissionDecision"], "deny")
        self.assertEqual(self.fire("PreToolUse", "NotebookEdit", {"notebook_path": "a/b.md"})["permissionDecision"], "deny")

    def test_non_markdown_write_is_silent(self):
        self.on()
        self.assertIsNone(self.fire("PreToolUse", "Write", {"file_path": "a/b.prefab"}))

    def test_markdown_write_allowed_when_off(self):
        self.assertIsNone(self.fire("PreToolUse", "Write", {"file_path": "a/b.md"}))

    def test_subagent_markdown_write_is_denied_too(self):
        self.on()
        got = self.fire("PreToolUse", "Write", {"file_path": "a/b.md"}, agent="A1")
        self.assertEqual(got["permissionDecision"], "deny")

    # --- the prompt line and the compaction dump ---

    def test_prompt_gets_the_dispatch_line(self):
        self.on()
        got = self.fire("UserPromptSubmit", extra={"prompt": "do the thing"})
        self.assertIn("named blocker", got["additionalContext"])
        self.assertIn("close", got["additionalContext"])

    def test_prompt_silent_when_off(self):
        self.assertIsNone(self.fire("UserPromptSubmit", extra={"prompt": "hi"}))

    def test_compaction_redumps_the_skill_whole(self):
        self.on()
        got = self.fire("SessionStart", extra={"source": "compact"})
        self.assertIn("SKILL-SENTINEL — with an em-dash.", got["additionalContext"])

    def test_sessions_do_not_share_a_marker(self):
        self.on(session="A")
        self.assertIsNone(self.fire("UserPromptSubmit", session="B", extra={"prompt": "hi"}))

    def test_garbage_payload_exits_clean(self):
        p = subprocess.run([PWSH, "-NoProfile", "-File", str(HOOK)], input="{not json",
                           capture_output=True, text=True,
                           env={**os.environ, "TEMP": str(self.markers)})
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
