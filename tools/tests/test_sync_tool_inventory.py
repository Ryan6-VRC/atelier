# tools/tests/test_sync_tool_inventory.py
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync_tool_inventory as s  # noqa: E402

WORKSPACE = Path(__file__).resolve().parent.parent.parent


class TestUnityExtractor(unittest.TestCase):
    def _repo(self, files: dict) -> Path:
        d = Path(tempfile.mkdtemp())
        for rel, body in files.items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
        return d

    def test_tagged_class_name_is_the_key(self):
        repo = self._repo({"packages/x/Editor/Foo.cs":
                           "namespace N {\n  [AgentTool]\n  public class Foo : EditorWindow {}\n}"})
        self.assertEqual(s.extract_unity_keys(repo), {"Foo"})

    def test_untagged_class_is_ignored(self):
        repo = self._repo({"packages/x/Editor/Ping.cs":
                           "public class Ping { [MenuItem(\"Tools/Ping\")] static void P(){} }"})
        self.assertEqual(s.extract_unity_keys(repo), set())

    def test_agenttool_in_comment_is_ignored(self):
        repo = self._repo({"packages/x/Editor/Note.cs":
                           "// see the [AgentTool] attribute docs\npublic class Note {}"})
        self.assertEqual(s.extract_unity_keys(repo), set())

    def test_duplicate_type_name_raises(self):
        repo = self._repo({
            "packages/a/Editor/Foo.cs": "[AgentTool]\nclass Foo {}",
            "packages/b/Editor/Foo.cs": "[AgentTool]\nclass Foo {}",
        })
        with self.assertRaises(s.InventoryError):
            s.extract_unity_keys(repo)

    def test_live_surface_extraction(self):
        # The exact census is enforced by TOOLS.md + --check, not here: tool names
        # churn under refactors, so this smoke test only proves the extractor reads
        # the real tree — stable tools present, non-tools (stubs) absent, sane floor.
        keys = s.extract_unity_keys(WORKSPACE / "vrc-unity-tools")
        for expected in ("CopyComponents", "GraftHierarchy", "ReportPackage",
                         "CopyDescriptor", "MoveComponents"):
            self.assertIn(expected, keys)
        self.assertNotIn("Ping", keys)
        self.assertNotIn("AgentSelfTest", keys)
        self.assertGreaterEqual(len(keys), 12)

    def test_agenttool_on_non_class_fails_loud(self):
        # A misplaced [AgentTool] (on a struct/enum) must not silently bind a later class.
        repo = self._repo({"packages/x/Editor/S.cs": "[AgentTool]\npublic struct S { }"})
        with self.assertRaises(s.InventoryError):
            s.extract_unity_keys(repo)

    def test_missing_packages_dir_fails_loud(self):
        with self.assertRaises(s.InventoryError):
            s.extract_unity_keys(Path(tempfile.mkdtemp()))   # no packages/


class TestBlenderExtractor(unittest.TestCase):
    def _repo(self, files: dict) -> Path:
        d = Path(tempfile.mkdtemp())
        for rel, body in files.items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
        return d

    def test_live_surface_union_dedup(self):
        keys = s.extract_blender_keys(WORKSPACE / "vrc-blender-tools")
        self.assertIn("apply_pose", keys)   # operator == cli stem (one key)
        self.assertIn("import_fbx", keys)
        self.assertEqual(len(keys), 11)

    def test_operator_in_any_module_and_single_quote(self):
        # An operator declared outside operators.py is still found (glob), and a
        # single-quoted bl_idname is matched.
        repo = self._repo({
            "avatarprep/operators.py": 'class A:\n    bl_idname = "avatarprep.op_a"\n',
            "avatarprep/extra.py": "class B:\n    bl_idname = 'avatarprep.op_b'\n",
            "cli/op_a.py": "", "cli/only_cli.py": "",
        })
        self.assertEqual(s.extract_blender_keys(repo), {"op_a", "op_b", "only_cli"})

    def test_missing_avatarprep_dir_fails_loud(self):
        repo = self._repo({"cli/x.py": ""})   # no avatarprep/
        with self.assertRaises(s.InventoryError):
            s.extract_blender_keys(repo)


class TestSkillsExtractor(unittest.TestCase):
    def test_live_surface_names(self):
        # Smoke test only (mirrors the Unity extractor): skill names churn, so prove
        # the extractor reads the real tree — a few stable skills present + a sane
        # floor — not an exact census (that is enforced by TOOLS.md + --check).
        keys = s.extract_skills_keys(WORKSPACE / "vrc-skills")
        for expected in ("import-vendor-asset", "own-base", "reproportion",
                         "own-mergeable"):
            self.assertIn(expected, keys)
        self.assertGreaterEqual(len(keys), 8)


