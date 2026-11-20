"""Fixed acceptance cases: workers must repair outputs, not these checks."""
import unittest

from label import task_label
from total import total_cents


class TotalTests(unittest.TestCase):
    def test_all_amounts_count_once_without_mutation(self):
        amounts = [125, 0, 75]
        self.assertEqual(total_cents(amounts), 200)
        self.assertEqual(amounts, [125, 0, 75])

    def test_empty_and_single_amount(self):
        self.assertEqual(total_cents([]), 0)
        self.assertEqual(total_cents([17]), 17)

    def test_invalid_amounts_are_refused(self):
        for value in (None, (1, 2), '12', [-1], [True], [1.5], ['1']):
            with self.subTest(value=value), self.assertRaises(ValueError):
                total_cents(value)


class LabelTests(unittest.TestCase):
    def test_outer_whitespace_is_removed(self):
        self.assertEqual(task_label('  Fix the total \n'), 'Task: Fix the total')

    def test_internal_whitespace_and_existing_title_are_preserved(self):
        self.assertEqual(task_label('Check  both files'), 'Task: Check  both files')
        self.assertEqual(task_label('Ready'), 'Task: Ready')

    def test_invalid_titles_are_refused(self):
        for value in ('', ' \t\n', None, 42, [], True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                task_label(value)


if __name__ == '__main__':
    unittest.main()
