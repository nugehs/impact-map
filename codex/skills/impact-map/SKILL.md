---
name: impact-map
description: Use when planning, scoping, or reviewing code changes in a local repository with the impact-map/change-impact-analyzer CLI or MCP server, especially to predict likely impacted files, tests, risks, import-neighbor files, or to validate predictions against a git diff.
---

# Impact Map

Use `impact-map` to get a deterministic first-pass map before broad, unfamiliar, cross-cutting, or high-risk code changes. Treat results as investigation leads, not proof. Always read the relevant code before editing.

## Source

The canonical skill source is backed by this repository at:

```bash
codex/skills/impact-map
```

If the analyzer repo is missing, restore it with:

```bash
git clone https://github.com/nugehs/impact-map /path/to/impact-map
```

If the installed skill is missing or stale, run this from an `impact-map` checkout:

```bash
codex/skills/impact-map/scripts/sync-installed.sh
```

## Workflow

1. Discover the target repo path from the user request or current workspace.
2. Run `impact-map` with the user-facing change request before editing when scope is unclear.
3. Inspect top candidates, related files, suggested tests, and risks.
4. Use `rg`, `rg --files`, repo scripts, and normal code reading to verify the map.
5. After a diff exists, re-run with `--diff-base` to catch missed changed files.

## Commands

Prefer the installed CLI:

```bash
impact-map /path/to/repo "add Stripe refunds to bookings" --top 12
cia /path/to/repo "fix auth redirect after login" --top 12
```

If the CLI is unavailable, run from the repo without installing:

```bash
cd /path/to/impact-map
PYTHONPATH=src python3 -m change_impact_analyzer.cli /path/to/repo "add Stripe refunds to bookings" --top 12
```

Use machine-readable output when another tool or script will consume it:

```bash
impact-map /path/to/repo "update booking cancellation policy" --json --top 12
```

Validate predictions after edits:

```bash
impact-map /path/to/repo "fix auth redirect after login" --diff-base HEAD
impact-map /path/to/repo "add Stripe refunds to bookings" --diff-base origin/main
```

## MCP Server

Run the local stdio MCP server from the analyzer repo:

```bash
cd /path/to/impact-map
PYTHONPATH=src python3 -m change_impact_analyzer.mcp_server
```

Tool: `analyze_change_impact`

Arguments:

- `repo`: local repository path
- `request`: plain-English code change request
- `top`: optional result count
- `max_files`: optional scan limit
- `diff_base`: optional git ref for validation
- `json`: optional machine-readable output

## Interpretation

- Top files are candidates to inspect or edit.
- Related files are import graph neighbors; check them for shared contracts and side effects.
- Suggested tests are starting points. Still use the target repo's own AGENTS.md, scripts, and CI conventions.
- Risk labels are prompts to verify areas such as auth, payments, database migrations, API contracts, mobile/web contracts, or deployment settings.
- `missed_changed_files` under `--diff-base` means the implementation touched files outside the predicted set; inspect whether that reveals hidden coupling or an incomplete map.

## Maintaining Impact Map

When editing the analyzer itself, run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

If entry points change in `pyproject.toml`, update this skill before syncing it into `~/.codex/skills`.
