import sys
import types
import unittest


class _ScrapyStub(types.SimpleNamespace):
    class Item(dict):
        pass

    class Spider:
        pass

    @staticmethod
    def Field(*args, **kwargs):
        return None

    @staticmethod
    def Request(*args, **kwargs):
        return None


sys.modules.setdefault("scrapy", _ScrapyStub())

from scoutbot.spiders.opportunities_spider import extract_deadline


class DeadlineExtractionTests(unittest.TestCase):
    def test_extracts_numeric_deadline(self):
        self.assertEqual(
            extract_deadline("Applications close on 30/06/2025"),
            "30/06/2025",
        )

    def test_extracts_ordinal_day_deadline(self):
        self.assertEqual(
            extract_deadline("Deadline: 30th June 2025"),
            "30th June 2025",
        )

    def test_extracts_month_day_without_year(self):
        self.assertEqual(
            extract_deadline("Submissions accepted until June 30"),
            "June 30",
        )

    def test_extracts_rolling_admissions(self):
        self.assertEqual(
            extract_deadline("Rolling admissions — applications reviewed monthly"),
            "Rolling",
        )


if __name__ == "__main__":
    unittest.main()
