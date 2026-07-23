# tools/tests/test_reflow_md.py
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import reflow_md as r  # noqa: E402


class ReflowInvariants(unittest.TestCase):
    """Every reflow must preserve the token stream and be idempotent — the two
    guarantees the tool asserts before any write. assertReflow enforces both,
    then checks the specific transform."""

    def assertReflow(self, src, *, contains=None, absent=None, unchanged=False):
        res = r.reflow(src)
        self.assertEqual(src.split(), res.split(), 'token stream altered')
        self.assertEqual(r.reflow(res), res, 'not idempotent')
        if unchanged:
            self.assertEqual(res, src, 'expected byte-unchanged')
        if contains is not None:
            self.assertIn(contains, res)
        if absent is not None:
            self.assertNotIn(absent, res)
        return res

    # --- core behaviour ---
    def test_paragraph_joins(self):
        self.assertReflow('one two\nthree four\n', contains='one two three four')

    def test_list_item_continuation_joins(self):
        self.assertReflow('- item text\n  continued\n- next\n', contains='item text continued')

    def test_nested_list_two_space_continuation_joins(self):
        self.assertReflow('- parent\n  more parent\n- sibling\n', contains='parent more parent')

    def test_table_and_code_untouched(self):
        self.assertReflow('| a | b |\n| - | - |\n| 1 | 2 |\n', unchanged=True)

    # --- council finding #1: setext headings must survive, idempotent ---
    def test_setext_h1_underline_stays_standalone(self):
        self.assertReflow('Title\n===\nFollowing text\n', absent='=== Following', unchanged=True)

    def test_setext_h2_dash_underline_stays_standalone(self):
        self.assertReflow('Sub\n---\nmore words\n', absent='- more', unchanged=True)

    # --- council finding #2: reference / footnote definitions must not merge ---
    def test_link_reference_definitions_do_not_merge(self):
        self.assertReflow('[a]: https://x/a\n[b]: https://x/b\n', absent='/a [b]', unchanged=True)

    def test_footnote_definitions_do_not_merge(self):
        self.assertReflow('[^1]: first\n[^2]: second\n', absent='first [^2]', unchanged=True)

    # --- council finding #3: hard breaks preserved ---
    def test_two_space_hardbreak_preserved(self):
        self.assertReflow('alpha\nbeta  \ngamma\n', contains='beta  ')

    def test_backslash_hardbreak_preserved(self):
        self.assertReflow('alpha\nbeta\\\ngamma\n', contains='beta\\')

    # --- council finding #4: a longer fence is not closed by an inner shorter run ---
    def test_long_fence_not_closed_by_inner_shorter_run(self):
        self.assertReflow('````\ncode ```\nstill code\n````\n', contains='still code', unchanged=True)

    def test_plain_fence_contents_not_reflowed(self):
        self.assertReflow('```\na\nb\n```\n', unchanged=True)

    # --- council finding #5: raw-text HTML preserved verbatim ---
    def test_pre_block_not_collapsed(self):
        self.assertReflow('<pre>\nline one\nline two\n</pre>\n', absent='one line two', unchanged=True)

    # --- council finding #7: bare leading '---' is a thematic break, not front-matter ---
    def test_unterminated_leading_rule_reflows_body(self):
        self.assertReflow('---\n\npara one\npara two\n', contains='para one para two')

    def test_real_frontmatter_passthrough_then_body_reflows(self):
        src = '---\nkey: val\nlist:\n  - a\n---\n\nbody one\nbody two\n'
        res = self.assertReflow(src, contains='body one body two')
        self.assertIn('key: val', res)

    # --- council finding #8 (accepted): 4-space continuation is left as-is, safely ---
    def test_deep_indent_continuation_left_unchanged(self):
        self.assertReflow('- parent\n  - child a\n    wrapped\n  - child b\n', unchanged=True)


if __name__ == '__main__':
    unittest.main()
