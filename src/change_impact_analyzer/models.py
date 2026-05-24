from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SourceFile:
    path: Path
    relative_path: str
    extension: str
    text: str
    line_count: int
    imports: tuple[str, ...] = ()
    routes: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    is_test: bool = False


@dataclass
class FileScore:
    file: SourceFile
    score: float
    reasons: list[str] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)


@dataclass
class ProjectProfile:
    root: Path
    file_count: int
    skipped_count: int
    extensions: dict[str, int]
    markers: list[str]
    package_scripts: dict[str, str] = field(default_factory=dict)


@dataclass
class ImpactValidation:
    base: str
    changed_files: list[str]
    confirmed_direct: list[str]
    confirmed_related: list[str]
    unconfirmed_candidates: list[str]
    missed_changed_files: list[str]
    verdict: str
    notes: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    request: str
    profile: ProjectProfile
    top_files: list[FileScore]
    test_suggestions: list[str]
    implementation_plan: list[str]
    risks: list[str]
    validation: ImpactValidation | None = None
