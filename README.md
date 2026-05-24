# impact-map

Change Impact Analyzer is a local CLI that reads a repository and a plain-English change request, then produces an impact report:

- likely files to inspect or edit
- why each file matched
- related files through imports
- tests that probably matter
- project and framework hints
- implementation plan and risk checks

This first version is deterministic. It does not call an AI model. That makes it fast, private, and easy to improve.

## Install

From this directory:

```bash
python3 -m pip install -e .
```

Then run:

```bash
cia /path/to/repo "add Stripe refunds to bookings"
```

You can also run without installing:

```bash
PYTHONPATH=src python3 -m change_impact_analyzer.cli /path/to/repo "add Stripe refunds to bookings"
```

## Options

```bash
cia /path/to/repo "fix auth redirect after login" --top 12
cia /path/to/repo "add CSV export for invoices" --json
cia /path/to/repo "update booking cancellation policy" --max-files 3000
```

## How it works

The analyzer:

1. Scans source-like files while skipping build output, dependencies, caches, and binary assets.
2. Extracts path tokens, identifiers, imports, routes, and test-file signals.
3. Scores files against the change request.
4. Boosts nearby files in the import graph.
5. Suggests existing tests and package test commands.
6. Flags common risk areas such as auth, payments, database changes, API contracts, and deployments.

## Current limits

- It uses heuristics, so it should guide investigation rather than replace engineering judgment.
- Import extraction covers common Python, JavaScript, TypeScript, React, and Node patterns.
- It does not edit code or open pull requests yet.

## Next useful upgrades

- Add an LLM summary layer on top of the deterministic report.
- Build a small web UI with clickable file links.
- Add AST parsers for deeper symbol and dependency tracking.
- Compare a git diff against the impact map for PR review.
- Teach it repo-specific rules through a `.cia.toml` file.
