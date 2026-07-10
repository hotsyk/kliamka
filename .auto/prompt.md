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
- **Baseline:** `kliamka_geomean_us=47.7634`, matched argparse ratio 1.273. Kliamka was already much faster than Click/Typer parsing.
- **Kept — complete-CLI fast path:** cached validated CLI field metadata and passed fully supplied namespaces through Pydantic without the env/default loop. Primary reached 43.7896; validation fell from 3.58us to 2.21us.
- **Kept — compiled parser recipes:** cache model-to-argparse argument recipes while allocating a fresh mutable parser. Explicit invalidation on `KliamkaArg` attribute writes and public converter registry changes replaced an expensive per-call signature. Primary reached 40.3072; creation fell to 88.15us.
- **Kept — avoid mapping copies:** pass namespace dictionaries directly when Pydantic's extra policy is default/ignore, while retaining filtering for allow/forbid. Primary reached 38.2466.
- **Kept — fast completeness/validation:** direct early-exit checks, compiled Pydantic validator calls, and cached `itemgetter` field access reduced validation to about 1.18us and primary to 35.9981.
- **Kept and reverse-confirmed — omit identity `str` converters for list tokens:** small win to 35.8413; restoring them regressed to 36.2670. Earlier omission for every scalar/list string had regressed and was discarded.
- **Kept — cached argparse Action templates:** compile model arguments once and clone independent Actions into every fresh parser. Primary reached 31.7368 and matched argparse ratio crossed below 1.0 (0.969).
- **Kept — cached help Action and empty parser state:** avoid repeated argparse locale/registry/group initialization while resetting all mutable parser containers and recomputing per-call metadata. Primary reached 17.9289; matched argparse ratio 0.511.
- **Kept — cloned empty positional/optional groups:** rebind fresh group objects directly to each parser's new mutable state. Current best primary is `16.5963`; creation 11.91us; full workflow 24.46us; matched argparse ratio 0.467.
- **Discarded twice — direct `Action.__dict__` cloning:** creation improved but suite primary reproducibly regressed; retain `copy.copy`. Direct manual `_add_action` replacement also regressed.
- **Kept — copy-equivalent fast Action reconstruction:** allocate the same Action class and update its existing `__dict__`, matching `copy.copy` semantics without reduction dispatch. Current direct-assignment/list-copy variant was discarded twice; this corrected variant cut primary to 14.7176.
- **Kept — direct help and prevalidated action attachment:** attach help to known-empty state and compile user/help conflicts once; parsers with extra preexisting actions (e.g. version) retain normal conflict handling. Primary reached 13.6909.
- **Kept — argv-aware prog memoization:** small general win. Current best is `kliamka_geomean_us=13.5365`, creation 6.33us, full workflow 18.74us, matched argparse ratio 0.373.
- **Discarded:** shared default ParserMeta, cached bound Pydantic validator, and precomputed negative-option flags all regressed primary/targeted metrics.
- Kliamka now beats argparse by about 2.7x in the matched geometric aggregate, while remaining roughly 5x faster than Click parsing and 19x faster than Typer parsing. Remaining raw parsing difference is principally the intentional validated model construction.
- **Later exploration under 4–5% machine drift:** full parser-graph prototype cloning, bulk group attachment, settings/validator caching, completeness specializations, SUPPRESS defaults, deferred-default parser subclassing, and several cloning micro-variants all failed strict primary acceptance. Two no-change controls measured 4.5–5.3% slower than the 13.5365 best; require a structural win above that margin.
- Packaging smoke tests also pass (wheel and sdist). Do not revisit the exhausted paths recorded in `.auto/log.jsonl` runs 28–49.
