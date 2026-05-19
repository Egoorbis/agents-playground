# Copilot Instructions

These principles guide all development in this repository.

## Code Quality

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python style; use `ruff` for linting and formatting.
- Use type annotations on every function signature and class attribute.
- Keep functions small and focused: a function should do one thing and do it well.
- Prefer explicit over implicit; avoid magic values — use named constants or enums.
- Write self-documenting code; add docstrings (Google-style) to every public module, class, and function.
- Avoid deep nesting; return early or raise exceptions to keep the happy path flat.
- Never suppress exceptions silently; log them with enough context to reproduce the problem.
- Use Pydantic models for all data structures that cross a boundary (I/O, API, config).

## Testing Standards

- Every module under `iam_rbac_reviewer/` must have a corresponding test file under `tests/`.
- Aim for **≥ 90 % line coverage** on the core analysis engine (`analyzer.py`, `tools.py`, `reporters.py`).
- Tests are named `test_<unit>_<scenario>` and grouped in classes named `Test<Unit>`.
- Use `pytest` with `pytest-cov`; run with `pytest --cov=iam_rbac_reviewer --cov-report=term-missing`.
- Mock external services (Azure AI Foundry, Azure Resource Graph) so tests run fully offline.
- Add at least one happy-path test, one edge-case test, and one failure-mode test per public function.
- Fixtures go in `tests/conftest.py`; keep test data in `tests/fixtures/`.

## User Experience & Output Consistency

- CLI commands follow the pattern `iam-rbac-reviewer <command> [OPTIONS]`.
- All CLI output respects `--output` flag values: `text` (default), `json`, `markdown`.
- Use [Rich](https://github.com/Textualize/rich) for human-readable terminal output (colour, tables, progress bars).
- Error messages are written to `stderr`; structured data to `stdout`.
- Every error message includes: what went wrong, why it happened, and how to fix it.
- Report findings are always sorted by severity (CRITICAL → HIGH → MEDIUM → LOW → INFO).

## Performance Requirements

- Policy analysis for up to **500 IAM roles** must complete in **< 30 seconds** on a standard laptop (M1/i7, 16 GB RAM).
- Foundry agent calls are async; use `asyncio` and `azure-ai-projects` async client throughout.
- Cache Azure Resource Graph query results for the lifetime of a single CLI invocation.
- Avoid loading the entire policy corpus into memory at once; stream/page API responses.
- Profile any new hot-path code with `cProfile` before merging if it touches the analyzer.

## Security Practices

- Never log or print credentials, tokens, or personally identifiable information.
- Load secrets from environment variables or Azure Key Vault — never hard-code them.
- Validate and sanitize all external input before passing it to the analysis engine.
- Dependency updates are reviewed for CVEs before merging (use `pip-audit`).

## Technology Stack

| Layer | Technology |
|---|---|
| Agent runtime | Azure AI Foundry (`azure-ai-projects`) |
| Language | Python ≥ 3.11 |
| Data validation | Pydantic v2 |
| CLI | Typer + Rich |
| HTTP client | httpx (async) |
| Testing | pytest, pytest-cov, pytest-asyncio |
| Linting / formatting | ruff |
| IAM data source | Azure Resource Graph (optional: JSON/YAML file) |
