"""Regression tests for the PR's escaped-alias, table-column and detached-outline failures."""
import unittest
from markdown_structure import wikilink_destination, table_cells, table_errors, hierarchy_errors


class MarkdownStructureTests(unittest.TestCase):
    def test_aliases(self):
        for raw in ['note|label', r'note\|label', 'note']:
            with self.subTest(raw=raw):
                self.assertEqual(wikilink_destination(raw), 'note')
        self.assertEqual(wikilink_destination(r'note#section\|label'), 'note#section')

    def test_escaped_table_alias_keeps_columns(self):
        row = r'|[[note\|label]]|context|'
        self.assertEqual(len(table_cells(row)), 2)
        self.assertEqual(table_errors('|Source|Context|\n|---|---|\n' + row), [])

    def test_unescaped_alias_and_column_shift_are_detected(self):
        issues = table_errors('|Source|Context|\n|---|---|\n|[[note|label]]|context|')
        self.assertTrue(any('column count' in x for x in issues))
        self.assertTrue(any('unescaped wikilink' in x for x in issues))

    def test_even_backslash_does_not_escape_pipe(self):
        self.assertEqual(len(table_cells(r'|a\\|b|')), 2)

    def test_correct_outline_and_blank_lines(self):
        self.assertEqual(hierarchy_errors('- root\n    - child\n\n        - leaf\n    - sibling'), [])

    def test_detached_outline_after_paragraph(self):
        self.assertTrue(hierarchy_errors('- root\n\nParagraph\n\n    - detached'))
        self.assertTrue(hierarchy_errors('    - detached'))

    def test_skipped_level_and_invalid_indent(self):
        self.assertTrue(hierarchy_errors('- root\n        - skipped'))
        self.assertTrue(hierarchy_errors('- root\n  - invalid'))

    def test_new_root_after_paragraph(self):
        self.assertEqual(hierarchy_errors('- root\nParagraph\n- next root'), [])


if __name__ == '__main__':
    unittest.main()
