# tools/tests/test_sync_tool_inventory.py
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync_tool_inventory as s  # noqa: E402

WORKSPACE = Path(__file__).resolve().parent.parent.parent


def needs_sibling(name):
    """The tool surfaces are gitignored sibling repos, absent from every linked worktree —
    which is where most work here happens. These tests used to ERROR there, leaving the suite
    permanently red in a worktree and making any genuine new failure indistinguishable from
    the inherited four. Skip instead, and let the skip count carry the honest signal."""
    return unittest.skipUnless(
        (WORKSPACE / name).is_dir(),
        f'{name} absent (linked worktree) — live-surface test skipped, not passed')


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

    @needs_sibling("vrc-unity-tools")
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

    @needs_sibling("vrc-blender-tools")
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
    @needs_sibling("vrc-skills")
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

    def _row(self, key: str, linked_key: str = None) -> str:
        """A skills row, key cell linked to SKILL_URL — of `linked_key` when given, to
        fabricate a stale link."""
        return f"| [`{key}`]({s.SKILL_URL.format(key=linked_key or key)}) | purpose |\n"

    def test_parses_only_the_skills_section(self):
        # The key comes out of the link wrapper; the Tools table (unlinked, and outside
        # the section) is not read as a skills row.
        body = ("# Repo\n\nintro\n\n## Skills\n\nprose\n\n| Key | Purpose |\n| --- | --- |\n"
                + self._row("own-base") + self._row("author-menu") + "\n"
                "## Tools\n\n| Key | Purpose |\n| --- | --- |\n| `CopyComponents` | x |\n")
        self.assertEqual(s.parse_readme_skills(self._readme(body)), {"own-base", "author-menu"})

    def test_unlinked_row_raises_as_a_formatting_error(self):
        # A cell that is not a plain link (bare key, or a styled/typo'd link) is named as
        # such: the key is then the whole raw cell, so the "must link to" message would
        # demand a URL with the broken cell embedded in it.
        body = "# Repo\n\n## Skills\n\n| Key | Purpose |\n| --- | --- |\n| `own-base` | z |\n"
        with self.assertRaisesRegex(s.InventoryError, "not a plain markdown link"):
            s.parse_readme_skills(self._readme(body))

    def test_link_to_another_skill_raises(self):
        # A copy-pasted row, or a renamed skill whose link went unupdated, fails loud
        # instead of shipping a 404 in the public README.
        body = ("# Repo\n\n## Skills\n\n| Key | Purpose |\n| --- | --- |\n"
                + self._row("own-base", linked_key="own-mergeable"))
        with self.assertRaises(s.InventoryError):
            s.parse_readme_skills(self._readme(body))

    def test_missing_section_raises(self):
        with self.assertRaises(s.InventoryError):
            s.parse_readme_skills(self._readme("# Repo\n\n## Tools\n\n| K |\n| - |\n| x |\n"))

    def test_empty_section_raises(self):
        with self.assertRaises(s.InventoryError):
            s.parse_readme_skills(self._readme("# Repo\n\n## Skills\n\nprose only\n\n## Next\n"))

    @needs_sibling("vrc-skills")
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


class TestBlankOut(unittest.TestCase):
    """Every case here is a shape live in vrc-unity-tools that broke a real scanner.
    blank_out must preserve length and newlines, so offsets stay usable."""

    def _blanked(self, src):
        out = s.blank_out(src)
        self.assertEqual(len(out), len(src))
        self.assertEqual(out.count("\n"), src.count("\n"))
        return out

    def test_char_literal_holding_a_quote(self):
        # AnimatorSchemaYaml.cs:199 — `c0 == '"'`. A scanner tracking " but not '…'
        # enters string mode here and eats the rest of the file.
        out = self._blanked("if (c0 == '\"') { }\npublic static string A(){}\n")
        self.assertIn("public static string A(", out)
        self.assertEqual(out.count("{"), 2)

    def test_escaped_quote_and_backslash_char_literals(self):
        out = self._blanked("x('\\''); y('\\\\'); {\n")
        self.assertEqual(out.count("{"), 1)

    def test_line_comment_with_odd_quote_count(self):
        # CheckAnimator.cs:648 — a // comment carrying three quotes.
        out = self._blanked('// bindings all hit \\"\\")\npublic static string B(){}\n')
        self.assertIn("public static string B(", out)

    def test_block_comment_opener_inside_line_comment(self):
        # ControllerFixpoint.cs:41 — `// built/*_Parameters.asset`; a scanner that scans
        # for /* first swallows to the next */ dozens of lines later.
        out = self._blanked("// built/*_Parameters\npublic static string C(){}\n")
        self.assertIn("public static string C(", out)

    def test_double_slash_inside_a_string(self):
        # UploadAvatarLogic.cs:11 — @"https?://\S+"
        out = self._blanked('var r = @"https?://\\S+";\npublic static string D(){}\n')
        self.assertIn("public static string D(", out)

    def test_braces_inside_verbatim_and_plain_strings(self):
        # ControllerRules.cs:122 and UploadAvatar.cs's TrimEnd('}') — an unbalanced brace
        # in a literal closed the class ~280 lines early and hid three doors.
        out = self._blanked('a(@"\\{fileID\\}"); b("{"); c(\'}\');\n')
        self.assertEqual(out.count("{"), 0)
        self.assertEqual(out.count("}"), 0)

    def test_nul_byte_source_is_read(self):
        # ReportConsole.cs carries raw NUL bytes; rg/grep/git grep call it binary and skip
        # it silently, which would drop a five-door class from the census.
        out = self._blanked('var s = "a\x00b";\npublic static string E(){}\n')
        self.assertIn("public static string E(", out)


