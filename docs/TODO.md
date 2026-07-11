# TODO — Development Log

Central task tracker and development log for kliamka.

## Current Tasks

- [x] Publish comprehensive MkDocs documentation through GitHub Pages and add local strict-build commands
- [x] Add opt-in pytest benchmark library-column comparison output
- [x] Autoresearch: improve general parser creation and parsing performance against
  argparse/click/typer while preserving behavior and passing the full quality suite
- [x] Work through the bug backlog in [PLAN.md](https://github.com/hotsyk/kliamka/blob/main/PLAN.md) (2026-07-06 code review) —
  all seven section-1 bugs fixed on 2026-07-07
- [x] Resolve PLAN.md code-quality items 2.1–2.9 (2.3 was already fixed)
- [x] Fix license metadata mismatch before the next PyPI release (PLAN 3.1/3.2)
- [x] Flesh out `docs/20260408_product_requirements.md` for the 0.8.x baseline
- [x] Prepare package metadata and changelog for version 0.8.0
- [x] Merge version 0.8.0 to `main` and complete GitHub Release and PyPI publication

## Development Log

### 2026-07-10 — Added comprehensive documentation and GitHub Pages deployment
- Added a Material for MkDocs site covering setup, arguments, environment variables,
  subcommands, converters, validation, parser customization, the public API, examples,
  troubleshooting, and contributor workflows.
- Added `make docs` for the same strict clean build used in automation and
  `make docs-serve` for local live preview; documentation dependencies are isolated in
  the `docs` optional dependency group and installed by `make init-dev`.
- Added a least-privilege, SHA-pinned GitHub Pages workflow for pushes/merges to `main`
  and `master`, plus manual dispatch. Pages artifacts are deployed without writing
  generated files to a branch.
- Decision: retain the explicitly requested `master` trigger while also supporting
  `main`, which is the repository's actual default branch.
- Verified the strict MkDocs build, 35 executable Python documentation snippets,
  165 unit tests, 2 packaging smoke tests, mypy/Ruff checks, workflow YAML parsing,
  pinned action revisions, and a clean Zizmor audit.

### 2026-07-10 — Prepared version 0.8.0 for release
- Bumped project metadata, public version, and package smoke-test assertions to 0.8.0.
- Added the 0.8.0 changelog covering general parser/validation performance improvements,
  preserved fresh-object semantics, Python 3.11–3.14 verification, and the opt-in
  cross-library benchmark report.
- Kept `Unreleased` open for future changes; no tag, GitHub Release, or PyPI publication
  was created from this branch.

### 2026-07-10 — Added opt-in cross-library benchmark table
- Added `--benchmark-compare-libraries` for a workload-by-library median table after
  pytest-benchmark's normal report, including argparse-relative ratios and placeholders
  for unavailable Click/Typer workloads.
- Added separate comparison metadata markers without renaming tests, changing timed
  bodies, or altering default pytest-benchmark grouping and JSON identities.
- Added focused formatting/table tests and documented the exact invocation.

### 2026-07-09 — Completed performance autoresearch
- Reduced the primary geometric-mean metric from 47.7634us to 12.3445us (74.2%).
- Matched argparse ratio improved from 1.273 to 0.320; Kliamka is about 3.1x faster in
  the matched aggregate and remains substantially faster than Click/Typer parsing.
- Main wins: compiled/cloned argparse state and Actions, lazy help materialization,
  a complete-CLI validation fast path, and direct compiled Pydantic validation.
- Verified unit/lint/type/format checks after every kept run; packaging smoke tests,
  dedicated cache/help isolation checks, and Python 3.11–3.14 Docker matrices pass.
- Benchmark sources, competitor code, metric calculation, dependency versions, and
  runtime settings were unchanged.

### 2026-07-09 — Started performance autoresearch
- Established the supplied pytest-benchmark suite as the immutable workload.
- Chose the geometric mean of all nine Kliamka benchmark medians as the primary metric,
  with category timings and cross-library ratios as diagnostics.
- Guardrails: benchmark sources and metric computation are off limits; unit tests, mypy,
  Ruff lint, and formatting checks run after every successful benchmark.
- Current kept implementation verified on Python 3.11, 3.12, 3.13, and 3.14 Docker images;
  packaging smoke tests and dedicated cache/help isolation checks also pass.

### 2026-07-09 — Prepared version 0.7.1 for release
- Retargeted the release from 0.7.0 to 0.7.1 after the partial 0.7.0 workflow run created
  a tag but did not create a GitHub Release or publish to PyPI.
- Bumped package metadata, public version, and version assertions to 0.7.1; moved the
  accumulated release notes into the 0.7.1 changelog section.
- Applied [PR #3](https://github.com/hotsyk/kliamka/pull/3) (`wheel` cleanup) and merged
  [PR #5](https://github.com/hotsyk/kliamka/pull/5) (Ruff target-version cleanup), with
  contributor attribution in `VERSIONS.md`.
- Implemented [issue #4](https://github.com/hotsyk/kliamka/issues/4): distributions are
  built and smoke-tested without OIDC permission, then passed as artifacts to separate
  release and trusted-publishing jobs; CI now includes Zizmor security analysis.
- Corrected the license expression to `LicenseRef-MIT-NORUS`, removed the inaccurate MIT
  classifier, and raised the setuptools floor to 77 for PEP 639 support.
- Addressed PR #6 security review: all workflow actions are pinned to immutable SHAs, and
  GitHub releases use the runner-provided `gh` CLI instead of a redundant action.
- Made release automation resumable after partial failure: existing tags are verified,
  missing GitHub/PyPI releases remain actionable, and `--generate-notes` works with `--repo`.
- Verified: 158 unit tests and 2 isolated wheel/sdist smoke tests pass; mypy, Ruff,
  formatting, all seven examples, workflow YAML parsing, built release license metadata,
  and Zizmor auditing are clean.

### 2026-07-09 — Resolved PLAN.md code-quality items 2.1–2.9
- Unsupported wide unions now fail cleanly; `Optional[T]` and `T | None` remain supported.
- Main and per-subcommand `ParserMeta` settings are honored, including subcommand-specific
  usage/prog when rendering post-parse validation errors.
- ENV conversion and Pydantic validation errors identify their source variable; boolean
  parsing is strict and documented; empty ENV values count as provided.
- `KliamkaArg.name` is now the canonical argparse destination, preventing normalized-name
  collisions; main/subcommand collision checks also cover ordinary Pydantic fields when
  either side is CLI-backed. Parser type-resolution duplication was extracted.
- Removed Pydantic v1 `__root__` filtering and added focused regression coverage.
- Verified: 158 unit tests and 2 packaging smoke tests pass; mypy/Ruff/formatting are
  clean; all seven examples run with their required sample arguments.

### 2026-07-07 — Fixed all confirmed bugs from the review (PLAN.md section 1)
- TDD: added `tests/test_regressions.py` (22 tests, one class per bug); verified each
  failed for the documented reason before implementing.
- Core change: parsers now register an `_UNSET` sentinel as the argparse default and
  `from_args()` resolves CLI > ENV > default explicitly — this replaced the
  `_was_cli_provided()` equality heuristic and fixed PLAN 1.3, 1.4, and 2.3 together.
- PEP 604 unions handled via `get_origin`/`get_args` in `_helpers.py`; positional dests
  normalized (hyphens); env conversion errors wrapped into `KliamkaError` naming the
  variable; subcommand dest collisions rejected at decoration time (`_command` reserved);
  env list elements now honor per-field converters.
- Behavior note: raw `parse_args()` namespaces carry the falsy `<kliamka.UNSET>` sentinel
  for absent args; three legacy tests asserting raw-namespace defaults were rerouted
  through `from_args()`. Shared `clean_converter_registry` fixture moved to
  `tests/conftest.py`.
- Verified: 131 tests pass, mypy/ruff clean, all examples run, original bug repros
  re-executed against the fix.

### 2026-07-06 — Full code review
- Reviewed 0.6.0 (main @ ac819b3); baseline green: 109 tests, mypy, ruff.
- Seven bugs confirmed by execution, logged with repro details in [PLAN.md](https://github.com/hotsyk/kliamka/blob/main/PLAN.md).
  Most severe: the README Quick Start (`bool | None`) crashes `create_parser()`.
- `docs/` folder was missing despite being referenced from CLAUDE.md and README;
  created this file and the product requirements stub.

## Notes

### Technical Debt
- Performance branch audit pending: `_core.py` and `_parser.py` now exceed 300 lines after
  cached parser construction work; review private argparse compatibility across Python 3.11–3.14
  and extract cache-cloning internals if doing so does not regress benchmarks.
- Code audit completed 2026-07-09 after the staged change set crossed the ~500-line
  review threshold; remaining findings are tracked in PLAN.md sections 2.10–4.

### Recurring Issues
- Docs advertise both `Optional[X]` and `X | None`; retain regression coverage for both
  spellings whenever annotation handling changes.
