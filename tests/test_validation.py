from pathlib import Path
import subprocess
import tempfile
import unittest

from change_impact_analyzer.models import FileScore, SourceFile
from change_impact_analyzer.validation import validate_against_diff


class ValidationTests(unittest.TestCase):
    def test_validate_against_diff_marks_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src/example.py").write_text("print('hello')\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-m",
                    "initial",
                ],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            top_files = [
                FileScore(
                    SourceFile(
                        path=repo / "src/example.py",
                        relative_path="src/example.py",
                        extension=".py",
                        text="",
                        line_count=1,
                    ),
                    score=10,
                )
            ]

            validation = validate_against_diff(repo, "HEAD", top_files)

        self.assertEqual(validation.verdict, "no_changes")
        self.assertIn("src/example.py", validation.unconfirmed_candidates)

    def test_validate_against_diff_marks_confirmed_and_missed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src/example.py").write_text("print('hello')\n", encoding="utf-8")
            (repo / "src/missed.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-m",
                    "initial",
                ],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "src/example.py").write_text("print('changed')\n", encoding="utf-8")
            (repo / "src/missed.py").write_text("print('changed')\n", encoding="utf-8")

            top_files = [
                FileScore(
                    SourceFile(
                        path=repo / "src/example.py",
                        relative_path="src/example.py",
                        extension=".py",
                        text="",
                        line_count=1,
                    ),
                    score=10,
                )
            ]

            validation = validate_against_diff(repo, "HEAD", top_files)

        self.assertEqual(validation.verdict, "needs_review")
        self.assertIn("src/example.py", validation.confirmed_direct)
        self.assertIn("src/missed.py", validation.missed_changed_files)


if __name__ == "__main__":
    unittest.main()
