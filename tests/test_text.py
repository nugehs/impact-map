import unittest

from change_impact_analyzer.text import tokenize, weighted_query_terms


class TextTests(unittest.TestCase):
    def test_tokenize_splits_identifiers(self):
        self.assertEqual(
            tokenize("fix bookingRefundStatus in API"),
            ["booking", "refund", "status", "api"],
        )

    def test_weighted_query_terms_boosts_domain_words(self):
        terms = weighted_query_terms("add stripe refund flow")
        self.assertGreater(terms["stripe"], terms["flow"])
        self.assertGreater(terms["refund"], terms["flow"])

    def test_weighted_query_terms_adds_singular_variants(self):
        terms = weighted_query_terms("refunds bookings")
        self.assertIn("refund", terms)
        self.assertIn("booking", terms)


if __name__ == "__main__":
    unittest.main()
