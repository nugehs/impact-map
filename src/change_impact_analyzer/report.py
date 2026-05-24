from __future__ import annotations

import json

from .models import AnalysisResult, FileScore


def render_markdown(result: AnalysisResult) -> str:
    lines: list[str] = []
    lines.append("# Change Impact Report")
    lines.append("")
    lines.append(f"Request: {result.request}")
    lines.append("")

    profile = result.profile
    lines.append("## Project Profile")
    lines.append(f"- Root: `{profile.root}`")
    lines.append(f"- Scanned files: {profile.file_count}")
    lines.append(f"- Skipped files/dirs: {profile.skipped_count}")
    if profile.markers:
        lines.append(f"- Detected markers: {', '.join(profile.markers)}")
    if profile.extensions:
        common = ", ".join(f"{ext}={count}" for ext, count in list(profile.extensions.items())[:10])
        lines.append(f"- Common extensions: {common}")
    lines.append("")

    lines.append("## Likely Impacted Files")
    if not result.top_files:
        lines.append("No strong file matches found.")
    for index, item in enumerate(result.top_files, start=1):
        lines.extend(_render_file_score(index, item))
    lines.append("")

    lines.append("## Tests To Run Or Add")
    for suggestion in result.test_suggestions:
        lines.append(f"- {suggestion}")
    lines.append("")

    lines.append("## Implementation Plan")
    for index, step in enumerate(result.implementation_plan, start=1):
        lines.append(f"{index}. {step}")
    lines.append("")

    lines.append("## Risks To Check")
    for risk in result.risks:
        lines.append(f"- {risk}")
    lines.append("")
    return "\n".join(lines)


def render_json(result: AnalysisResult) -> str:
    data = {
        "request": result.request,
        "profile": {
            "root": str(result.profile.root),
            "file_count": result.profile.file_count,
            "skipped_count": result.profile.skipped_count,
            "extensions": result.profile.extensions,
            "markers": result.profile.markers,
            "package_scripts": result.profile.package_scripts,
        },
        "top_files": [
            {
                "path": str(item.file.path),
                "relative_path": item.file.relative_path,
                "extension": item.file.extension,
                "line_count": item.file.line_count,
                "score": round(item.score, 2),
                "reasons": item.reasons,
                "routes": list(item.file.routes),
                "symbols": list(item.file.symbols[:25]),
                "related_files": item.related_files,
                "is_test": item.file.is_test,
            }
            for item in result.top_files
        ],
        "test_suggestions": result.test_suggestions,
        "implementation_plan": result.implementation_plan,
        "risks": result.risks,
    }
    return json.dumps(data, indent=2)


def _render_file_score(index: int, item: FileScore) -> list[str]:
    lines = [
        f"{index}. `{item.file.relative_path}`",
        f"   - Score: {item.score:.1f}",
    ]
    for reason in item.reasons[:5]:
        lines.append(f"   - {reason}")
    if item.file.routes:
        routes = ", ".join(f"`{route}`" for route in item.file.routes[:5])
        lines.append(f"   - Routes: {routes}")
    if item.related_files:
        related = ", ".join(f"`{path}`" for path in item.related_files[:5])
        lines.append(f"   - Related: {related}")
    return lines
