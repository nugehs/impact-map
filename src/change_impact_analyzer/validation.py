from __future__ import annotations

import subprocess
from pathlib import Path

from .models import FileScore, ImpactValidation


def validate_against_diff(repo: Path, base: str, top_files: list[FileScore]) -> ImpactValidation:
    changed_files = _changed_files(repo, base)
    predicted = {item.file.relative_path for item in top_files}
    related = {path for item in top_files for path in item.related_files}

    changed = set(changed_files)
    confirmed_direct = sorted(changed & predicted)
    confirmed_related = sorted((changed & related) - predicted)
    missed_changed = sorted(changed - predicted - related)
    unconfirmed = sorted(predicted - changed)

    notes: list[str] = []
    if confirmed_direct:
        notes.append("At least one predicted file was changed, so the map has direct confirmation.")
    if confirmed_related:
        notes.append("Some changed files were not top predictions but were related to predicted files.")
    if unconfirmed:
        notes.append("Unchanged predicted files are not automatically false; they may be inspect-only or indirect impact.")
    if missed_changed:
        notes.append("Changed files outside the prediction/related set are possible false negatives and need review.")
    if not changed_files:
        notes.append("No git changes were found against the selected base.")

    if missed_changed:
        verdict = "needs_review"
    elif confirmed_direct or confirmed_related:
        verdict = "confirmed"
    elif changed_files:
        verdict = "not_confirmed"
    else:
        verdict = "no_changes"

    return ImpactValidation(
        base=base,
        changed_files=changed_files,
        confirmed_direct=confirmed_direct,
        confirmed_related=confirmed_related,
        unconfirmed_candidates=unconfirmed,
        missed_changed_files=missed_changed,
        verdict=verdict,
        notes=notes,
    )


def _changed_files(repo: Path, base: str) -> list[str]:
    tracked = _git_lines(repo, ["diff", "--name-only", "--relative", base, "--"])
    staged = _git_lines(repo, ["diff", "--cached", "--name-only", "--relative", "--"])
    untracked = _git_lines(repo, ["ls-files", "--others", "--exclude-standard"])
    return sorted(set(tracked + staged + untracked))


def _git_lines(repo: Path, args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
