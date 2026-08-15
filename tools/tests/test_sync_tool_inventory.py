# tools/tests/test_sync_tool_inventory.py
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync_tool_inventory as s  # noqa: E402
from atelier_paths import resolve  # noqa: E402

WORKSPACE = Path(__file__).resolve().parent.parent.parent
MAIN, MAIN_FELL_BACK = resolve()   # code surfaces; WORKSPACE stays the docs-under-test side


def setUpModule():
    # A green run must name what it measured: assertion messages only print on failure, and
    # the trap is a green run that lied — an editable install can resolve `s` to a different
    # checkout than the one under test (dispatched-work.md worktree trap), and the live-
    # surface tests read a tree that is not this one.
    print(f'\ntest_sync_tool_inventory: code surfaces = {MAIN}'
          + (' (FALLBACK — main-checkout resolution failed)' if MAIN_FELL_BACK else ''))
    print(f'test_sync_tool_inventory: docs under test = {WORKSPACE} | module = {s.__file__}')


def needs_sibling(name):
    """The tool surfaces are gitignored sibling repos, present only in the main checkout —
    which atelier_paths resolves, so these tests run from any linked worktree too. A skip
    therefore means the main checkout itself lacks the sibling (an unbootstrapped clone,
    docs/bootstrap.md), and the skip count carries that signal instead of ERRORing the
    suite red."""
    return unittest.skipUnless(
        (MAIN / name).is_dir(),
        f'{name} absent from the main checkout ({MAIN}) — live-surface test skipped, not passed')


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
        keys = s.extract_unity_keys(MAIN / "vrc-unity-tools")
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
        # Smoke test only (mirrors the Unity and skills extractors): the exact census is
        # enforced by TOOLS.md + --check, not here. It was pinned exact here anyway, and
        # went red the first time vrc-blender-tools grew a door (rename_objects, #24).
        # A count never carried the dedup this test is named for: every operator
        # short-name is also a cli stem, so the union's size is the stem count either
        # way — apply_pose surviving as ONE key is the whole assertion.
        keys = s.extract_blender_keys(MAIN / "vrc-blender-tools")
        self.assertIn("apply_pose", keys)   # operator == cli stem (one key)
        self.assertIn("import_fbx", keys)
        self.assertGreaterEqual(len(keys), 11)

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
        keys = s.extract_skills_keys(MAIN / "vrc-skills")
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

    @unittest.skipUnless(MAIN == WORKSPACE, "main tree only — this README is branch-pinned, "
                         "vrc-skills' HEAD is not, so only the main tree can assert lockstep")
    @needs_sibling("vrc-skills")
    def test_live_readme_matches_frontmatter(self):
        # The real README roster stays in lockstep with the plugin's skill names — the check
        # the hook runs, asserted here so a main-tree test run alone catches drift. Main tree
        # only, deliberately: from a branch older than a roster change this red would clear
        # only by merging main into an unrelated PR, while the hook's --code-root run already
        # covers a worktree's README as a warning on every commit.
        readme = s.parse_readme_skills(WORKSPACE / "README.md")
        code = s.extract_skills_keys(MAIN / "vrc-skills")
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

    def test_interpolated_verbatim_in_either_order(self):
        # `$@"` and `@$"` are both legal and mean the same thing; only the verbatim rules
        # (no escapes, "" for a quote) keep a trailing backslash from eating the delimiter.
        for prefix in ('$@"', '@$"'):
            out = self._blanked(f'var s = {prefix}C:\\path\\{{x}}";\npublic static string F(){{}}\n')
            self.assertIn("public static string F(", out)
            self.assertEqual(out.count("{"), 1)

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
        doors, statics, _ = s.extract_unity_doors(self._repo(
            "[AgentTool]\npublic static class T {\n"
            "  public static string Run(string a) { return a; }\n"
            "  public static bool Helper() { return true; }\n}"))
        self.assertEqual(doors["T"], {"Run"})
        self.assertEqual(statics["T"], {"Run", "Helper"})

    def test_class_keyword_in_doc_comment_does_not_truncate(self):
        # CompileController.cs:51 — `/// (see class docs)`. This bug hid
        # CompileController.Run and DecompileController.Run from an earlier census.
        doors, _, _ = s.extract_unity_doors(self._repo(
            "[AgentTool]\npublic static class T {\n"
            "  /// <summary>see class docs</summary>\n"
            "  public static string Compile(string p) { return p; }\n}"))
        self.assertEqual(doors["T"], {"Compile"})

    def test_nested_type_members_are_not_the_tools_doors(self):
        # UploadAvatar.UploadOutcome.Uploaded is not UploadAvatar.Uploaded.
        doors, statics, _ = s.extract_unity_doors(self._repo(
            "[AgentTool]\npublic static class T {\n"
            "  public struct Out { public static string Made() { return null; } }\n"
            "  public static string Run() { return null; }\n}"))
        self.assertEqual(doors["T"], {"Run"})
        self.assertNotIn("Made", statics["T"])

    def test_readonly_field_and_expression_bodied_property_are_not_methods(self):
        doors, statics, _ = s.extract_unity_doors(self._repo(
            "[AgentTool]\npublic static class T {\n"
            "  public static readonly string Dir = Make(\"x\");\n"
            "  public static string StatusPath => Dir + \"/s.json\";\n"
            "  public static string Run() { return null; }\n}"))
        self.assertEqual(statics["T"], {"Run"})
        self.assertEqual(doors["T"], {"Run"})

    def test_tuple_async_and_overloaded_signatures(self):
        doors, statics, _ = s.extract_unity_doors(self._repo(
            "[AgentTool]\npublic static class T {\n"
            "  public static (string a, string b) Classify(object o) { return (null, null); }\n"
            "  public static async System.Threading.Tasks.Task<int> RunCore() { return 0; }\n"
            "  public static string Run(int a) { return null; }\n"
            "  public static string Run(string a) { return null; }\n}"))
        self.assertEqual(statics["T"], {"Classify", "RunCore", "Run"})
        self.assertEqual(doors["T"], {"Run"})          # tuple/Task returns are not doors

    def test_stale_doors_extra_entry_fails_loud(self):
        # NOT_DOORS rot surfaces on its own (the entry stops excluding, so the method turns
        # up as a new coverage finding). DOORS_EXTRA rot would silently delete a door, so it
        # is the table that needs the guard.
        repo = self._repo(
            "[AgentTool]\npublic static class CheckAvatar {\n"
            "  public static string Inspect() { return null; }\n}")
        with self.assertRaises(s.InventoryError):
            s.extract_unity_doors(repo)          # DOORS_EXTRA names CheckAvatar.ScanAnchorSeams

    def test_exception_tables_apply(self):
        repo = self._repo(
            "[AgentTool]\npublic static class ReportConsole {\n"
            "  public static string Report() { return null; }\n"
            "  public static string BenignLabel() { return null; }\n}")
        doors, _, _ = s.extract_unity_doors(repo)
        self.assertEqual(doors["ReportConsole"], {"Report"})


