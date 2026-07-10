# Autoresearch: Make Kliamka faster than comparable CLI libraries

## Objective
Improve Kliamka's general-purpose parser creation, argument parsing, and model construction performance on the supplied benchmark suite. Close the gap to raw argparse and retain Kliamka's existing advantage over Click and Typer where applicable. Optimize production implementation paths, not benchmark-specific inputs or classes.

## Metrics
- **Primary**: `kliamka_geomean_us` (microseconds, lower is better) — geometric mean of the median runtime of all nine timed Kliamka benchmarks. Geometric mean balances creation, parsing, full-workflow, validation, and repeated-parsing workloads without allowing the millisecond-scale repeated benchmark to dominate by units alone.
- **Secondary**: `creation_geomean_us`, `parsing_geomean_us`, `full_geomean_us`, `validation_us`, `repeated_100_us`, `vs_argparse_ratio`, `vs_click_parsing_ratio`, and `vs_typer_parsing_ratio`.

## How to Run
`./.auto/measure.sh`

The benchmark command requested by the user is run unchanged:
`pytest benchmark/test_benchmark.py -v --benchmark-compare --benchmark-json=benchmark_results.json`

Pytest-benchmark already executes many rounds per test. The metric uses medians to limit noise and emits structured `METRIC` lines.

## Files in Scope
- `src/kliamka/_core.py` — parser creation entry point and `from_args` model construction.
- `src/kliamka/_parser.py` — argparse argument population and type/help configuration.
- `src/kliamka/_helpers.py` — annotation inspection and enum conversion helpers.
- `src/kliamka/_converters.py` — converter lookup and wrapping.
- `src/kliamka/_decorators.py` — full CLI/subcommand setup if a broadly useful optimization is found.
- `src/kliamka/__init__.py` — only if internal implementation changes require export adjustments.
- `tests/` — add general regression coverage when an optimization changes implementation structure or fixes a discovered issue; never weaken/delete tests.
- `docs/TODO.md` and `.auto/ideas.md` — development record and deferred experiments.

## Off Limits
- `benchmark/test_benchmark.py` and all other `benchmark/` sources.
- `.auto/measure.sh` metric membership, weighting, and benchmark command after baseline, except to fix a genuine measurement bug documented in the experiment log.
- `benchmark_results.json` as an implementation input.
- Test configuration, pytest-benchmark settings, competitor implementations, dependency versions, and machine/runtime settings.
- Benchmark-specific branches, class-name checks, input memoization, cached returned mutable parsers/models, or any behavior that gives the supplied benchmark classes special treatment.

## Constraints
- Preserve public API and documented semantics, including fresh independent parser objects from each `create_parser()` call.
- No new runtime dependencies.
- Do not cache mutable `ArgumentParser`, `Namespace`, or model instances across calls.
- Optimizations must generalize to normal user-defined `KliamkaArgClass` subclasses and annotation combinations.
- Every passing benchmark automatically runs unit tests, mypy, Ruff lint, and Ruff formatting checks via `.auto/checks.sh`.
- Keep only primary-metric improvements; discard unchanged/regressing experiments. Reconfirm small/noisy wins.

## What's Been Tried
- Baseline pending. Initial supplied results show Kliamka parser creation about 1.2x slower than equivalent argparse, parsing about 1.3–1.4x slower than argparse but substantially faster than Click/Typer, and `from_args` validation around 4.6 microseconds.
