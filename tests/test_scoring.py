from pathlib import Path
import unittest

from change_impact_analyzer.models import SourceFile
from change_impact_analyzer.scoring import score_files


class ScoringTests(unittest.TestCase):
    def test_score_files_prefers_path_and_content_match(self):
        files = [
            SourceFile(
                path=Path("/repo/src/bookings/refunds.ts"),
                relative_path="src/bookings/refunds.ts",
                extension=".ts",
                text="export function createStripeRefund() { return stripe.refunds.create(); }",
                line_count=1,
                symbols=("createStripeRefund", "create", "stripe", "refund"),
            ),
            SourceFile(
                path=Path("/repo/src/users/profile.ts"),
                relative_path="src/users/profile.ts",
                extension=".ts",
                text="export function updateProfile() {}",
                line_count=1,
                symbols=("updateProfile", "update", "profile"),
            ),
        ]

        ranked = score_files(files, "add stripe refunds to bookings", top_n=2)

        self.assertEqual(ranked[0].file.relative_path, "src/bookings/refunds.ts")
        self.assertEqual(len(ranked), 1)


if __name__ == "__main__":
    unittest.main()
