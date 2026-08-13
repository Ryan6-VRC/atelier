# tools/tests/test_check_prose.py
#
# Run:  python -m unittest discover -s tools/tests -t tools/tests
# Not  `-t .` — this directory has no __init__.py, so the repo-root spelling dies with
# "Start directory is not importable".
#
# Nearly every test here builds a synthetic workspace and patches check_prose.ROOT at it,
# because the gate derives every path from its own __file__. That is also what makes this
# suite honest in a linked worktree: the vrc-* siblings are gitignored and therefore absent
# there, so any test that asserted against the live tree would either lie or skip. The few
# that do read the live tree say so and guard on SIBLINGS_PRESENT.
import contextlib
import inspect
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_prose as c  # noqa: E402

WORKSPACE = Path(__file__).resolve().parent.parent.parent
SIBLINGS_PRESENT = (WORKSPACE / 'vrc-skills' / 'tools' / 'validate_skills.py').is_file()
DOTGIT = ('file' if (WORKSPACE / '.git').is_file()
          else 'dir' if (WORKSPACE / '.git').is_dir() else 'absent')

CLEAN_MD = '# Title\n\nOne paragraph on one line.\n'
DRIFTED_MD = '# Title\n\nhard wrapped\nacross two lines.\n'   # reflow joins these


def setUpModule():
    # Which tree am I actually testing, and which guards were live? A worktree run and a
    # main-tree run differ by four skipped tests, and without this line the two artifacts
    # are indistinguishable — "green" and "green having checked nothing" read the same.
    print(f'\ntest_check_prose: module under test = {c.__file__}')
    print(f'test_check_prose: venue = {WORKSPACE} (.git is {DOTGIT}, '
          f'siblings_present={SIBLINGS_PRESENT})')


class TestVenueClassification(unittest.TestCase):
    """Always runs, everywhere. The live-surface tests below skip when the siblings are
    absent; a guard that rots into permanently-false would make a suite that checks nothing
    look exactly like a suite that passes."""

    def test_absent_siblings_are_explained_by_the_venue(self):
        # Not "which of two shapes is this" — a worktree with the siblings linked in to
        # exercise the guarded tests is a legitimate third. The thing worth failing on is
        # siblings missing for a reason that ISN'T a worktree, i.e. an unbootstrapped clone
        # or a rename that quietly turned the guard permanently false.
        self.assertIn(DOTGIT, ('file', 'dir'), f'{WORKSPACE} is not a git checkout')
        self.assertTrue(SIBLINGS_PRESENT or DOTGIT == 'file',
                        f'{WORKSPACE} has a real .git but no vrc-skills sibling. Every '
                        'live-surface test here is then skipped, so a green run would prove '
                        'nothing — clone the siblings (docs/bootstrap.md) or check whether '
                        'the guard predicate still names the right path.')