class TestDoorExtraction(unittest.TestCase):
    def _repo(self, body: str) -> Path:
        d = Path(tempfile.mkdtemp())
        p = d / "packages/x/Editor/T.cs"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        return d

    def test_string_returns_are_doors_other_returns_are_not(self):
        doors, statics = s.extract_unity_doors(self._repo(
            "[AgentTool]\npublic static class T {\n"
            "  public static string Run(string a) { return a; }\n"
            "  public static bool Helper() { return true; }\n}"))
        self.assertEqual(doors["T"], {"Run"})
        self.assertEqual(statics["T"], {"Run", "Helper"})

    def test_class_keyword_in_doc_comment_does_not_truncate(self):
        # CompileController.cs:51 — `/// (see class docs)`. This bug hid
        # CompileController.Compile and DecompileController.Decompile from an earlier census.
        doors, _ = s.extract_unity_doors(self._repo(
            "[AgentTool]\npublic static class T {\n"
            "  /// <summary>see class docs</summary>\n"
            "  public static string Compile(string p) { return p; }\n}"))
        self.assertEqual(doors["T"], {"Compile"})

    def test_nested_type_members_are_not_the_tools_doors(self):
        # UploadAvatar.UploadOutcome.Uploaded is not UploadAvatar.Uploaded.
        doors, statics = s.extract_unity_doors(self._repo(
            "[AgentTool]\npublic static class T {\n"
            "  public struct Out { public static string Made() { return null; } }\n"
            "  public static string Run() { return null; }\n}"))
        self.assertEqual(doors["T"], {"Run"})
        self.assertNotIn("Made", statics["T"])

    def test_readonly_field_and_expression_bodied_property_are_not_methods(self):
        doors, statics = s.extract_unity_doors(self._repo(
            "[AgentTool]\npublic static class T {\n"
            "  public static readonly string Dir = Make(\"x\");\n"
            "  public static string StatusPath => Dir + \"/s.json\";\n"
            "  public static string Run() { return null; }\n}"))
        self.assertEqual(statics["T"], {"Run"})
        self.assertEqual(doors["T"], {"Run"})

    def test_tuple_async_and_overloaded_signatures(self):
        doors, statics = s.extract_unity_doors(self._repo(
            "[AgentTool]\npublic static class T {\n"
            "  public static (string a, string b) Classify(object o) { return (null, null); }\n"
            "  public static async System.Threading.Tasks.Task<int> RunCore() { return 0; }\n"
            "  public static string Run(int a) { return null; }\n"
            "  public static string Run(string a) { return null; }\n}"))
        self.assertEqual(statics["T"], {"Classify", "RunCore", "Run"})
        self.assertEqual(doors["T"], {"Run"})          # tuple/Task returns are not doors

    def test_exception_tables_apply(self):
        repo = self._repo(
            "[AgentTool]\npublic static class ReportConsole {\n"
            "  public static string Report() { return null; }\n"
            "  public static string BenignLabel() { return null; }\n}")
        doors, _ = s.extract_unity_doors(repo)
        self.assertEqual(doors["ReportConsole"], {"Report"})


