from __future__ import annotations

import re
from pathlib import Path

from .text import split_identifier


IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
    re.compile(r"^\s*import\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
    re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)"),
    re.compile(r"^\s*from\s+([A-Za-z0-9_\.]+)\s+import\s+", re.MULTILINE),
    re.compile(r"^\s*import\s+([A-Za-z0-9_\.]+)", re.MULTILINE),
]

ROUTE_PATTERNS = [
    re.compile(r"\b(?:app|router|server)\.(?:get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"@(?:Get|Post|Put|Patch|Delete|Controller)\(\s*['\"]?([^'\"\)]*)['\"]?\s*\)"),
    re.compile(r"@(?:app|router)\.(?:get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]"),
]

SYMBOL_PATTERNS = [
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", re.MULTILINE),
    re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", re.MULTILINE),
    re.compile(r"^\s*(?:export\s+)?(?:interface|type)\s+([A-Za-z_$][\w$]*)", re.MULTILINE),
    re.compile(r"^\s*def\s+([A-Za-z_][\w]*)", re.MULTILINE),
    re.compile(r"^\s*class\s+([A-Za-z_][\w]*)", re.MULTILINE),
]

TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|__tests__|specs?)/|"
    r"(\.test|\.spec)\.[A-Za-z0-9]+$|"
    r"(^|/)test_[A-Za-z0-9_]+\.py$|"
    r"(^|/)[A-Za-z0-9_]+_test\.py$"
)


def extract_imports(text: str) -> tuple[str, ...]:
    imports: set[str] = set()
    for pattern in IMPORT_PATTERNS:
        imports.update(match.group(1) for match in pattern.finditer(text))
    return tuple(sorted(imports))


def extract_routes(text: str, path: Path) -> tuple[str, ...]:
    routes: set[str] = set()
    for pattern in ROUTE_PATTERNS:
        routes.update(match.group(1) or "/" for match in pattern.finditer(text))

    parts = path.parts
    if "app" in parts and path.name in {"page.tsx", "page.jsx", "route.ts", "route.js"}:
        app_index = parts.index("app")
        route_parts = []
        for part in parts[app_index + 1 : -1]:
            if part.startswith("(") and part.endswith(")"):
                continue
            route_parts.append(part)
        if route_parts:
            routes.add("/" + "/".join(route_parts))
    return tuple(sorted(routes))


def extract_symbols(text: str) -> tuple[str, ...]:
    symbols: set[str] = set()
    for pattern in SYMBOL_PATTERNS:
        for match in pattern.finditer(text):
            symbols.add(match.group(1))
            symbols.update(split_identifier(match.group(1)))
    return tuple(sorted(symbols))


def is_test_path(relative_path: str) -> bool:
    return bool(TEST_PATH_RE.search(relative_path))

