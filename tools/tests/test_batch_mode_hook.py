# tools/tests/test_batch_mode_hook.py
"""The hook's contract is four arms keyed on one marker file. Each arm rests on a measured host
fact (updatedInput reaches the subagent; a Skill call fires PreToolUse with its args; a typed slash
command fires UserPromptSubmit with the raw text and no Skill event; a subagent's payload carries
its parent's session_id), measured headless and not documented. The tests here pin
the script's side of each; the host side is re-measured with a headless `claude -p` run.

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

    def test_close_is_the_first_word_not_any_word(self):
        self.on()
        got = self.fire("PreToolUse", "Skill", {"skill": "batch-venue-work", "args": "do a close review of these"})
        self.assertTrue(self.marker().exists())
        self.assertIn("still ON", got["additionalContext"])
        self.fire("PreToolUse", "Skill", {"skill": "batch-venue-work", "args": "  Close "})
        self.assertFalse(self.marker().exists())

    def test_close_with_trailing_instructions_turns_it_off(self):
        for args in ("close and review the menus first", "close, skip Somi", "CLOSE\nthen commit"):
            self.on()
            got = self.fire("PreToolUse", "Skill", {"skill": "batch-venue-work", "args": args})
            self.assertFalse(self.marker().exists(), args)
            self.assertIn("OFF", got["additionalContext"])

    def test_a_word_starting_with_close_opens(self):
        self.fire("PreToolUse", "Skill", {"skill": "batch-venue-work", "args": "closet outfits batch"})
        self.assertTrue(self.marker().exists())

    def test_first_arm_does_not_claim_already_on(self):
        got = self.on()
        self.assertNotIn("already", got["additionalContext"])

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
        self.assertNotIn("permissionDecision", got)  # a rewrite, never a permission bypass
        new = got["updatedInput"]
        self.assertTrue(new["prompt"].startswith("Own the hat."))
        # The rails are read as UTF-8 and re-emitted as UTF-8: the em-dash must round-trip.
        self.assertIn("RAILS-SENTINEL — with an em-dash.", new["prompt"])
        self.assertEqual(new["subagent_type"], "general-purpose")
        self.assertEqual(new["model"], "opus")

    def test_nested_input_fields_round_trip_intact(self):
        self.on()
        deep = {"prompt": "x", "run_in_background": True, "isolation": None,
                "tags": ["a", "b"], "opts": {"k": {"j": {"i": [1, {"z": False}]}}}}
        new = self.fire("PreToolUse", "Agent", deep)["updatedInput"]
        for k in ("run_in_background", "isolation", "tags", "opts"):
            self.assertEqual(new[k], deep[k], k)

    def test_agent_brief_untouched_when_off(self):
        self.assertIsNone(self.fire("PreToolUse", "Agent", {"prompt": "Own the hat."}))

    def test_agent_brief_already_carrying_rails_is_left_alone(self):
        self.on()
        self.assertIsNone(self.fire("PreToolUse", "Agent",
                                    {"prompt": "x\n\n--- Batch mode rails ---\nRAILS-SENTINEL"}))
        # Mentioning the rails is not carrying them.
        got = self.fire("PreToolUse", "Agent", {"prompt": "Find out why the Batch mode rails were missing."})
        self.assertIn("RAILS-SENTINEL", got["updatedInput"]["prompt"])

    def test_marker_is_keyed_on_session_not_agent(self):
        # The host fact this rests on (a subagent's hook payload carries its parent's session_id
        # plus its own agent_id) was measured headless, not here; this pins only that the hook
        # keys on the session and ignores agent_id, so that payload shape finds the marker.
        self.on()
        got = self.fire("PreToolUse", "Agent", {"prompt": "nested"}, agent="A1")
        self.assertIn("RAILS-SENTINEL", got["updatedInput"]["prompt"])

    def test_missing_rails_file_still_routes(self):
        self.on()
        (self.skill / "worker-rails.md").unlink()
        got = self.fire("PreToolUse", "Agent", {"prompt": "x"})
        self.assertIn("worker-rails.md", got["updatedInput"]["prompt"])

    # --- the prompt line and the compaction dump ---

    def test_prompt_gets_the_dispatch_line(self):
        self.on()
        got = self.fire("UserPromptSubmit", extra={"prompt": "do the thing"})
        self.assertIn("named blocker", got["additionalContext"])
        self.assertIn("close", got["additionalContext"])

    # --- the typed slash command: UserPromptSubmit carries the raw text and no Skill event fires ---

    def typed(self, prompt):
        got = self.fire("UserPromptSubmit", extra={"prompt": prompt})
        if got is not None:
            # A copy-pasted 'PreToolUse' here would pass every text assertion while the host discards it.
            self.assertEqual("UserPromptSubmit", got["hookEventName"])
        return got

    def test_typed_open_arms(self):
        got = self.typed("/batch-venue-work these six rows")
        self.assertTrue(self.marker().exists())
        self.assertIn("ON", got["additionalContext"])
        self.assertNotIn("already", got["additionalContext"])

    def test_typed_close_disarms(self):
        self.on()
        got = self.typed("/batch-venue-work close")
        self.assertFalse(self.marker().exists())
        self.assertIn("OFF", got["additionalContext"])

    def test_typed_close_followed_by_more_lines_disarms(self):
        self.on()
        got = self.typed("/batch-venue-work close\nthen commit the venue record")
        self.assertFalse(self.marker().exists())
        self.assertIn("OFF", got["additionalContext"])

    def test_typed_open_while_on_says_already_on(self):
        self.on()
        got = self.typed("/batch-venue-work colse")
        self.assertTrue(self.marker().exists())
        self.assertIn("already ON", got["additionalContext"])

    def test_mention_mid_sentence_is_not_the_switch(self):
        self.assertIsNone(self.typed("later run /batch-venue-work close for me"))
        self.assertFalse(self.marker().exists())
        self.on()
        got = self.typed("remind me how /batch-venue-work close works")
        self.assertTrue(self.marker().exists())
        self.assertIn("named blocker", got["additionalContext"])  # the ordinary age line, mode untouched

    def test_writes_are_never_blocked(self):
        self.on()
        self.assertIsNone(self.fire("PreToolUse", "Write", {"file_path": "a/README.md"}))

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