class TestCheckDoors(unittest.TestCase):
    def _tree(self, cs: str, docs: dict) -> tuple:
        code = Path(tempfile.mkdtemp())
        p = code / "vrc-unity-tools/packages/x/Editor/T.cs"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cs, encoding="utf-8")
        d = Path(tempfile.mkdtemp())
        (d / "docs").mkdir()
        for name, body in docs.items():
            (d / "docs" / name).write_text(body, encoding="utf-8")
        return code, d

    CS = ("[AgentTool]\npublic static class T {\n"
          "  public static string Run(string a) { return a; }\n}")

    def test_undocumented_door_is_a_finding(self):
        problems, census = s.check_doors(*self._tree(self.CS, {"a.md": "T does things.\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("T.Run", problems[0])
        self.assertIn("0/1", census)

    def test_bare_call_satisfies_coverage(self):
        problems, census = s.check_doors(*self._tree(self.CS, {"a.md": "`T.Run(a)` does it.\n"}))
        self.assertEqual(problems, [])
        self.assertIn("1/1", census)

    def test_fully_qualified_call_satisfies_coverage(self):
        # unity-tools.md prescribes the qualified form; a matcher without the optional
        # namespace prefix would report every landed call as missing.
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`Ryan6Vrc.AgentTools.Editor.T.Run(a)`\n"}))
        self.assertEqual(problems, [])

    def test_call_in_any_governed_doc_counts(self):
        # RenderThumbnailPlay.Begin is documented in emulator.md, not the contract pair.
        problems, _ = s.check_doors(*self._tree(self.CS, {"a.md": "x\n", "emulator.md": "`T.Run(a)`\n"}))
        self.assertEqual(problems, [])

    def test_call_naming_no_such_method_is_a_finding(self):
        problems, _ = s.check_doors(*self._tree(self.CS, {"a.md": "`T.Run(a)` and `T.Gone(x)`\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("T.Gone", problems[0])
        self.assertIn("names no public static", problems[0])

    def test_non_tool_host_is_not_resolved(self):
        # ArmatureLinkService.GetLinks( / Assembly.GetType( are live in the real docs.
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)`, `ArmatureLinkService.GetLinks()`\n"}))
        self.assertEqual(problems, [])

    def test_prefix_class_is_not_credited(self):
        cs = ("[AgentTool]\npublic static class T {\n"
              "  public static string Run() { return null; }\n}\n"
              "[AgentTool]\npublic static class TPlay {\n"
              "  public static string Shoot() { return null; }\n}")
        problems, _ = s.check_doors(*self._tree(cs, {"a.md": "`TPlay.Shoot()`\n"}))
        self.assertEqual([p for p in problems if p.startswith("T.Run")], problems)
        self.assertEqual(len(problems), 1)

    def test_missing_code_root_is_structural(self):
        _, docs = self._tree(self.CS, {"a.md": "x\n"})
        with self.assertRaises(s.InventoryError):
            s.check_doors(Path(tempfile.mkdtemp()), docs)

    def _workspace(self, door_documented: bool) -> Path:
        """A whole miniature workspace: three sibling surfaces, TOOLS.md, README.md, docs/."""
        w = Path(tempfile.mkdtemp())
        (w / "vrc-unity-tools/packages/x/Editor").mkdir(parents=True)
        (w / "vrc-unity-tools/packages/x/Editor/Foo.cs").write_text(
            "[AgentTool]\npublic static class Foo {\n"
            "  public static string Run(string a) { return a; }\n}", encoding="utf-8")
        (w / "vrc-blender-tools/avatarprep").mkdir(parents=True)
        (w / "vrc-blender-tools/avatarprep/ops.py").write_text(
            "bl_idname = 'avatarprep.do_thing'\n", encoding="utf-8")
        (w / "vrc-blender-tools/cli").mkdir(parents=True)
        (w / "vrc-blender-tools/cli/run_thing.py").write_text("", encoding="utf-8")
        (w / "vrc-skills/skills/sk").mkdir(parents=True)
        (w / "vrc-skills/skills/sk/SKILL.md").write_text(
            "---\nname: sk\ndescription: d\n---\n", encoding="utf-8")
        (w / "TOOLS.md").write_text(
            "Header.\n\n## vrc-unity-tools\n\n| Key | Purpose |\n| --- | --- |\n| `Foo` | f |\n\n"
            "## vrc-blender-tools\n\n| Key | Purpose |\n| --- | --- |\n"
            "| `do_thing` | d |\n| `run_thing` | r |\n", encoding="utf-8")
        (w / "README.md").write_text(
            "# R\n\n## Skills\n\n| Skill | What |\n| --- | --- |\n"
            "| [sk](https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/sk/SKILL.md) | s |\n",
            encoding="utf-8")
        (w / "docs").mkdir()
        (w / "docs/unity-tools.md").write_text(
            "`Foo.Run(a)` does it.\n" if door_documented else "Foo does it.\n", encoding="utf-8")
        return w

    def test_door_finding_does_not_suppress_the_readme_mirror(self):
        # The reason door findings live in their own list: gating inject() would stop the
        # public README tracking TOOLS.md for as long as one door row sat unwritten, and
        # since the hook only warns, nobody would see why.
        w = self._workspace(door_documented=False)
        rc = s.main(["--docs-root", str(w), "--code-root", str(w)])
        self.assertEqual(rc, 1)
        self.assertIn("Header.", (w / "README.md").read_text(encoding="utf-8"))

    def test_clean_workspace_returns_zero(self):
        w = self._workspace(door_documented=True)
        self.assertEqual(s.main(["--docs-root", str(w), "--code-root", str(w)]), 0)

    @needs_sibling("vrc-unity-tools")
    def test_live_docs_name_every_live_door(self):
        # The teeth: the hook only warns, so this is what actually catches the rot.
        # Report which module was imported — an editable install can resolve `s` to a
        # different checkout than the one under test (dispatched-work.md worktree trap).
        problems, census = s.check_doors(WORKSPACE, WORKSPACE)
        self.assertEqual(problems, [], f"{census} | tested module: {s.__file__}")


if __name__ == "__main__":
    unittest.main()
