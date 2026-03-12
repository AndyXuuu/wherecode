import unittest

from app.analyzer import analyze_text


class AnalyzerTestCase(unittest.TestCase):
    def test_positive_signal(self) -> None:
        row = analyze_text("chip breakthrough with strong growth and record profit")
        self.assertEqual(row["sentiment_label"], "positive")
        self.assertIn(row["value_level"], {"high", "medium"})

    def test_negative_signal(self) -> None:
        row = analyze_text("company faces investigation and loss with debt risk")
        self.assertEqual(row["sentiment_label"], "negative")
        self.assertEqual(row["value_level"], "low")


if __name__ == "__main__":
    unittest.main()
