# tools/tests/test_test_venue_common.py
"""Where a provisioned TestEditor's com.ryan6vrc.* packages come from, and the provisioning
refusal built on it.

The trap these close: setup-test-editor.ps1 bakes -ToolsRoot into the venue manifest as an
absolute path at provisioning time, then early-returns "already exists" + exit 0 on any later
call. A worktree worker who passes -ToolsRoot therefore gets a venue still pointing at the MAIN
checkout, and a green suite that says nothing about their own edits.

Every case builds a synthetic venue on disk rather than touching a real TestEditor: the cases
that matter are the DEGRADED ones (an embedded shadow, an unparseable ref, two roots at once),
and none of those exist in a healthy venue, so a fixture-free test could only ever assert the
happy path.

pwsh is required; without it the whole fixture skips rather than passing vacuously."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

COMMON = Path(__file__).resolve().parent.parent / "test-venue-common.ps1"
SETUP = Path(__file__).resolve().parent.parent / "setup-test-editor.ps1"
PWSH = shutil.which("pwsh")


class _VenueFixture:
    """Synthetic-venue helpers. Deliberately NOT a TestCase: the setup-refusal class below needs these
    builders, and inheriting a TestCase to get them would re-run every case in it under a second name."""

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="tvc-"))
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)

    def venue(self, manifest_deps=None, embedded=()):
        """A synthetic venue: Packages/manifest.json plus any embedded package folders."""
        venue = self.temp / f"venue-{len(list(self.temp.glob('venue-*')))}"
        (venue / "Packages").mkdir(parents=True)
        deps = manifest_deps if manifest_deps is not None else {}
        (venue / "Packages" / "manifest.json").write_text(
            json.dumps({"dependencies": deps}, indent=2), encoding="utf-8")
        for name in embedded:
            folder = venue / "Packages" / name
            folder.mkdir()
            (folder / "package.json").write_text(json.dumps({"name": name}), encoding="utf-8")
        return venue

    def run_ps(self, script):
        """Dot-source the common file, then run `script`. Returns stdout, stripped."""
        out = subprocess.run(
            [PWSH, "-NoProfile", "-NonInteractive", "-Command",
             f". '{COMMON}'; {script}"],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, f"pwsh failed: {out.stderr}")
        return out.stdout.strip()


@unittest.skipUnless(PWSH, "pwsh not on PATH")
class VenuePackageRoots(_VenueFixture, unittest.TestCase):
    def test_manifest_ref_yields_its_checkout_root(self):
        venue = self.venue({
            "com.ryan6vrc.agent-tools": "file:C:/work/vrc-unity-tools/packages/com.ryan6vrc.agent-tools",
            "com.ryan6vrc.avatar-tools": "file:C:/work/vrc-unity-tools/packages/com.ryan6vrc.avatar-tools",
            "com.vrchat.avatars": "1.0.0",
        })
        self.assertEqual(self.run_ps(f"Get-VenueToolsRoot '{venue}'"), "C:/work/vrc-unity-tools")

    def test_non_ryan6vrc_deps_are_not_read_as_a_root(self):
        """A venue whose only file: refs are other vendors has no tools root, not a wrong one."""
        venue = self.venue({"com.example.thing": "file:C:/elsewhere/packages/com.example.thing"})
        self.assertEqual(self.run_ps(f"'[' + (Get-VenueToolsRoot '{venue}') + ']'"), "[]")

    def test_two_checkouts_at_once_is_not_one_answer(self):
        """A venue left half-repointed by an interrupted run: naming either root would be a lie."""
        venue = self.venue({
            "com.ryan6vrc.agent-tools": "file:C:/work/vrc-unity-tools/packages/com.ryan6vrc.agent-tools",
            "com.ryan6vrc.avatar-tools": "file:C:/other/vrc-unity-tools/packages/com.ryan6vrc.avatar-tools",
        })
        self.assertEqual(self.run_ps(f"'[' + (Get-VenueToolsRoot '{venue}') + ']'"), "[]")

    def test_embedded_copy_shadows_the_manifest_entry(self):
        """Unity loads Packages/<name>/ over the manifest ref, so the ref is NOT what compiled."""
        venue = self.venue(
            {"com.ryan6vrc.agent-tools": "file:C:/work/vrc-unity-tools/packages/com.ryan6vrc.agent-tools"},
            embedded=["com.ryan6vrc.agent-tools"])
        roots = self.run_ps(
            f"(Get-VenueToolPackageRoots '{venue}' | ForEach-Object {{ $_.Package + '=' + $_.Source }}) -join ';'")
        self.assertEqual(roots, "com.ryan6vrc.agent-tools=embedded")

    def test_embedded_folder_without_package_json_is_not_a_package(self):
        """Unity only auto-loads a folder carrying package.json; a bare dir must not shadow."""
        venue = self.venue(
            {"com.ryan6vrc.agent-tools": "file:C:/work/vrc-unity-tools/packages/com.ryan6vrc.agent-tools"})
        (venue / "Packages" / "com.ryan6vrc.agent-tools").mkdir()
        self.assertEqual(self.run_ps(f"Get-VenueToolsRoot '{venue}'"), "C:/work/vrc-unity-tools")

    def test_missing_packages_dir_is_empty_not_an_exception(self):
        venue = self.temp / "bare"
        venue.mkdir()
        self.assertEqual(self.run_ps(f"@(Get-VenueToolPackageRoots '{venue}').Count"), "0")

    def test_separator_spellings_compare_equal(self):
        """The baked ref is forward-slashed and Resolve-Path is backslashed; the guard compares them."""
        self.assertEqual(
            self.run_ps(r"(ConvertTo-ComparablePath 'C:\work\tools\') -eq "
                        r"(ConvertTo-ComparablePath 'C:/work/tools')"),
            "True")


@unittest.skipUnless(PWSH, "pwsh not on PATH")
class SetupRefusesAStalePointer(_VenueFixture, unittest.TestCase):
    """The early return is the whole trap: it must not exit 0 on a venue pointing elsewhere."""

    def run_setup(self, venue, tools_root):
        return subprocess.run(
            [PWSH, "-NoProfile", "-NonInteractive", "-File", str(SETUP),
             "-Dest", str(venue), "-ToolsRoot", str(tools_root),
             "-SourceProject", str(self._source_project())],
            capture_output=True, text=True, timeout=180)

    def _source_project(self):
        """Enough of a Unity project that setup gets past its own argument resolution."""
        proj = self.temp / "source"
        (proj / "Packages").mkdir(parents=True, exist_ok=True)
        (proj / "ProjectSettings").mkdir(parents=True, exist_ok=True)
        (proj / "Packages" / "manifest.json").write_text('{"dependencies":{}}', encoding="utf-8")
        return proj

    def _tools_root(self, name):
        root = self.temp / name
        (root / "packages" / "com.ryan6vrc.agent-tools").mkdir(parents=True)
        return root

    def test_mismatched_pointer_refuses_instead_of_exiting_green(self):
        wanted = self._tools_root("wanted-tools")
        venue = self.venue({
            "com.ryan6vrc.agent-tools":
                "file:C:/main-checkout/vrc-unity-tools/packages/com.ryan6vrc.agent-tools"})
        out = self.run_setup(venue, wanted)
        self.assertNotEqual(out.returncode, 0, "a stale pointer must not exit 0")
        combined = out.stdout + out.stderr
        self.assertIn("C:/main-checkout/vrc-unity-tools", combined, "must name what it points at")
        self.assertIn(str(wanted), combined, "must name what was asked for")
        self.assertIn("-Sync", combined, "must name the remedy")

    def test_matching_pointer_is_the_ordinary_quiet_re_run(self):
        wanted = self._tools_root("wanted-tools")
        ref = "file:" + str(wanted).replace("\\", "/") + "/packages/com.ryan6vrc.agent-tools"
        venue = self.venue({"com.ryan6vrc.agent-tools": ref})
        out = self.run_setup(venue, wanted)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("already exists", out.stdout)

    def test_embedded_shadow_is_named_rather_than_reported_as_agreement(self):
        wanted = self._tools_root("wanted-tools")
        ref = "file:" + str(wanted).replace("\\", "/") + "/packages/com.ryan6vrc.agent-tools"
        venue = self.venue({"com.ryan6vrc.agent-tools": ref}, embedded=["com.ryan6vrc.agent-tools"])
        out = self.run_setup(venue, wanted)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("EMBEDDED", out.stdout)


if __name__ == "__main__":
    unittest.main()
