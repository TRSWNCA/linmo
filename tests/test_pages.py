from __future__ import annotations

import unittest

from linmo.pages import parse_pages


class ParsePagesTests(unittest.TestCase):
    def test_single_page(self) -> None:
        self.assertEqual(parse_pages("41"), [41])

    def test_range(self) -> None:
        self.assertEqual(parse_pages("1-3"), [1, 2, 3])

    def test_list(self) -> None:
        self.assertEqual(parse_pages("1,3,5"), [1, 3, 5])

    def test_keeps_first_occurrence_order_without_duplicates(self) -> None:
        self.assertEqual(parse_pages("3,1-3"), [3, 1, 2])

    def test_rejects_descending_range(self) -> None:
        with self.assertRaises(ValueError):
            parse_pages("3-1")


if __name__ == "__main__":
    unittest.main()