class Fixture(unittest.TestCase):
    """A synthetic workspace root with check_prose.ROOT patched at it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()   # resolve: ROOT is resolved, and an
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)   # 8.3/junction TEMP
        self.root = self.tmp / 'root'                                  # breaks relative_to
        self.root.mkdir()

        # Hermetic git. Both git_ignored and governed_md spawn git themselves, so the tests
        # cannot pass flags — a developer's global core.excludesFile (or an inherited GIT_DIR
        # from running under a hook or `git bisect run`) would otherwise silently change which
        # files pass 4 sees.
        env = dict(os.environ)
        for var in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
                    'GIT_OBJECT_DIRECTORY', 'GIT_CEILING_DIRECTORIES',
                    # -c settings travel in these, so `git -c core.excludesFile=... `,
                    # an alias, or `git bisect run` would otherwise reach straight past
                    # the GIT_CONFIG_GLOBAL/SYSTEM redirect below and change pass 4's
                    # file set on someone else's machine.
                    'GIT_CONFIG_PARAMETERS', 'GIT_CONFIG_COUNT'):
            env.pop(var, None)
        for var in [k for k in env if k.startswith(('GIT_CONFIG_KEY_', 'GIT_CONFIG_VALUE_'))]:
            env.pop(var, None)
        nowhere = str(self.tmp / 'no-such-gitconfig')
        env['GIT_CONFIG_GLOBAL'] = nowhere
        env['GIT_CONFIG_SYSTEM'] = nowhere
        self._envp = mock.patch.dict(os.environ, env, clear=True)
        self._envp.start()
        self.addCleanup(self._envp.stop)

        # Process-global dedupe state in the module under test. Left alone, whether a test
        # sees the vanished-family NOTE would depend on which test ran first.
        c._NOTED_VANISHED.clear()
        self.addCleanup(c._NOTED_VANISHED.clear)

        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self._rootp = mock.patch.object(c, 'ROOT', self.root)
        self._rootp.start()
        self.addCleanup(self._rootp.stop)
        self.out = c.Findings()

    # -- fixture builders --

    def write(self, rel, body=''):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding='utf-8')
        return p

    def skill(self, name, body, family='.claude/skills'):
        return self.write(f'{family}/{name}/SKILL.md', body)

    def sibling_gate(self, src="print('validate_skills: 0 skill(s), 0 error(s), 0 warning(s)')\n"):
        """A stub child gate. vrc-skills/skills/ must exist alongside it or all_skill_dirs
        raises FAMILY_REQUIRED_BY — the sibling repo being present with its skill family gone
        is corruption, not absence, and that check fires before the child is ever invoked."""
        (self.root / 'vrc-skills' / 'skills').mkdir(parents=True, exist_ok=True)
        return self.write('vrc-skills/tools/validate_skills.py', src)

    FENCE = {'roots': ['.'], 'glob': '**/*.md', 'exclude': [], 'not_ignored': True}

    def fence(self, **over):
        return {**self.FENCE, **over}

    # -- helpers --

    def capture(self, fn, *a, **kw):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fn(*a, **kw)
        return buf.getvalue()

    def capture_raises(self, exc, fn, *a, **kw):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(exc) as cm:
            fn(*a, **kw)
        return cm.exception, buf.getvalue()


# ---------------------------------------------------------------- constants

class TestReadConstants(Fixture):
    def test_missing_file_fails_loud(self):
        with self.assertRaises(c.GateError):
            c.read_constants(self.root / 'docs' / 'nope.md', 'governed_fence')

    def test_no_block_with_the_marker_fails_loud(self):
        p = self.write('docs/tool-design.md', '# D\n\n```yaml\nsomething_else: 1\n```\n')
        with self.assertRaises(c.GateError):
            c.read_constants(p, 'governed_fence')

    def test_invalid_yaml_is_an_internal_failure_not_a_finding(self):
        p = self.write('docs/tool-design.md',
                       '# D\n\n```yaml\ngoverned_fence:\n  roots: [ unclosed\n```\n')
        with self.assertRaises(c.GateError):
            c.read_constants(p, 'governed_fence')

    def test_marker_selects_its_block_among_several(self):
        p = self.write('docs/tool-design.md',
                       '# D\n\n```yaml\ndecoy: 1\n```\n\n'
                       '```yaml\ngoverned_fence:\n  glob: "**/*.md"\n```\n\n'
                       '```yaml\nalso_not_it: 2\n```\n')
        self.assertEqual(c.read_constants(p, 'governed_fence'),
                         {'governed_fence': {'glob': '**/*.md'}})


class TestValidateFence(Fixture):
    def test_absent_mapping_fails_loud(self):
        # main() reaches this with None from consts.get('governed_fence').
        with self.assertRaises(c.GateError):
            c.validate_fence(None)

    def test_missing_key_is_named(self):
        f = self.fence()
        del f['roots']
        with self.assertRaisesRegex(c.GateError, 'roots'):
            c.validate_fence(f)

    def test_wrong_type_is_named_with_both_types(self):
        with self.assertRaisesRegex(c.GateError, "glob.*str.*list"):
            c.validate_fence(self.fence(glob=['**/*.md']))

    def test_empty_string_element_rejected(self):
        with self.assertRaises(c.GateError):
            c.validate_fence(self.fence(exclude=['']))

    def test_empty_roots_is_the_refusal_that_matters(self):
        # The whole reason this function exists: an empty roots selects zero files and
        # reports a clean run, which is the one failure a governance gate must never have.
        with self.assertRaisesRegex(c.GateError, 'zero files'):
            c.validate_fence(self.fence(roots=[]))

    def test_valid_fence_raises_nothing(self):
        c.validate_fence(self.fence())


# ---------------------------------------------------------------- helpers

class TestStripFences(unittest.TestCase):
    def test_blanks_fenced_content_and_preserves_line_count(self):
        src = ['before', '```python', 'code = 1', '```', 'after']
        self.assertEqual(c.strip_fences(src), ['before', '', '', '', 'after'])

    def test_tilde_fences_are_fences_too(self):
        src = ['a', '~~~', 'hidden', '~~~', 'b']
        self.assertEqual(c.strip_fences(src), ['a', '', '', '', 'b'])

    def test_a_shorter_or_mismatched_run_does_not_close_the_fence(self):
        # ```` opens; ``` is too short to close it, and ~~~ is the wrong character.
        src = ['````', '~~~', '```', 'still inside', '````', 'out']
        self.assertEqual(c.strip_fences(src), ['', '', '', '', '', 'out'])


class TestFnmatchMd(unittest.TestCase):
    def test_double_star_also_matches_zero_directories(self):
        self.assertTrue(c.fnmatch_md('README.md', '**/*.md'))
        self.assertTrue(c.fnmatch_md('docs/x.md', '**/*.md'))
        self.assertFalse(c.fnmatch_md('docs/x.txt', '**/*.md'))


class TestGitIgnored(Fixture):
    def test_empty_input_short_circuits(self):
        with mock.patch.object(c.subprocess, 'run',
                               side_effect=AssertionError('spawned git for nothing')):
            self.assertEqual(c.git_ignored(self.root, []), set())

    def test_reports_only_the_ignored_subset(self):
        self.write('.gitignore', 'skip/\n')
        self.assertEqual(c.git_ignored(self.root, ['skip/a.md', 'keep.md']), {'skip/a.md'})


class TestGovernedMd(Fixture):
    def _rels(self, fence):
        return sorted(p.relative_to(self.root).as_posix() for p in c.governed_md(self.root, fence))

    def test_exclude_prunes_the_directory(self):
        self.write('keep.md', CLEAN_MD)
        self.write('test-output/drop.md', CLEAN_MD)
        self.assertEqual(self._rels(self.fence(exclude=['test-output/'])), ['keep.md'])

    def test_not_ignored_drops_gitignored_files(self):
        self.write('.gitignore', 'secret/\n')
        self.write('keep.md', CLEAN_MD)
        self.write('secret/hidden.md', CLEAN_MD)
        self.assertEqual(self._rels(self.fence()), ['keep.md'])
        self.assertIn('secret/hidden.md', self._rels(self.fence(not_ignored=False)))

    def test_glob_is_honored(self):
        self.write('a.md', CLEAN_MD)
        self.write('b.txt', 'not markdown')
        self.assertEqual(self._rels(self.fence()), ['a.md'])


class TestAllSkillDirs(Fixture):
    def test_vanished_family_under_a_present_repo_fails_loud(self):
        # vrc-skills present but its skills/ gone would otherwise drop every plugin skill
        # and still score the run clean.
        self.write('vrc-skills/tools/validate_skills.py', '')
        with self.assertRaisesRegex(c.GateError, 'vanished'):
            c.all_skill_dirs()

    def test_non_strict_downgrades_the_vanished_family_to_a_note(self):
        # What passes 2-3 call. Raising there aborts the run before any pass reports,
        # which costs a maintainer with a half-refactored sibling the adjudication of the
        # doc edits they actually made — pass 1 still fails the run on the strict call.
        self.write('vrc-skills/tools/validate_skills.py', '')
        self.skill('local', '---\nname: local\n---\n\n# L\n')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            dirs = c.all_skill_dirs(strict=False)
        self.assertEqual([p.name for p in dirs], ['local'])
        self.assertIn('vanished', buf.getvalue())
        self.assertIn('pass 1 will fail the run', buf.getvalue())

    def test_no_families_at_all_is_a_valid_state(self):
        self.assertEqual(c.all_skill_dirs(), [])

    def test_project_skills_alone_are_enumerated(self):
        self.skill('solo', '---\nname: solo\n---\n\n# Solo\n')
        self.assertEqual([p.name for p in c.all_skill_dirs()], ['solo'])


# ---------------------------------------------------------------- pass 1

SUMMARY = 'validate_skills: {n} skill(s), {e} error(s), {w} warning(s)'


class TestPassValidate(Fixture):
    def _child(self, body):
        self.sibling_gate(body)
        self.skill('demo', '---\nname: demo\n---\n\n# Demo\n')

    def test_honest_tally_is_adopted(self):
        self._child(f"print('ERROR a/SKILL.md:1: bad')\n"
                    f"print('WARN  a/SKILL.md:2: meh')\n"
                    f"print({SUMMARY.format(n=1, e=1, w=1)!r})\n"
                    f"raise SystemExit(1)\n")
        self.capture(c.pass_validate, self.out)
        self.assertEqual(self.out.per_pass['validate_skills'], [1, 1])

    def test_child_exit_two_aborts_the_run(self):
        self._child("import sys\nsys.stderr.write('boom\\n')\nraise SystemExit(2)\n")
        exc, _ = self.capture_raises(c.GateError, c.pass_validate, self.out)
        self.assertIn('internal failure', str(exc))

    def test_missing_summary_aborts_the_run(self):
        self._child("print('some output but no summary')\n")
        exc, _ = self.capture_raises(c.GateError, c.pass_validate, self.out)
        self.assertIn('without its summary line', str(exc))

    def test_summary_disagreeing_with_exit_code_aborts_the_run(self):
        # Claims clean, exits 1: the child's own tally and its exit code contradict.
        self._child(f"print({SUMMARY.format(n=1, e=0, w=0)!r})\nraise SystemExit(1)\n")
        exc, _ = self.capture_raises(c.GateError, c.pass_validate, self.out)
        self.assertIn('disagrees', str(exc))

    def test_summary_disagreeing_with_emitted_lines_aborts_the_run(self):
        # Claims two errors, prints one. A gate that miscounts its own findings is broken,
        # not lenient.
        self._child(f"print('ERROR a/SKILL.md:1: bad')\n"
                    f"print({SUMMARY.format(n=1, e=2, w=0)!r})\nraise SystemExit(1)\n")
        exc, _ = self.capture_raises(c.GateError, c.pass_validate, self.out)
        self.assertIn('disagrees', str(exc))

    def test_absent_sibling_names_the_skills_it_could_not_check(self):
        self.skill('one', '---\nname: one\n---\n\n# One\n')
        self.skill('two', '---\nname: two\n---\n\n# Two\n')
        text = self.capture(c.pass_validate, self.out)
        self.assertIn('NOTE', text)
        self.assertIn('2 .claude/skills/ skill(s) went unchecked', text)
        self.assertEqual(self.out.errors, 0)

    def test_no_skill_directories_skips_cleanly(self):
        self.sibling_gate()
        text = self.capture(c.pass_validate, self.out)
        self.assertIn('no governed skill directories', text)
        self.assertEqual(self.out.errors, 0)

    @unittest.skipUnless(SIBLINGS_PRESENT, 'vrc-skills absent (linked worktree)')
    def test_real_child_gate_reports_a_real_finding(self):
        # The stubs above never read their argv, so they cannot catch a mutation that stops
        # passing the skill directories through (all_skill_dirs -> skill_dirs would silently
        # drop the child's "no SKILL.md" error). Only the real child can.
        shutil.copytree(WORKSPACE / 'vrc-skills' / 'tools',
                        self.root / 'vrc-skills' / 'tools')
        shutil.copy(WORKSPACE / 'vrc-skills' / 'CONVENTIONS.md',
                    self.root / 'vrc-skills' / 'CONVENTIONS.md')
        (self.root / 'vrc-skills' / 'skills').mkdir(parents=True, exist_ok=True)
        (self.root / '.claude' / 'skills' / 'empty-dir').mkdir(parents=True)
        self.capture(c.pass_validate, self.out)
        self.assertEqual(self.out.per_pass['validate_skills'], [1, 0])


# ---------------------------------------------------------------- pass 2

class TestPassDocPointers(Fixture):
    """Every carve-out here is tested in both directions. A test that only proves a skip
    fires stays green when the skip is widened to swallow real findings, which is the
    failure mode that matters for a gate."""

    BAD_CONTROL = 'docs/definitely-missing.md'

    def control(self, name='control'):
        self.skill(name, f'---\nname: {name}\n---\n\n# C\n\nSee `{self.BAD_CONTROL}`.\n')

    def run_pass(self, exempt=()):
        return self.capture(c.pass_doc_pointers, self.out, list(exempt), self.fence())

    def test_unresolvable_pointer_warns_at_its_line(self):
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n```\nfenced `docs/ignored.md`\n```\n\n'
                           'Real text citing `docs/nope.md` here.\n')
        text = self.run_pass()
        self.assertIn('.claude/skills/demo/SKILL.md:11:', text)   # the prose line, not the fence
        self.assertIn('docs/nope.md', text)
        self.assertNotIn('docs/ignored.md', text)
        self.assertEqual(self.out.warnings, 1)

    def test_resolvable_pointer_is_silent(self):
        self.write('docs/real.md', CLEAN_MD)
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\nSee `docs/real.md`.\n')
        self.run_pass()
        self.assertEqual(self.out.warnings, 0)

    def test_repeated_pointer_warns_once_per_file(self):
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n`docs/nope.md`\n\n`docs/nope.md`\n')
        self.run_pass()
        self.assertEqual(self.out.warnings, 1)

    def test_exempt_skill_is_skipped_but_the_control_is_still_reported(self):
        self.skill('exempted', '---\nname: exempted\n---\n\n# E\n\n`docs/exempt-miss.md`\n')
        self.control()
        text = self.run_pass(exempt=['exempted'])
        self.assertEqual(self.out.warnings, 1)
        self.assertIn(self.BAD_CONTROL, text)
        self.assertNotIn('docs/exempt-miss.md', text)

    def test_absent_sibling_carve_out_slash_branch_spares_only_the_sibling(self):
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n`vrc-unity-tools/notes/x.md`\n')
        self.control()
        text = self.run_pass()
        self.assertEqual(self.out.warnings, 1)
        self.assertIn(self.BAD_CONTROL, text)
        self.assertNotIn('vrc-unity-tools', text)

    def test_present_sibling_makes_its_broken_pointer_a_finding_again(self):
        (self.root / 'vrc-unity-tools').mkdir()
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n`vrc-unity-tools/notes/x.md`\n')
        text = self.run_pass()
        self.assertEqual(self.out.warnings, 1)
        self.assertIn('vrc-unity-tools/notes/x.md', text)

    def test_KNOWN_QUIRK_a_sibling_pointer_through_docs_leaks_past_the_carve_out(self):
        # Pinned as-is, NOT endorsed. DOCS_REF_RE re-extracts the 'docs/x.md' tail of
        # 'vrc-unity-tools/docs/x.md' as a second, independent ref. That tail does not start
        # with 'vrc-', so the absent-sibling carve-out above does not spare it, and the gate
        # warns about a pointer nobody wrote — in a worktree, which is the venue the carve-out
        # exists for. Over-reporting, not a silent miss, so this pins today's behavior; the
        # fix is routed to docs/local/inbox/check-prose-test-coverage.md.
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n`vrc-unity-tools/docs/x.md`\n')
        text = self.run_pass()
        self.assertEqual(self.out.warnings, 1)
        self.assertIn("'docs/x.md'", text)
        self.assertNotIn('vrc-unity-tools/docs/x.md', text)

    def test_bare_name_carve_out_needs_the_sibling_absent(self):
        # Bare names resolve partly out of vrc-skills, so with it absent a miss says nothing.
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n`orphan.md`\n')
        self.control()
        text = self.run_pass()
        self.assertEqual(self.out.warnings, 1)
        self.assertIn(self.BAD_CONTROL, text)
        self.assertNotIn('orphan.md', text)

    def test_bare_name_is_checked_once_the_sibling_exists(self):
        self.sibling_gate()
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n`orphan.md`\n')
        text = self.run_pass()
        self.assertEqual(self.out.warnings, 1)
        self.assertIn('orphan.md', text)

    def test_per_tree_scratch_pointer_is_spared_but_the_control_is_not(self):
        # docs/local/ is gitignored, so it exists only in the tree that made it — a pointer
        # there is unresolvable by construction, not broken.
        self.write('.gitignore', 'docs/local/\n')
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n`docs/local/board.md`\n')
        self.control()
        text = self.run_pass()
        self.assertEqual(self.out.warnings, 1)
        self.assertIn(self.BAD_CONTROL, text)
        self.assertNotIn('docs/local/board.md', text)


# ---------------------------------------------------------------- pass 3

class TestPassToolNames(Fixture):
    def run_pass(self, exempt=()):
        return self.capture(c.pass_tool_names, self.out, list(exempt), 'Tools')

    def setUp(self):
        super().setUp()
        self.write('TOOLS.md', '| Key | Purpose |\n| --- | --- |\n| `RealTool` | x |\n'
                               '| `CheckAvatar` | y |\n')

    def test_unknown_name_warns_at_its_line(self):
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\nprose\n\n## Tools\n\n'
                           '- **`Ghost`** — not in the roster\n')
        text = self.run_pass()
        self.assertIn('.claude/skills/demo/SKILL.md:11:', text)
        self.assertIn('Ghost', text)
        self.assertEqual(self.out.warnings, 1)

    def test_known_name_is_silent(self):
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n## Tools\n\n- **`RealTool`** — x\n')
        self.run_pass()
        self.assertEqual(self.out.warnings, 0)

    def test_wildcard_token_resolves_by_prefix(self):
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n## Tools\n\n- **`Check*`** — family\n')
        self.run_pass()
        self.assertEqual(self.out.warnings, 0)

    def test_non_token_shapes_are_not_the_slot(self):
        # Dotted package ids and paths are prose, not checkable tool names.
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n## Tools\n\n'
                           '- **`com.vendor.thing`** — a package\n'
                           '- **`tools/reflow_md.py`** — a path\n')
        self.run_pass()
        self.assertEqual(self.out.warnings, 0)

    def test_only_the_terminal_section_is_scanned_and_the_last_one_wins(self):
        self.skill('demo', '---\nname: demo\n---\n\n# D\n\n## Tools\n\n'
                           '- **`EarlyGhost`** — in a superseded section\n\n'
                           '## Notes\n\n- **`OutsideGhost`** — not in the slot\n\n'
                           '## Tools (again)\n\n- **`LateGhost`** — the live section\n')
        text = self.run_pass()
        self.assertEqual(self.out.warnings, 1)
        self.assertIn('LateGhost', text)

    def test_exempt_skill_is_skipped_but_the_control_is_still_reported(self):
        self.skill('exempted', '---\nname: exempted\n---\n\n# E\n\n## Tools\n\n'
                               '- **`ExemptGhost`** — x\n')
        self.skill('control', '---\nname: control\n---\n\n# C\n\n## Tools\n\n'
                              '- **`ControlGhost`** — x\n')
        text = self.run_pass(exempt=['exempted'])
        self.assertEqual(self.out.warnings, 1)
        self.assertIn('ControlGhost', text)
        self.assertNotIn('ExemptGhost', text)


# ---------------------------------------------------------------- pass 4

class TestPassForm(Fixture):
    def test_drifted_file_is_an_error_naming_the_fix(self):
        self.write('bad.md', DRIFTED_MD)
        text = self.capture(c.pass_form, self.out, self.fence())
        self.assertEqual(self.out.errors, 1)
        self.assertIn('reflow_md.py', text)

    def test_clean_file_passes_and_the_count_is_reported(self):
        self.write('good.md', CLEAN_MD)
        text = self.capture(c.pass_form, self.out, self.fence())
        self.assertEqual(self.out.errors, 0)
        self.assertIn('1 governed file(s) checked', text)

    def test_zero_files_is_refused_not_reported_as_clean(self):
        # No .md anywhere: reporting "0 checked, no findings" would pass the gate by
        # measuring nothing, which is the failure this refusal exists for.
        exc, _ = self.capture_raises(c.GateError, c.pass_form, self.out, self.fence())
        self.assertIn('zero files', str(exc))

    def test_non_git_root_is_skipped_with_a_note(self):
        self.write('good.md', CLEAN_MD)
        plain = self.root / 'vrc-plain'
        plain.mkdir()
        (plain / 'x.md').write_text(DRIFTED_MD, encoding='utf-8')
        # Excluded from the '.' root too, or the drifted file is reached through the walk
        # rather than through the root under test, and the assertion proves nothing.
        text = self.capture(c.pass_form, self.out,
                            self.fence(roots=['.', 'vrc-*'], exclude=['vrc-plain/']))
        self.assertIn('is not a git repo', text)
        self.assertEqual(self.out.errors, 0)

    def test_unmatched_root_glob_is_skipped_with_a_note(self):
        self.write('good.md', CLEAN_MD)
        text = self.capture(c.pass_form, self.out, self.fence(roots=['.', 'vrc-*']))
        self.assertIn('no sibling matches root "vrc-*"', text)

    def test_a_dot_git_FILE_is_still_a_repo(self):
        # In a linked worktree .git is a file, not a directory — the venue this workspace
        # actually commits from. Testing .exists() with a git-init'd fixture alone would let
        # a narrowing to .is_dir() through, and that mutation makes pass 4 skip every root,
        # resolve zero files, and refuse to run at all.
        wt = self.root / 'vrc-thing'
        wt.mkdir()
        (wt / '.git').write_text(f'gitdir: {(self.root / ".git").as_posix()}\n', encoding='utf-8')
        (wt / 'drifted.md').write_text(DRIFTED_MD, encoding='utf-8')
        self.write('good.md', CLEAN_MD)
        text = self.capture(c.pass_form, self.out, self.fence(roots=['.', 'vrc-*'],
                                                              not_ignored=False))
        self.assertNotIn('is not a git repo', text)
        self.assertEqual(self.out.errors, 1)


# ---------------------------------------------------------------- entry point

class TestMainExitCodes(Fixture):
    """The 0/1/2 mapping is a contract three callers depend on (.githooks/pre-commit reads
    it to decide whether the gate judged or crashed). Assert it through the real entry point
    rather than trusting main()'s return value."""

    def build(self, child_body=None, drifted=False):
        tools = self.root / 'tools'
        tools.mkdir()
        for name in ('check_prose.py', 'reflow_md.py'):
            shutil.copy(WORKSPACE / 'tools' / name, tools / name)
        self.write('docs/tool-design.md',
                   '# D\n\n```yaml\ngoverned_fence:\n  roots:\n    - "."\n'
                   '  not_ignored: true\n  glob: "**/*.md"\n  exclude:\n'
                   '    - test-output/\n```\n')
        self.write('TOOLS.md', '| Key |\n| --- |\n| `RealTool` |\n')
        self.write('README.md', DRIFTED_MD if drifted else CLEAN_MD)
        if child_body is not None:
            self.sibling_gate(child_body)
            # A skill directory has to exist or pass 1 NOTE-skips before it ever invokes the
            # child, and the exit-code assertions below would be measuring nothing.
            self.skill('demo', '---\nname: demo\n---\n\n# Demo\n')

    def run_gate(self):
        p = subprocess.run([sys.executable, str(self.root / 'tools' / 'check_prose.py')],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        return p.returncode, p.stdout + p.stderr

    def test_clean_workspace_exits_zero(self):
        self.build(child_body=f"print({SUMMARY.format(n=1, e=0, w=0)!r})\n")
        rc, text = self.run_gate()
        self.assertEqual(rc, 0, text)

    def test_findings_exit_one(self):
        self.build(child_body=f"print({SUMMARY.format(n=1, e=0, w=0)!r})\n", drifted=True)
        rc, text = self.run_gate()
        self.assertEqual(rc, 1, text)
        self.assertIn('1 error(s)', text)

    def test_malformed_fence_exits_two(self):
        self.build(child_body=f"print({SUMMARY.format(n=1, e=0, w=0)!r})\n")
        self.write('docs/tool-design.md',
                   '# D\n\n```yaml\ngoverned_fence:\n  roots: []\n  not_ignored: true\n'
                   '  glob: "**/*.md"\n  exclude: []\n```\n')
        rc, text = self.run_gate()
        self.assertEqual(rc, 2, text)

    def test_crashed_child_gate_exits_two_not_one(self):
        # Exit 1 would tell the hook "the prose has findings" about a gate that never ran.
        self.build(child_body="raise SystemExit(2)\n")
        rc, text = self.run_gate()
        self.assertEqual(rc, 2, text)

    def test_a_crashed_child_still_lets_the_other_passes_report_first(self):
        # Pass 1 runs last so a half-refactored vrc-skills does not cost a maintainer the
        # adjudication of the doc edits they actually made.
        self.build(child_body="raise SystemExit(2)\n", drifted=True)
        rc, text = self.run_gate()
        self.assertEqual(rc, 2, text)
        self.assertIn('README.md', text)
        self.assertIn('not one-line-per-paragraph', text)

    def test_an_aborted_run_still_prints_a_tally_and_says_it_is_partial(self):
        # Exiting 2 with no summary at all reads downstream as "nothing was judged", which
        # is false once any pass got far enough to emit a finding. The hook's message is
        # written against this line.
        self.build(child_body="raise SystemExit(2)\n", drifted=True)
        rc, text = self.run_gate()
        self.assertEqual(rc, 2, text)
        self.assertIn('check_prose:', text)
        self.assertIn('RUN INCOMPLETE', text)

    def test_a_vanished_skill_family_does_not_silence_the_reporting_passes(self):
        # The scenario the pass reorder exists for, and the one it used to miss: passes 2-3
        # called all_skill_dirs strictly, so a present vrc-skills with its skills/ gone
        # aborted at pass 2 with empty stdout and the maintainer's drifted doc unadjudicated.
        self.build(child_body="raise SystemExit(2)\n", drifted=True)
        shutil.rmtree(self.root / 'vrc-skills' / 'skills')
        rc, text = self.run_gate()
        self.assertEqual(rc, 2, text)
        self.assertIn('not one-line-per-paragraph', text)   # pass 4 still adjudicated
        self.assertIn('vanished', text)
        self.assertIn('RUN INCOMPLETE', text)


# ---------------------------------------------------------------- drift

class TestSharedHelperDrift(unittest.TestCase):
    @unittest.skipUnless(SIBLINGS_PRESENT, 'vrc-skills absent (linked worktree)')
    def test_strip_fences_has_not_drifted_from_the_child_gates_copy(self):
        # strip_fences and FENCE_RE are duplicated in vrc-skills/tools/validate_skills.py.
        # Nothing forces them to stay in step, and a one-character divergence silently
        # changes which lines each gate reads — with no test in either repo going red.
        #
        # Compared by agreement on inputs, not by source or bytecode: the two copies are
        # allowed to differ in comments and docstrings (the child's carries one, this repo's
        # does not), and both of those representations move when a docstring does. What has
        # to hold is that they answer the same for the same markdown.
        sys.path.insert(0, str(WORKSPACE / 'vrc-skills' / 'tools'))
        import validate_skills as v   # noqa: E402
        cases = [
            ['plain', 'text'],
            ['a', '```', 'code', '```', 'b'],
            ['a', '~~~', 'code', '~~~', 'b'],
            ['````', '```', 'still inside', '````', 'out'],
            ['   ```yaml', 'indented fence', '   ```', 'after'],
            ['```unclosed', 'runs to the end'],
            ['# H1', '```md', '# fenced H1', '```', '[link](x.md)'],
        ]
        for lines in cases:
            with self.subTest(lines=lines):
                self.assertEqual(c.strip_fences(lines), v.strip_fences(lines),
                                 'the two strip_fences copies have diverged')
        self.assertEqual(c.FENCE_RE.pattern, v.FENCE_RE.pattern)


if __name__ == '__main__':
    unittest.main()
