from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyzer import analyze
from .report import render_json, render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cia",
        description="Predict files, tests, and risks for a requested code change.",
    )
    parser.add_argument("repo", type=Path, help="Path to the repository to analyze.")
    parser.add_argument("request", help="Plain-English change request.")
    parser.add_argument("--top", type=int, default=10, help="Number of impacted files to show.")
    parser.add_argument("--max-files", type=int, default=5000, help="Maximum source-like files to scan.")
    parser.add_argument("--json", action="store_true", help="Render machine-readable JSON instead of Markdown.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.top < 1:
        parser.error("--top must be at least 1")
    if args.max_files < 1:
        parser.error("--max-files must be at least 1")

    try:
        result = analyze(args.repo, args.request, top_n=args.top, max_files=args.max_files)
    except Exception as exc:
        print(f"cia: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(render_json(result))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

