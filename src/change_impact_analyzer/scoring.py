from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from .models import FileScore, SourceFile
from .text import tokenize, weighted_query_terms


RISK_KEYWORDS = {
    "auth": ["auth", "login", "logout", "session", "role", "jwt", "oauth"],
    "payments": ["payment", "stripe", "refund", "checkout", "invoice", "subscription", "billing"],
    "database": ["database", "schema", "migration", "prisma", "sql"],
    "api contracts": ["api", "route", "endpoint", "dto", "schema", "response", "request"],
    "notifications": ["email", "notification", "webhook", "sms"],
    "files": ["upload", "download", "csv", "export", "import", "file"],
    "deployment": ["deploy", "docker", "env", "config", "secret"],
}

CONFIG_HINTS = {
    "docker": ["Dockerfile", "docker-compose.yml"],
    "env": [".env", "config", "settings"],
    "config": ["config", "settings"],
    "deploy": ["Dockerfile", "Procfile", "wrangler", "vercel", "netlify"],
    "database": ["schema", "migration", "prisma"],
    "migration": ["schema", "migration", "prisma"],
    "stripe": ["stripe"],
    "auth": ["auth", "session", "middleware"],
}

TEST_MATCH_STOP_TERMS = {
    "app",
    "backend",
    "component",
    "components",
    "frontend",
    "helper",
    "helpers",
    "hook",
    "hooks",
    "index",
    "lib",
    "screen",
    "service",
    "services",
    "src",
    "test",
    "tests",
    "types",
    "ui",
    "util",
    "utils",
}


def score_files(files: list[SourceFile], request: str, top_n: int) -> list[FileScore]:
    query = weighted_query_terms(request)
    direct_scores: list[FileScore] = []

    for source in files:
        score, reasons = _score_file(source, query)
        if score > 0:
            direct_scores.append(FileScore(source, score, reasons))

    relation_boosts, related = _dependency_boosts(files, direct_scores)
    by_path = {item.file.relative_path: item for item in direct_scores}
    for path, boost in relation_boosts.items():
        if path in by_path:
            by_path[path].score += boost
            by_path[path].reasons.append(f"related through imports (+{boost:.1f})")
        else:
            source = next((file for file in files if file.relative_path == path), None)
            if source:
                by_path[path] = FileScore(source, boost, [f"related through imports (+{boost:.1f})"])

    for path, relations in related.items():
        if path in by_path:
            by_path[path].related_files = sorted(relations)[:8]

    ranked = sorted(by_path.values(), key=lambda item: item.score, reverse=True)
    return ranked[:top_n]


def suggest_tests(files: list[SourceFile], top_files: list[FileScore], package_scripts: dict[str, str]) -> list[str]:
    suggestions: list[str] = []

    preferred_scripts = [
        name
        for name in ("test", "test:unit", "test:integration", "test:e2e", "lint", "typecheck")
        if name in package_scripts
    ]
    for name in preferred_scripts:
        suggestions.append(f"Run package script `{name}`: {package_scripts[name]}")

    test_files = [file for file in files if file.is_test]
    top_terms = set()
    for scored in top_files:
        top_terms.update(tokenize(scored.file.relative_path))
        top_terms.update(tokenize(" ".join(scored.file.symbols[:20])))
    top_terms = {term for term in top_terms if term not in TEST_MATCH_STOP_TERMS and len(term) > 2}

    matched_tests: list[tuple[int, SourceFile]] = []
    for test in test_files:
        test_terms = {
            term for term in tokenize(test.relative_path) if term not in TEST_MATCH_STOP_TERMS and len(term) > 2
        }
        overlap = len(top_terms & test_terms)
        if overlap:
            matched_tests.append((overlap, test))

    for _, test in sorted(matched_tests, key=lambda item: item[0], reverse=True)[:8]:
        suggestions.append(f"Inspect or run related test `{test.relative_path}`")

    if not suggestions:
        if any(file.extension == ".py" for file in files):
            suggestions.append("No matching test file found. Try `python3 -m unittest` or `pytest` if this repo uses pytest.")
        elif any(file.extension in {".ts", ".tsx", ".js", ".jsx"} for file in files):
            suggestions.append("No matching test file found. Check package scripts for the repo's preferred JS test runner.")
        else:
            suggestions.append("No matching test file found. Add focused coverage around the highest-ranked impacted file.")

    return dedupe(suggestions)


