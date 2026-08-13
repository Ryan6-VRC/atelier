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

    # --- every block rule is measured from the list item's content column ---
    # A `- ` item's content starts at column 2 and a `  - ` child's at 4, so the
    # first indent that means "code" is that column plus 4. An absolute threshold
    # fails in both directions: it certifies wrapped continuations as canonical,
    # and it stops recognizing the block starts nested one level in.
    def test_child_item_continuation_joins(self):
        self.assertReflow('- parent\n  - child a\n    wrapped\n  - child b\n',
                          contains='  - child a wrapped')

    def test_ordered_item_continuation_joins(self):
        self.assertReflow('1. first\n   wrapped\n', contains='1. first wrapped')

    def test_wide_ordered_marker_continuation_joins(self):
        self.assertReflow('10. first\n    wrapped\n', contains='10. first wrapped')

    def test_indented_code_inside_list_item_stays_verbatim(self):
        self.assertReflow('- item\n\n      code line\n      more code\n', unchanged=True)

    def test_indented_code_under_child_item_stays_verbatim(self):
        self.assertReflow('- p\n  - child\n\n        deep code\n', unchanged=True)

    def test_top_level_indented_code_stays_verbatim(self):
        self.assertReflow('para\n\n    code a\n    code b\n', unchanged=True)

    def test_top_level_indented_code_starting_with_dash_is_not_a_list(self):
        # With no list open, column 4 is code — even when it looks like a bullet.
        self.assertReflow('para\n\n    - not a list\n    still code\n', unchanged=True)

    def test_fence_indented_into_a_list_item_still_opens(self):
        # The fence sits at 4, inside a child whose content column is 4. Block
        # starts must move with the item, or the fence goes unrecognized and its
        # body is joined into the bullet — a destroyed code block, guards green.
        self.assertReflow('- parent\n  - child\n    ```\n    code one\n    code two\n    ```\n  - sibling\n',
                          absent='child ```', unchanged=True)

    def test_heading_indented_into_a_list_item_stays_standalone(self):
        self.assertReflow('- bullet\n    # Heading\n', unchanged=True)

    def test_setext_underline_indented_into_a_list_item_stays_standalone(self):
        self.assertReflow('- bullet\n    ---\n', unchanged=True)

    def test_reference_definitions_indented_into_a_list_item_do_not_merge(self):
        self.assertReflow('- item\n\n    [a]: http://x\n    [b]: http://y\n', unchanged=True)

    def test_marker_followed_by_five_spaces_opens_code_not_content(self):
        # CommonMark: 5+ spaces after the marker means content starts one column
        # past it, and the rest of the line is an indented code block.
        self.assertReflow('-     foo\n      bar\n', unchanged=True)

    def test_spaced_thematic_break_is_not_a_list_marker(self):
        # `* * *` matches a bullet pattern but opens no item, so the line below
        # it is still top-level code.
        self.assertReflow('* * *\n    x = 1\nprose word here\n', contains='    x = 1')

    # --- tabs are declined rather than modelled ---
    # A tab's width depends on the column it lands in, and nothing here is
    # authored with tabs. So no indent bound accepts one and no item is measured
    # through one: a tab-bearing line is left exactly as written, in both
    # directions — never joined into, and never reported as needing a reflow.
    def test_tab_after_marker_leaves_the_item_alone(self):
        self.assertReflow('- bullet\n-\tfoo\n', unchanged=True)
        self.assertReflow('-\tfirst\n    wrapped\n', unchanged=True)

    def test_tab_led_fence_is_code_not_a_fence(self):
        self.assertReflow('\t```\n```\n* star item\n     prose word\n', unchanged=True)

    def test_tab_led_line_does_not_close_a_fence(self):
        self.assertReflow('  ~~~~\n\t~~~~\n  * star item\n      prose word\n', unchanged=True)

    def test_ordered_marker_over_nine_digits_is_not_a_marker(self):
        # CommonMark caps an ordered marker at 9 digits; past that the line is
        # ordinary prose and must not open an item, or the code block below it
        # gets dedented out of protection.
        self.assertReflow('1234567890. prose\n\n            code one\n            code two\n',
                          unchanged=True)

    # --- known residual, locked so a change here is deliberate ---
    def test_known_residual_non_one_ordered_marker_after_paragraph(self):
        """A non-`1` ordered marker cannot interrupt a paragraph in CommonMark,
        so this line is prose and the block below it is top-level code — but the
        marker still opens an item here and the code is joined. Both candidate
        fixes measured worse (one joins every `1./2./3.` step list in the repo,
        the other raises the adversarial residual sevenfold), so the behaviour is
        recorded rather than fixed. Change it only with a measurement."""
        self.assertReflow('paragraph\n2. not a list\n\n    code one\n    code two\n',
                          contains='code one code two')


if __name__ == '__main__':
    unittest.main()