class TestCheckDoors(unittest.TestCase):
    def _tree(self, cs: str, docs: dict, tools_md: str = "") -> tuple:
        code = Path(tempfile.mkdtemp())
        p = code / "vrc-unity-tools/packages/x/Editor/T.cs"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cs, encoding="utf-8")
        d = Path(tempfile.mkdtemp())
        (d / "docs").mkdir()
        for name, body in docs.items():
            (d / "docs" / name).write_text(body, encoding="utf-8")
        # Written unconditionally, empty by default: `check_doors` reads TOOLS.md strictly, so
        # writing it only when a case supplies one would raise in every case that does not --
        # and the cheapest way out of that failure is to make the read tolerant, silently
        # reversing the decision that a missing TOOLS.md is a broken --docs-root.
        (d / "TOOLS.md").write_text(tools_md, encoding="utf-8")
        return code, d

    # A minimal keyed table under the Unity heading `_bare_door_rows` scopes to.
    ROWS = "## vrc-unity-tools\n\n| Key | Purpose |\n| --- | --- |\n| `T` | {} |\n"

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
        # RenderThumbnailPlay.Run is documented in emulator.md, not the contract pair.
        problems, _ = s.check_doors(*self._tree(self.CS, {"a.md": "x\n", "emulator.md": "`T.Run(a)`\n"}))
        self.assertEqual(problems, [])

    def test_call_naming_no_such_method_is_a_finding(self):
        problems, _ = s.check_doors(*self._tree(self.CS, {"a.md": "`T.Run(a)` and `T.Gone(x)`\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("T.Gone", problems[0])
        self.assertIn("names no public static", problems[0])

    def test_parenless_call_naming_no_such_method_is_a_finding(self):
        # The style R19's rename rotted 5 sites in, two of them in files the paren-only scan
        # had nothing to say about at all -- so an agent clearing every reported finding still
        # shipped the stale ones.
        problems, _ = s.check_doors(*self._tree(self.CS, {"a.md": "`T.Run(a)` and `T.Gone`\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("T.Gone", problems[0])
        self.assertIn("names no public static", problems[0])

    def test_parenless_call_does_not_satisfy_coverage(self):
        # Resolution reads a parenless mention; coverage must not. The missing-door message
        # prescribes the paste-able form, so crediting a mention would make the check's own
        # remedy unsatisfiable -- loosening while the diff reads as tightening.
        problems, census = s.check_doors(*self._tree(self.CS, {"a.md": "`T.Run` does it.\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("T.Run is a door with no literal call", problems[0])
        self.assertIn("0/1", census)

    def test_a_paren_on_the_next_line_is_not_a_call(self):
        # `\s*\(` would capture the paragraph break and credit coverage; `[ \t]*\(` does not.
        problems, census = s.check_doors(
            *self._tree(self.CS, {"a.md": "`T.Run`\n\n(See also the door roster.)\n"}))
        self.assertIn("0/1", census)
        self.assertTrue(any("no literal call" in p for p in problems))

    def test_a_space_before_the_arg_list_still_counts(self):
        problems, census = s.check_doors(*self._tree(self.CS, {"a.md": "`T.Run (a)`\n"}))
        self.assertEqual(problems, [])
        self.assertIn("1/1", census)

    def test_a_nested_member_path_is_not_a_call(self):
        # `UploadAvatar.UploadOutcome.Uploaded` is a shape `_depth1_body` exists to handle. An
        # optional arg list would otherwise read it as a call to `UploadAvatar.UploadOutcome`
        # and prescribe "fix the call or the doc", which fits nothing the author did.
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)` returns `T.Outcome.Ok`\n"}))
        self.assertEqual(problems, [])

    def test_a_call_at_the_end_of_a_sentence_is_still_checked(self):
        # The path guard keys on a dot followed by a word character, so sentence punctuation
        # after an unbackticked call does not buy silence.
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)` is the door. Never T.Gone.\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("T.Gone", problems[0])

    def test_file_reference_is_not_a_parenless_call(self):
        # The false red R19's finding declined the widening over. The uppercase-method guard
        # carries it, and carries more now that the arg list is optional.
        problems, _ = s.check_doors(
            *self._tree(self.CS, {"a.md": "`T.Run(a)`, declared in `T.cs (line 40)`\n"}))
        self.assertEqual(problems, [])

    def test_non_tool_host_is_not_resolved(self):
        # ArmatureLinkService.GetLinks( / Assembly.GetType( are live in the real docs.
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)`, `ArmatureLinkService.GetLinks()`\n"}))
        self.assertEqual(problems, [])

    def test_prefix_class_is_not_credited(self):
        cs = ("[AgentTool]\npublic static class T {\n"
              "  public static string Run() { return null; }\n}\n"
              "[AgentTool]\npublic static class TPlay {\n"
              "  public static string Run() { return null; }\n}")
        # Both doors are `Run` (every primary is), so the prefix is the only thing separating
        # `T` from `TPlay` — the case the guard actually has to survive.
        problems, _ = s.check_doors(*self._tree(cs, {"a.md": "`TPlay.Run()`\n"}))
        self.assertEqual([p for p in problems if p.startswith("T.Run")], problems)
        self.assertEqual(len(problems), 1)

    def test_stale_door_in_a_tools_md_row_is_a_finding(self):
        # Six rows in the system tool index taught deleted door names through R19's rename and
        # the gate stayed green: TOOLS.md is at the repo root, and the corpus globbed docs/.
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)`\n"}, tools_md=self.ROWS.format("`T.Gone` does it")))
        self.assertEqual(len(problems), 1)
        self.assertIn("T.Gone", problems[0])
        self.assertTrue(problems[0].startswith("TOOLS.md:"), problems[0])

    def test_a_door_named_only_in_a_tools_md_row_is_still_undocumented(self):
        # Same asymmetry the skills corpus has: routing rows are not the door roster.
        problems, census = s.check_doors(*self._tree(
            self.CS, {"a.md": "T does things.\n"}, tools_md=self.ROWS.format("`T.Run(a)` does it")))
        self.assertEqual(len(problems), 1)
        self.assertIn("no literal call", problems[0])
        self.assertIn("0/1", census)

    def test_a_bare_door_in_its_own_rows_cell_is_a_finding(self):
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)`\n"}, tools_md=self.ROWS.format("`Run` does it")))
        self.assertEqual(len(problems), 1)
        self.assertIn("`Run` is written bare in the T row", problems[0])
        self.assertIn("`T.Run`", problems[0])

    def test_a_bare_row_finding_does_not_name_an_owner_the_trigger_did_not_prove(self):
        # Every [AgentTool] class declares `Run`, so a row legitimately naming a sibling tool's
        # door bare trips this check too. The trigger proves the name resolves on THIS row's
        # class and nothing more, so the message offers that class rather than asserting it.
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)`\n"}, tools_md=self.ROWS.format("see `Run`")))
        self.assertEqual(len(problems), 1)
        self.assertIn("if this row's tool is the one meant", problems[0])
        self.assertNotIn("names a T door", problems[0])

    def test_one_bare_row_finding_per_issue_not_per_occurrence(self):
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)`\n"}, tools_md=self.ROWS.format("`Run`, and again `Run`")))
        self.assertEqual(len(problems), 1)

    def test_a_bare_token_that_is_not_a_member_of_its_row_class_is_clean(self):
        # The whole-file reading of this rule runs ~13 false to 3 true: these rows are thick
        # with Unity types, status values and sibling class names. Scoping the token to its own
        # row's class is what turns a guess about meaning into an assertion about state.
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)`\n"},
            tools_md=self.ROWS.format("takes a `Transform`; returns `PENDING`")))
        self.assertEqual(problems, [])

    def test_a_class_with_no_run_door_is_a_finding(self):
        # The rule's power is that it has no exceptions: the kit once ran two conventions at
        # once and agents generalized whichever they met first onto the other half.
        cs = ("[AgentTool]\npublic static class T {\n"
              "  public static string Report() { return null; }\n}")
        problems, _ = s.check_doors(*self._tree(cs, {"a.md": "`T.Report()`\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("declares no `Run` door", problems[0])

    def test_a_secondary_door_alongside_run_is_clean(self):
        cs = ("[AgentTool]\npublic static class T {\n"
              "  public static string Run() { return null; }\n"
              "  public static string CheckBare() { return null; }\n}")
        problems, _ = s.check_doors(
            *self._tree(cs, {"a.md": "`T.Run()` and `T.CheckBare()`\n"}))
        self.assertEqual(problems, [])

    NS_CS = ("namespace Ryan6Vrc.AvatarTools.Editor {\n[AgentTool]\npublic static class T {\n"
             "  public static string Run(string a) { return a; }\n}\n}")

    def test_wrong_kit_in_a_qualified_call_is_a_finding(self):
        # unity.md calls the AgentTools/AvatarTools split "the recurring stumble"; the
        # qualified form the docs prescribe is what makes a wrong one checkable.
        problems, _ = s.check_doors(*self._tree(
            self.NS_CS, {"a.md": "`Ryan6Vrc.AgentTools.Editor.T.Run(a)`\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("wrong kit", problems[0])

    def test_a_parenless_wrong_kit_call_is_still_a_finding(self):
        # `_call_re`'s namespace prefix swallows a parenless qualified ref and resolves it
        # clean, so a paren-only namespace arm would leave a shape that reads as checked.
        problems, _ = s.check_doors(*self._tree(
            self.NS_CS, {"a.md": "`T.Run(a)` — see `Ryan6Vrc.AgentTools.Editor.T.Run`\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("wrong kit", problems[0])

    def test_right_kit_in_a_qualified_call_is_clean(self):
        problems, _ = s.check_doors(*self._tree(
            self.NS_CS, {"a.md": "`Ryan6Vrc.AvatarTools.Editor.T.Run(a)`\n"}))
        self.assertEqual(problems, [])

    def test_qualified_call_on_an_unknown_class_is_a_finding(self):
        problems, _ = s.check_doors(*self._tree(
            self.NS_CS, {"a.md": "`Ryan6Vrc.AvatarTools.Editor.T.Run(a)` and "
                                 "`Ryan6Vrc.AvatarTools.Editor.Typo.Run(a)`\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("no [AgentTool] class", problems[0])

    def test_source_file_reference_is_not_a_call(self):
        # `CheckSeam.cs (line 40)` is a shape the docs already use; a method group that
        # accepted lowercase would report it as a call to a method named `cs`.
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)`; see `T.cs (line 40)` for the constants.\n"}))
        self.assertEqual(problems, [])

    def test_one_finding_per_issue_not_per_occurrence(self):
        problems, _ = s.check_doors(*self._tree(
            self.CS, {"a.md": "`T.Run(a)` `T.Gone(x)` `T.Gone(y)` `T.Gone(z)`\n"}))
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
        # The teeth: the hook only warns, so this is what actually catches the rot — which
        # means it has to run in a worktree, where most commits here are made and where the
        # gitignored siblings are absent. Docs come from THIS tree, code from the main
        # checkout, which is what the two roots are for (setUpModule names both).
        problems, census = s.check_doors(MAIN, WORKSPACE)
        self.assertEqual(problems, [], census)


class TestSkillLiterals(unittest.TestCase):
    """The resolution scan reaches `vrc-skills` skill bodies; the coverage scan does not."""

    CS = ("[AgentTool]\npublic static class T {\n"
          "  public static string Run(string a) { return a; }\n}")

    def _tree(self, docs: dict, skills: dict = None, cs: str = None):
        code = Path(tempfile.mkdtemp())
        p = code / "vrc-unity-tools/packages/x/Editor/T.cs"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cs or self.CS, encoding="utf-8")
        for name, body in (skills or {}).items():
            sp = code / "vrc-skills/skills" / name / "SKILL.md"
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(body, encoding="utf-8")
        d = Path(tempfile.mkdtemp())
        (d / "docs").mkdir()
        for name, body in docs.items():
            (d / "docs" / name).write_text(body, encoding="utf-8")
        (d / "TOOLS.md").write_text("", encoding="utf-8")   # strict read; see TestCheckDoors._tree
        return code, d

    def test_a_broken_skill_literal_is_a_finding_naming_the_owning_repo(self):
        problems, _ = s.check_doors(*self._tree(
            {"a.md": "`T.Run(a)`\n"}, {"s": "call `T.Nope(a)` here\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("T.Nope", problems[0])
        # code_root-relative, and it says where the fix lands: this is the first finding
        # this check emits that an Atelier committer cannot clear in their own commit.
        self.assertIn("vrc-skills/skills/s/SKILL.md", problems[0])
        self.assertIn("fix in `vrc-skills`", problems[0])

    def test_the_wrong_kit_arm_reaches_skills_too(self):
        cs = ("namespace Ryan6Vrc.AvatarTools.Editor {\n[AgentTool]\n"
              "public static class T {\n"
              "  public static string Run(string a) { return a; }\n}\n}")
        problems, _ = s.check_doors(*self._tree(
            {"a.md": "`Ryan6Vrc.AvatarTools.Editor.T.Run(a)`\n"},
            {"s": "`Ryan6Vrc.AgentTools.Editor.T.Run(a)`\n"}, cs=cs))
        self.assertEqual(len(problems), 1)
        self.assertIn("wrong kit", problems[0])
        self.assertIn("vrc-skills/skills/s/SKILL.md", problems[0])

    def test_a_door_named_only_in_a_skill_is_still_undocumented(self):
        """The load-bearing asymmetry. Feeding the skills corpus into the coverage
        accumulator would let this door read as covered and delete its finding — the check
        silently LOOSENING while the diff looks like it tightened."""
        problems, census = s.check_doors(*self._tree(
            {"a.md": "T does things.\n"}, {"s": "call `T.Run(a)` here\n"}))
        self.assertEqual(len(problems), 1)
        self.assertIn("no literal call under docs/", problems[0])
        self.assertIn("0/1", census)

    def test_a_resolving_skill_literal_is_silent(self):
        problems, _ = s.check_doors(*self._tree(
            {"a.md": "`T.Run(a)`\n"}, {"s": "call `T.Run(a)` here\n"}))
        self.assertEqual(problems, [])

    def test_vendor_api_literals_in_skills_are_ignored(self):
        """Roughly 7 of the 18 dotted literals across the skills name vendor APIs
        (`AssetDatabase.ImportAsset`, `PrefabUtility.GetRemovedGameObjects`,
        `ModularAvatarMenuItem.InitSettings`). No door census can adjudicate them, and
        flagging them would be the false red that makes a check get switched off."""
        problems, _ = s.check_doors(*self._tree({"a.md": "`T.Run(a)`\n"}, {"s": (
            "`AssetDatabase.ImportAsset(p)` and `PrefabUtility.GetRemovedGameObjects(g)` "
            "and `ModularAvatarMenuItem.InitSettings(x)`\n")}))
        self.assertEqual(problems, [])

    def test_a_missing_vrc_skills_sibling_is_skipped_not_an_error(self):
        """`--code-root` legitimately points at a tree without the siblings. Requiring the
        directory would turn that into exit 2, which the hook prints as "README was not
        checked" — suppressing the mirror over a check that was never the point."""
        code, docs = self._tree({"a.md": "`T.Run(a)`\n"})
        self.assertEqual(s._skill_bodies(code), [])
        problems, _ = s.check_doors(code, docs)
        self.assertEqual(problems, [])

    def test_skill_paths_survive_diverging_roots(self):
        """docs_root and code_root diverge in a worktree by design. A skill path is under
        code_root, so computing it against docs_root raises ValueError — an uncaught
        traceback, not even the InventoryError exit-2 arm."""
        code, docs = self._tree({"a.md": "`T.Run(a)`\n"}, {"s": "call `T.Nope(a)`\n"})
        self.assertNotEqual(code, docs)
        problems, _ = s.check_doors(code, docs)   # must not raise
        self.assertTrue(any("vrc-skills" in p for p in problems))


class TestLiveSkillLiterals(unittest.TestCase):
    @needs_sibling("vrc-skills")
    def test_live_skill_literals_all_resolve(self):
        """The premise this check was built on, pinned: every kit literal in the shipped
        skills resolves today. This is the check's only current job — it has caught no
        drift, and is a lagging detector besides (a door rename lands in vrc-unity-tools,
        whose own commits never run the hook that carries it)."""
        bodies = s._skill_bodies(MAIN)
        self.assertTrue(bodies, "no skill bodies found — the scan would be vacuously clean")
        doors, statics, namespaces = s.extract_unity_doors(MAIN / "vrc-unity-tools")
        found = set()
        s._resolution_scan(
            [(p.relative_to(MAIN).as_posix(), s._read(p)) for p in bodies],
            statics, namespaces, found, fix_in="vrc-skills")
        self.assertEqual(sorted(found), [])


if __name__ == "__main__":
    unittest.main()
