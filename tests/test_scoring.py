from pathlib import Path
import unittest

from change_impact_analyzer.models import SourceFile
from change_impact_analyzer.scoring import score_files, suggest_tests


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

    def test_suggest_tests_ignores_generic_path_terms(self):
        files = [
            SourceFile(
                path=Path("/repo/src/components/camera/CameraControls.tsx"),
                relative_path="src/components/camera/CameraControls.tsx",
                extension=".tsx",
                text="",
                line_count=1,
                symbols=("CameraControls", "camera", "controls"),
            ),
            SourceFile(
                path=Path("/repo/src/services/auth/__tests__/auth.test.ts"),
                relative_path="src/services/auth/__tests__/auth.test.ts",
                extension=".ts",
                text="",
                line_count=1,
                is_test=True,
            ),
        ]
        top_files = score_files(files, "improve camera zoom controls", top_n=1)

        suggestions = suggest_tests(files, top_files, {"test": "jest"})

        self.assertEqual(suggestions, ["Run package script `test`: jest"])


if __name__ == "__main__":
    unittest.main()
