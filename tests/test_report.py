from pathlib import Path
import unittest

from change_impact_analyzer.models import FileScore, SourceFile
from change_impact_analyzer.report import suggested_file_action


class ReportTests(unittest.TestCase):
    def test_screen_file_gets_primary_action(self):
        item = FileScore(
            SourceFile(
                path=Path("/repo/app/camera.tsx"),
                relative_path="app/(tabs)/camera.tsx",
                extension=".tsx",
                text="",
                line_count=10,
                symbols=("CameraScreen", "camera", "screen"),
            ),
            score=10,
        )

        self.assertIn("Primary screen", suggested_file_action(item, 2))

    def test_theme_file_gets_conditional_action(self):
        item = FileScore(
            SourceFile(
                path=Path("/repo/src/constants/theme.ts"),
                relative_path="src/constants/theme.ts",
                extension=".ts",
                text="",
                line_count=10,
            ),
            score=10,
        )

        self.assertIn("visual polish", suggested_file_action(item, 5))


if __name__ == "__main__":
    unittest.main()