def build_plan(request: str, top_files: list[FileScore]) -> list[str]:
    if not top_files:
        return [
            "Clarify the change request with exact feature area, expected behavior, and examples.",
            "Search the repo manually for the domain terms in the request.",
            "Add or update a focused test before changing behavior.",
        ]

    implementation_files = [
        score
        for score in top_files
        if not score.file.is_test and score.file.extension not in {".md", ".mdx", ".rst"}
    ]
    primary_score = implementation_files[0] if implementation_files else top_files[0]
    primary = primary_score.file.relative_path
    supporting = [score.file.relative_path for score in implementation_files[1:4]]

    plan = [
        f"Open `{primary}` first and decide whether it owns the requested behavior or only calls into another file.",
        "Follow its imports/callers into the related files before editing so the change lands at the owner, not just the highest-ranked match.",
        "Make the smallest implementation change in the owner file, then adjust supporting UI/hooks/services only if the first edit requires it.",
        "Use the ranked list as a checklist: edit primary owner, inspect supporting files for side effects, ignore files whose action says conditional-only.",
        "Run or add the closest focused test, then run the repo's broader test/lint command if available.",
    ]
    if supporting:
        plan.insert(1, f"Keep these supporting files open while tracing side effects: {', '.join(f'`{path}`' for path in supporting)}.")
    if any(score.file.routes for score in top_files):
        plan.insert(2, "Check the matched routes for request/response contracts and downstream consumers.")
    if any("schema" in score.file.relative_path.lower() or score.file.extension == ".sql" for score in top_files):
        plan.insert(2, "Review schema or migration impact before changing application code.")
    if _looks_like_ui_change(request, top_files):
        plan.insert(2, "For UI interaction work, verify gesture/tap/keyboard layering and check that nearby overlays still receive input correctly.")
    return plan


def identify_risks(request: str, top_files: list[FileScore]) -> list[str]:
    terms = set(tokenize(request))
    paths = " ".join(score.file.relative_path.lower() for score in top_files)
    risks: list[str] = []

    for label, keywords in RISK_KEYWORDS.items():
        if terms.intersection(keywords) or any(keyword in paths for keyword in keywords):
            risks.append(_risk_sentence(label))

    if not risks:
        risks.append("No obvious high-risk domain detected. Main risk is missing a caller or test outside the matched files.")
    return risks


def _score_file(source: SourceFile, query: Counter[str]) -> tuple[float, list[str]]:
    path_terms = tokenize(source.relative_path)
    path_counts = Counter(path_terms)
    text_lower = source.text.lower()
    symbol_terms = tokenize(" ".join(source.symbols))
    route_terms = tokenize(" ".join(source.routes))

    score = 0.0
    reasons: list[str] = []

    path_hits = []
    for term, weight in query.items():
        if term in path_counts:
            amount = 9.0 * weight * path_counts[term]
            score += amount
            path_hits.append(term)

    if path_hits:
        reasons.append(f"path matches: {', '.join(sorted(set(path_hits))[:8])}")

    symbol_hits = sorted(set(symbol_terms) & set(query))
    if symbol_hits:
        amount = 5.0 * sum(query[term] for term in symbol_hits)
        score += amount
        reasons.append(f"symbol matches: {', '.join(symbol_hits[:8])}")

    route_hits = sorted(set(route_terms) & set(query))
    if route_hits:
        amount = 7.0 * sum(query[term] for term in route_hits)
        score += amount
        reasons.append(f"route matches: {', '.join(route_hits[:8])}")

    content_hits = []
    for term, weight in query.items():
        count = len(re.findall(rf"\b{re.escape(term)}\b", text_lower))
        if count:
            capped = min(count, 12)
            amount = math.log1p(capped) * 2.2 * weight
            score += amount
            content_hits.append(f"{term}({count})")

    if content_hits:
        reasons.append(f"content matches: {', '.join(content_hits[:8])}")

    config_bonus = _config_bonus(source, query)
    if config_bonus:
        score += config_bonus
        reasons.append(f"configuration/domain hint (+{config_bonus:.1f})")

    if source.is_test:
        if _query_wants_tests(query):
            score *= 0.9
            reasons.append("test file, prompt mentions tests")
        else:
            score *= 0.45
            reasons.append("test file, ranked lower than implementation files")

    if source.extension in {".md", ".mdx", ".rst"} and not _query_wants_docs(query):
        score *= 0.35
        reasons.append("documentation file, ranked lower unless docs are requested")

    if source.line_count > 800:
        score *= 0.9
        reasons.append("large file, inspect carefully")

    return score, reasons


