from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .extractors import extract_imports, extract_routes, extract_symbols, is_test_path
from .models import ProjectProfile, SourceFile


SKIP_DIRS = {
    ".cache",
    ".gradle",
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".eas",
    ".expo",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".turbo",
    ".venv",
    ".worktrees",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "Pods",
    "target",
    "vendor",
    "venv",
}

SOURCE_EXTENSIONS = {
    ".astro",
    ".cjs",
    ".cljs",
    ".config",
    ".cs",
    ".css",
    ".go",
    ".graphql",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".md",
    ".mjs",
    ".php",
    ".prisma",
    ".py",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".svelte",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".vue",
    ".yaml",
    ".yml",
}

SPECIAL_FILENAMES = {
    "Dockerfile",
    "Gemfile",
    "Makefile",
    "Procfile",
    "docker-compose.yml",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "requirements.txt",
    "yarn.lock",
}


class RepoScanner:
    def __init__(self, root: Path, max_file_bytes: int = 300_000, max_files: int = 5000):
        self.root = root.resolve()
        self.max_file_bytes = max_file_bytes
        self.max_files = max_files
        self.skipped_count = 0

    def scan(self) -> tuple[ProjectProfile, list[SourceFile]]:
        if not self.root.exists():
            raise FileNotFoundError(f"Repository path does not exist: {self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"Repository path is not a directory: {self.root}")

        files: list[SourceFile] = []
        extensions: Counter[str] = Counter()

        for path in self._walk():
            if len(files) >= self.max_files:
                self.skipped_count += 1
                continue

            if not self._is_source_like(path):
                self.skipped_count += 1
                continue

            try:
                if path.stat().st_size > self.max_file_bytes:
                    self.skipped_count += 1
                    continue
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                self.skipped_count += 1
                continue

            relative = path.relative_to(self.root).as_posix()
            extension = path.suffix.lower() or path.name
            extensions[extension] += 1
            files.append(
                SourceFile(
                    path=path,
                    relative_path=relative,
                    extension=extension,
                    text=text,
                    line_count=text.count("\n") + 1,
                    imports=extract_imports(text),
                    routes=extract_routes(text, Path(relative)),
                    symbols=extract_symbols(text),
                    is_test=is_test_path(relative),
                )
            )

        profile = ProjectProfile(
            root=self.root,
            file_count=len(files),
            skipped_count=self.skipped_count,
            extensions=dict(extensions.most_common()),
            markers=self._detect_markers(),
            package_scripts=self._package_scripts(),
        )
        return profile, files

    def _walk(self):
        stack = [self.root]
        while stack:
            current = stack.pop()
            try:
                children = sorted(current.iterdir(), key=lambda child: child.name)
            except OSError:
                self.skipped_count += 1
                continue

            for child in children:
                if child.is_dir():
                    if child.name in SKIP_DIRS:
                        self.skipped_count += 1
                        continue
                    stack.append(child)
                elif child.is_file():
                    yield child

    def _is_source_like(self, path: Path) -> bool:
        return path.suffix.lower() in SOURCE_EXTENSIONS or path.name in SPECIAL_FILENAMES

    def _detect_markers(self) -> list[str]:
        markers: list[str] = []
        checks = {
            "Node/JavaScript": "package.json",
            "Python": "pyproject.toml",
            "Python requirements": "requirements.txt",
            "Ruby": "Gemfile",
            "Rust": "Cargo.toml",
            "Go": "go.mod",
            "Docker": "Dockerfile",
            "Prisma": "prisma/schema.prisma",
            "Next.js": "next.config.js",
            "Vite": "vite.config.ts",
            "Tailwind": "tailwind.config.js",
        }
        for label, relative in checks.items():
            if (self.root / relative).exists():
                markers.append(label)

        package_json = self.root / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
            deps = {}
            deps.update(data.get("dependencies", {}))
            deps.update(data.get("devDependencies", {}))
            dep_markers = {
                "React": "react",
                "Vue": "vue",
                "Svelte": "svelte",
                "NestJS": "@nestjs/core",
                "Express": "express",
                "Expo": "expo",
                "Stripe SDK": "stripe",
                "Prisma Client": "@prisma/client",
                "Jest": "jest",
                "Vitest": "vitest",
                "Playwright": "@playwright/test",
            }
            for label, dep in dep_markers.items():
                if dep in deps:
                    markers.append(label)
        return sorted(set(markers))

    def _package_scripts(self) -> dict[str, str]:
        package_json = self.root / "package.json"
        if not package_json.exists():
            return {}
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        scripts = data.get("scripts", {})
        if isinstance(scripts, dict):
            return {str(key): str(value) for key, value in scripts.items()}
        return {}
