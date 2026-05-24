from __future__ import annotations

from pathlib import Path

from .models import AnalysisResult
from .scanner import RepoScanner
from .scoring import build_plan, identify_risks, score_files, suggest_tests


def analyze(repo: Path, request: str, top_n: int = 10, max_files: int = 5000) -> AnalysisResult:
    scanner = RepoScanner(repo, max_files=max_files)
    profile, files = scanner.scan()
    top_files = score_files(files, request, top_n=top_n)
    tests = suggest_tests(files, top_files, profile.package_scripts)
    plan = build_plan(request, top_files)
    risks = identify_risks(request, top_files)
    return AnalysisResult(
        request=request,
        profile=profile,
        top_files=top_files,
        test_suggestions=tests,
        implementation_plan=plan,
        risks=risks,
    )