class TestParseAndCheck(unittest.TestCase):
    def _tools_md(self, body: str) -> Path:
        p = Path(tempfile.mkdtemp()) / "TOOLS.md"
        p.write_text(body, encoding="utf-8")
        return p

    CLEAN = (
        "# vrc-unity-tools\n\n| Key | Purpose |\n| --- | --- |\n| `CopyComponents` | x |\n\n"
        "# vrc-blender-tools\n\n| Key | Purpose |\n| --- | --- |\n| apply_recipe | y |\n"
    )

    def test_skips_header_and_delimiter_rows(self):
        keys = s.parse_tools_md(self._tools_md(self.CLEAN))
        self.assertEqual(keys["vrc-unity-tools"], {"CopyComponents"})
        self.assertEqual(keys["vrc-blender-tools"], {"apply_recipe"})

    def test_missing_section_raises(self):
        body = self.CLEAN.replace("# vrc-blender-tools\n\n| Key | Purpose |\n| --- | --- |\n| apply_recipe | y |\n", "")
        with self.assertRaises(s.InventoryError):
            s.parse_tools_md(self._tools_md(body))

    def test_marker_literals_forbidden(self):
        with self.assertRaises(s.InventoryError):
            s.parse_tools_md(self._tools_md(self.CLEAN + "\n" + s.BEGIN + "\n"))

    def test_check_reports_both_directions(self):
        code = {"vrc-unity-tools": {"CopyComponents", "CleanFX"},
                "vrc-blender-tools": set(), "vrc-skills": set()}
        doc = {"vrc-unity-tools": {"CopyComponents", "Ghost"},
               "vrc-blender-tools": set(), "vrc-skills": set()}
        problems = s.check(code, doc)
        self.assertTrue(any("CleanFX" in p and "undocumented" in p for p in problems))
        self.assertTrue(any("Ghost" in p and "phantom" in p for p in problems))


class TestReadmeSkills(unittest.TestCase):
    def _readme(self, body: str) -> Path:
        p = Path(tempfile.mkdtemp()) / "README.md"
        p.write_text(body, encoding="utf-8")
        return p

    def test_parses_only_the_skills_section(self):
        body = ("# Repo\n\nintro\n\n## Skills\n\nprose\n\n"
                "| Key | Purpose |\n| --- | --- |\n| `own-base` | z |\n| author-menu | m |\n\n"
                "## Tools\n\n| Key | Purpose |\n| --- | --- |\n| `CopyComponents` | x |\n")
        self.assertEqual(s.parse_readme_skills(self._readme(body)), {"own-base", "author-menu"})

    def test_missing_section_raises(self):
        with self.assertRaises(s.InventoryError):
            s.parse_readme_skills(self._readme("# Repo\n\n## Tools\n\n| K |\n| - |\n| x |\n"))

    def test_empty_section_raises(self):
        with self.assertRaises(s.InventoryError):
            s.parse_readme_skills(self._readme("# Repo\n\n## Skills\n\nprose only\n\n## Next\n"))

    def test_live_readme_matches_frontmatter(self):
        # The real README roster stays in lockstep with the plugin's skill names —
        # the check the hook runs, asserted here so a test run alone catches drift.
        readme = s.parse_readme_skills(WORKSPACE / "README.md")
        code = s.extract_skills_keys(WORKSPACE / "vrc-skills")
        self.assertEqual(readme, code)


class TestInject(unittest.TestCase):
    def _pair(self, readme: str, tools: str):
        d = Path(tempfile.mkdtemp())
        (d / "README.md").write_text(readme, encoding="utf-8")
        (d / "TOOLS.md").write_text(tools, encoding="utf-8")
        return d / "README.md", d / "TOOLS.md"

    def test_bootstrap_then_idempotent(self):
        rp, tp = self._pair("# Repo\n\nHello.\n", "# vrc-unity-tools\n\ntable\n")
        s.inject(rp, tp)
        first = rp.read_text(encoding="utf-8")
        self.assertIn("## Tools", first)
        self.assertIn(s.BEGIN, first)
        self.assertIn("table", first)
        s.inject(rp, tp)
        self.assertEqual(rp.read_text(encoding="utf-8"), first)

    def test_replaces_between_existing_markers(self):
        rp, tp = self._pair(f"# Repo\n\n{s.BEGIN}\nOLD\n{s.END}\n\ntail\n", "NEW-CONTENT\n")
        s.inject(rp, tp)
        out = rp.read_text(encoding="utf-8")
        self.assertIn("NEW-CONTENT", out)
        self.assertNotIn("OLD", out)
        self.assertIn("tail", out)

    def test_unbalanced_markers_raise(self):
        rp, tp = self._pair(f"# Repo\n{s.BEGIN}\nx\n", "y\n")
        with self.assertRaises(s.InventoryError):
            s.inject(rp, tp)

    def test_inject_returns_wrote_flag(self):
        # True on a real write, False when the block is already in sync (idempotent);
        # the hook stages README only on True.
        rp, tp = self._pair("# Repo\n", "content\n")
        self.assertTrue(s.inject(rp, tp))
        self.assertFalse(s.inject(rp, tp))


if __name__ == "__main__":
    unittest.main()
