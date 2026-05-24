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

    lines.append("## Recommended Next Steps")
    for index, step in enumerate(result.implementation_plan, start=1):
        lines.append(f"{index}. {step}")
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
                "suggested_action": suggested_file_action(item, index),
                "routes": list(item.file.routes),
                "symbols": list(item.file.symbols[:25]),
                "related_files": item.related_files,
                "is_test": item.file.is_test,
            }
            for index, item in enumerate(result.top_files, start=1)
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
        f"   - Action: {suggested_file_action(item, index)}",
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


def suggested_file_action(item: FileScore, rank: int) -> str:
    path = item.file.relative_path.lower()
    symbols = " ".join(item.file.symbols).lower()
    combined = f"{path} {symbols}"

    if item.file.is_test:
        return "Run or update after the implementation path is clear; do not start here unless the request is test-only."
    if item.file.extension in {".md", ".mdx", ".rst"}:
        return "Update only if user-facing docs or setup instructions must change."
    if any(part in path for part in ("theme", "styles", "tokens", "colors")):
        return "Inspect only if the change needs visual polish, spacing, or shared design tokens."
    if any(part in path for part in ("permission", "auth", "session", "guard")):
        return "Inspect for behavioral side effects; edit only if the change affects access, auth, or permission flow."
    if "overlay" in path:
        return "Check for UI overlap or gesture conflicts; edit only if the new interaction collides with this layer."
    if any(part in path for part in ("control", "toolbar", "button", "form", "panel")):
        return "Inspect first for UI ownership; edit here if the requested control should be reusable or shared."
    if any(part in combined for part in ("screen", "page", "view")) or path.startswith("app/"):
        return "Primary screen/entrypoint candidate; edit here if the matched behavior is local state, gestures, or orchestration."
    if any(part in path for part in ("route", "controller", "endpoint", "api")):
        return "Trace the request/response contract here before changing clients or callers."
    if any(part in path for part in ("service", "manager", "repository", "store")):
        return "Inspect for business logic ownership; edit here if the requested behavior is not just presentation."
    if rank == 1:
        return "Primary implementation candidate; read callers/imports, then make the smallest behavior change here."
    if "hook" in path or combined.startswith("use"):
        return "Inspect if state, lifecycle, or permission behavior changes; otherwise treat as supporting context."
    return "Inspect to confirm whether it is a caller, dependency, or shared helper before editing."
