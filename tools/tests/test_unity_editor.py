# tools/tests/test_unity_editor.py
"""Resolve-UnityEditor picks a Unity.exe from a project's pinned version, and its whole
reason to exist is the registry branch — the Hub records custom install dirs there, and an
entry can be "manual":true, so the default path is a fallback and never the authority.

That branch cannot be proven on a machine whose registry entry and default path are the same
string (they are, on the author's box: a passing call is indistinguishable from the fallback).
Every case below therefore points $env:APPDATA at a temp dir holding a synthetic registry, and
the registry hits are deliberately at NON-default locations so only the registry can answer.

pwsh is required; without it the whole fixture skips rather than passing vacuously."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

RESOLVER = Path(__file__).resolve().parent.parent / "unity-editor.ps1"
PWSH = shutil.which("pwsh")

# A version installed nowhere, for the cases that must end in a refusal. The pinned
# 2022.3.22f1 is real at the default path on a provisioned machine, so using it here would
# let the fallback answer and the case would assert a refusal that never comes (measured).
ABSENT = "9999.1.1f1"


@unittest.skipUnless(PWSH, "pwsh not on PATH")
class ResolveUnityEditor(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="ue-"))
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)
        self.appdata = self.temp / "appdata"
        (self.appdata / "UnityHub").mkdir(parents=True)

    def project(self, version="2022.3.22f1", line=None):
        """A minimal Unity project: just the ProjectVersion.txt the resolver reads."""
        proj = self.temp / f"proj-{len(list(self.temp.glob('proj-*')))}"
        (proj / "ProjectSettings").mkdir(parents=True)
        body = line if line is not None else f"m_EditorVersion: {version}\n"
        (proj / "ProjectSettings" / "ProjectVersion.txt").write_text(body, encoding="utf-8")
        return proj

    def registry(self, payload):
        """payload=None writes no registry at all (the absent-registry case)."""
        reg = self.appdata / "UnityHub" / "editors-v2.json"
        if payload is None:
            if reg.exists():
                reg.unlink()
            return
        reg.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")

    def fake_editor(self, name):
        """A Unity.exe at a location the default-path fallback would never guess."""
        exe = self.temp / name / "Editor" / "Unity.exe"
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_text("", encoding="utf-8")
        return exe

    def resolve(self, proj):
        """Returns (ok, text): the resolved path, or the refusal message.

        Paths arrive through the ENVIRONMENT, never interpolated into the source: a single
        quote in a path (a %TEMP% under a name like O'Connor) would otherwise close the
        PowerShell literal early and break every case with a syntax error instead of a
        result. Args after -Command are appended to the command text rather than bound as
        parameters, so env is the clean seam here."""
        script = (
            "$ErrorActionPreference='Stop'; . $env:UE_RESOLVER; "
            "try { Resolve-UnityEditor $env:UE_PROJECT } "
            "catch { Write-Output ('THREW: ' + $_.Exception.Message) }"
        )
        p = subprocess.run(
            [PWSH, "-NoProfile", "-Command", script],
            capture_output=True, text=True,
            env={**os.environ, "APPDATA": str(self.appdata),
                 "UE_RESOLVER": str(RESOLVER), "UE_PROJECT": str(proj)},
        )
        self.assertEqual(p.returncode, 0, f"pwsh exited {p.returncode}: {p.stderr}")
        out = p.stdout.strip()
        return (not out.startswith("THREW: "), out)

    # --- the registry branch: the reason this function exists ---

    def test_registry_wins_at_a_non_default_location(self):
        exe = self.fake_editor("custom-install")
        self.registry({"schema_version": "2", "data": [
            {"version": "2022.3.22f1", "location": [str(exe)], "manual": True}]})
        ok, got = self.resolve(self.project())
        self.assertTrue(ok, got)
        self.assertEqual(Path(got), exe)

    def test_registry_location_may_be_a_bare_string(self):
        """Older Hub writes a string where the current schema has an array."""
        exe = self.fake_editor("string-form")
        self.registry({"data": [{"version": "2022.3.22f1", "location": str(exe)}]})
        ok, got = self.resolve(self.project())
        self.assertTrue(ok, got)
        self.assertEqual(Path(got), exe)

    def test_registry_entry_for_another_version_is_ignored(self):
        other = self.fake_editor("wrong-version")
        self.registry({"data": [{"version": "6000.0.1f1", "location": [str(other)]}]})
        ok, got = self.resolve(self.project(version=ABSENT))
        self.assertFalse(ok, f"resolved to {got} on a version mismatch")
        self.assertIn(ABSENT, got)

    def test_install_path_with_wildcard_characters_resolves(self):
        """Test-Path reads its argument as a wildcard pattern, so a real Unity.exe under a
        directory named e.g. '[LTS]' (legal on Windows) reports absent and the resolver would fall through to
        the default with the right editor sitting on disk. A custom install directory is
        precisely what the registry branch exists to find, so this is where it must hold."""
        exe = self.fake_editor("hub [LTS] 2022")
        self.registry({"data": [{"version": "2022.3.22f1", "location": [str(exe)]}]})
        ok, got = self.resolve(self.project())
        self.assertTrue(ok, got)
        self.assertEqual(Path(got), exe)

    def test_project_path_with_an_apostrophe_resolves(self):
        """Paths reach pwsh as arguments; an apostrophe must not terminate a string literal."""
        exe = self.fake_editor("o'connor-install")
        self.registry({"data": [{"version": "2022.3.22f1", "location": [str(exe)]}]})
        proj = self.temp / "Ryan O'Connor project"
        (proj / "ProjectSettings").mkdir(parents=True)
        (proj / "ProjectSettings" / "ProjectVersion.txt").write_text(
            "m_EditorVersion: 2022.3.22f1\n", encoding="utf-8")
        ok, got = self.resolve(proj)
        self.assertTrue(ok, got)
        self.assertEqual(Path(got), exe)

    # --- degradation: none of these may take the resolver down ---

    def test_readable_registry_with_no_matching_entry_is_still_named(self):
        """A registry can answer nothing while being perfectly readable. Naming only the
        default path would report it as never consulted, contradicting the refusal's own
        claim to list what was searched."""
        self.registry({"data": [{"version": "6000.0.1f1", "location": ["X:/nope/Unity.exe"]}]})
        ok, got = self.resolve(self.project(version=ABSENT))
        self.assertFalse(ok, got)
        self.assertIn("editors-v2.json", got)

    def test_empty_registry_file_is_named_and_not_fatal(self):
        """Get-Content -Raw on an empty file is $null, and `$null | ConvertFrom-Json` returns
        nothing WITHOUT throwing — so the catch never fires and the loop must tolerate it."""
        self.registry("")
        ok, got = self.resolve(self.project(version=ABSENT))
        self.assertFalse(ok, got)
        self.assertIn("editors-v2.json", got)

    def test_corrupt_registry_falls_through_and_names_itself(self):
        self.registry("{ not json at all")
        ok, got = self.resolve(self.project(version=ABSENT))
        self.assertFalse(ok, got)
        self.assertIn("editors-v2.json", got)
        self.assertIn("unreadable", got)

    def test_absent_registry_is_named_not_fatal(self):
        self.registry(None)
        ok, got = self.resolve(self.project(version=ABSENT))
        self.assertFalse(ok, got)
        self.assertIn("absent", got)

    def test_null_location_entry_does_not_derail_the_scan(self):
        """A malformed entry must not stop a good one later in the list."""
        exe = self.fake_editor("after-the-bad-entry")
        self.registry({"data": [
            {"version": "2022.3.22f1", "location": None},
            {"version": "2022.3.22f1", "location": [str(exe)]},
        ]})
        ok, got = self.resolve(self.project())
        self.assertTrue(ok, got)
        self.assertEqual(Path(got), exe)

    def test_registry_entry_pointing_at_a_dead_path_keeps_searching(self):
        self.registry({"data": [
            {"version": ABSENT, "location": [str(self.temp / "gone" / "Unity.exe")]}]})
        ok, got = self.resolve(self.project(version=ABSENT))
        self.assertFalse(ok, got)
        self.assertIn("Searched:", got)

    # --- the project side ---

    def test_missing_project_version_file_names_the_project(self):
        proj = self.temp / "not-a-project"
        proj.mkdir()
        ok, got = self.resolve(proj)
        self.assertFalse(ok, got)
        self.assertIn("ProjectVersion.txt", got)

    def test_project_version_without_the_version_line_refuses_cleanly(self):
        """The naive `.Matches.Groups[1]` form throws 'Cannot index into a null array'
        here instead, which is why the resolver tests the match before indexing it."""
        ok, got = self.resolve(self.project(line="m_EditorVersionWithRevision: x (abc)\n"))
        self.assertFalse(ok, got)
        self.assertIn("m_EditorVersion", got)
        self.assertNotIn("null array", got)


if __name__ == "__main__":
    unittest.main()
