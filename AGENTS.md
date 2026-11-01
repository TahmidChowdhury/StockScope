# StockScope agent workflow

The primary agent owns scope, integration, and delivery. Start each change with a user-visible outcome and a way to verify it. In a multi-feature discussion, identify the current slice before editing. Treat later ideas as backlog until requested.

## Assignments

Handle single-file tasks directly when practical. For independent work, the orchestrator may assign at most two workers at once. Give each the worktree, files it owns, acceptance criteria, and checks to run. Each file has one writer. Workers return to the orchestrator if the change requires expanding ownership.

- Use research_surface for a bounded UI change on the desk, company page, or a related navigation path.
- Use evidence_reviewer for a read-only check of data provenance, missing values, interactions, and regression coverage.

Only the primary agent creates branches, stages commits, opens PRs, or starts additional work. Inspect existing diffs first and isolate concurrent edits in separate worktrees. A worker finishes its assignment by reporting files changed, checks performed, and remaining gaps.

## Completion

Review the combined diff against the requested outcome. For market-data changes check timestamps, unavailable data, and provider usage. For interaction changes exercise the affected path, including keyboard or touch where relevant. Report unverified behavior explicitly. Stop when the agreed checks and deliverables are complete.