def _config_bonus(source: SourceFile, query: Counter[str]) -> float:
    relative = source.relative_path.lower()
    bonus = 0.0
    for term, hints in CONFIG_HINTS.items():
        if term not in query:
            continue
        if any(hint.lower() in relative for hint in hints):
            bonus += 4.0
    return bonus


def _query_wants_tests(query: Counter[str]) -> bool:
    return bool(set(query).intersection({"test", "tests", "spec", "coverage", "qa"}))


def _query_wants_docs(query: Counter[str]) -> bool:
    return bool(set(query).intersection({"doc", "docs", "documentation", "readme", "changelog"}))


def _looks_like_ui_change(request: str, top_files: list[FileScore]) -> bool:
    terms = set(tokenize(request))
    paths = " ".join(score.file.relative_path.lower() for score in top_files)
    return bool(
        terms.intersection({"ui", "screen", "button", "control", "gesture", "pinch", "tap", "layout", "style"})
        or any(part in paths for part in ("component", ".tsx", "screen", "page", "view"))
    )


def _dependency_boosts(
    files: list[SourceFile], direct_scores: list[FileScore]
) -> tuple[dict[str, float], dict[str, set[str]]]:
    path_by_stem = defaultdict(list)
    for file in files:
        path = Path(file.relative_path)
        path_by_stem[path.stem].append(file.relative_path)
        path_by_stem[path.name].append(file.relative_path)

    import_edges: dict[str, set[str]] = defaultdict(set)
    reverse_edges: dict[str, set[str]] = defaultdict(set)

    for file in files:
        for imported in file.imports:
            for resolved in _resolve_import(imported, file.relative_path, path_by_stem):
                if resolved != file.relative_path:
                    import_edges[file.relative_path].add(resolved)
                    reverse_edges[resolved].add(file.relative_path)

    boosts: dict[str, float] = defaultdict(float)
    related: dict[str, set[str]] = defaultdict(set)
    seeds = sorted(direct_scores, key=lambda item: item.score, reverse=True)[:15]
    for seed in seeds:
        base = min(seed.score * 0.16, 8.0)
        for neighbor in import_edges[seed.file.relative_path]:
            boosts[neighbor] += base
            related[neighbor].add(seed.file.relative_path)
            related[seed.file.relative_path].add(neighbor)
        for neighbor in reverse_edges[seed.file.relative_path]:
            boosts[neighbor] += base * 0.85
            related[neighbor].add(seed.file.relative_path)
            related[seed.file.relative_path].add(neighbor)

    return dict(boosts), related


def _resolve_import(imported: str, from_path: str, path_by_stem: dict[str, list[str]]) -> list[str]:
    if imported.startswith("."):
        base = Path(from_path).parent
        normalized = (base / imported.replace(".", "/")).as_posix()
        candidates = []
        for key, paths in path_by_stem.items():
            if normalized.endswith(key):
                candidates.extend(paths)
        return candidates[:5]

    last = imported.split("/")[-1].split(".")[-1]
    return path_by_stem.get(last, [])[:5]


def _risk_sentence(label: str) -> str:
    return {
        "auth": "Auth-related change: verify permissions, redirects, sessions, and unauthorized states.",
        "payments": "Payment-related change: verify idempotency, webhook behavior, refunds, invoices, and provider edge cases.",
        "database": "Database-related change: check migrations, seed data, rollback behavior, and query compatibility.",
        "api contracts": "API contract change: verify request/response shape, validation, client consumers, and backward compatibility.",
        "notifications": "Notification change: verify duplicate sends, retries, provider failures, and user-visible copy.",
        "files": "File import/export change: verify encoding, large files, empty files, and permission boundaries.",
        "deployment": "Deployment/config change: verify environment variables, secrets, build output, and production defaults.",
    }[label]


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
