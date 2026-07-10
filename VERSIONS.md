# Kliamka Version History

## Unreleased

## 0.8.0

### Performance

- Parser construction now caches schema-dependent argument plans and prebuilt argparse
  parser/action templates. Every `create_parser()` call still returns fresh parser, action,
  group, and mutable container objects, preserving parser isolation and public behavior.
- Complete CLI namespaces use a safe fast path through Pydantic's compiled validator when
  the model configuration permits it. Calls requiring environment/default resolution or
  different extra-field handling retain the general validation path.
- The benchmark suite's primary geometric-mean timing improved from `47.7634 µs` to
  `12.3445 µs` (about 74.2%). Across matched argparse workloads, the aggregate Kliamka
  timing is approximately `0.32×` argparse. Timings remain environment-dependent.
- Parser caching, help behavior, converter invalidation, object isolation, and package
  installation were verified on Python 3.11, 3.12, 3.13, and 3.14.

### Benchmark tooling

- Added the opt-in `--benchmark-compare-libraries` pytest option. It appends a median-time
  table with equivalent workloads as rows and argparse, Kliamka, Click, and Typer as
  columns, including argparse-relative ratios and placeholders for unavailable libraries.
- Existing benchmark names, timed bodies, JSON identities, and default pytest-benchmark
  output remain unchanged when the option is not supplied.

## 0.7.1

### Bug fixes

- **PEP 604 union support** — `bool | None` / `int | None` annotations (as shown in the
  README Quick Start) no longer crash `create_parser()` with
  `ValueError: ... is not callable`; both `typing.Optional[X]` and `X | None` work
- **Hyphenated positional arguments** — `KliamkaArg("input-file", positional=True)` now
  round-trips through `from_args()` instead of losing the supplied value
- **CLI > ENV precedence** — an argument explicitly given on the command line now always
  wins, even when its value equals the declared default (previously a set env var would
  silently override it); internally, parsers now register an `UNSET` sentinel as the
  argparse default and `from_args()` resolves CLI > ENV > default explicitly
- **Bool flags with `default=True`** — a falsy environment variable (e.g. `DEBUG=false`)
  now overrides the default as documented
- **Clean errors for bad environment values** — invalid env var values (failed converters,
  invalid enum names) now raise `KliamkaError` naming the variable, and render as a
  standard `error:` line through the decorators instead of a traceback
- **Subcommand argument collisions fail fast** — sharing a namespace destination between
  the main class and a subcommand now raises `KliamkaError` at decoration time, including
  collisions with ordinary Pydantic fields (argparse silently clobbered the main value);
  the `_command` destination is reserved
- **Env-var lists honor per-field `converter=`** — comma-separated env values are now
  converted per element exactly like CLI tokens

### Behavior notes

- Namespaces returned by a raw `create_parser().parse_args()` now carry the
  `<kliamka.UNSET>` sentinel (falsy) for arguments that were not provided; defaults are
  applied by `from_args()`. Code using the decorators or `from_args()` is unaffected.
- Explicitly passing a list flag with zero values (e.g. `--files`) now counts as
  a provided empty list and overrides env/default values.
- Raw argparse namespaces now use model field names as destinations. This prevents
  normalized option spellings such as `--foo-bar` and `--foo_bar` from sharing a value.

### Quality improvements

- Wider unions such as `int | str` are rejected clearly; only `Optional[T]` / `T | None`
  unions are supported.
- Main and per-subcommand `ParserMeta` usage, prog, epilog, and version settings are honored,
  including when post-parse validation errors render usage.
- Environment boolean parsing is strict, conversion and validation errors name their source
  variable, and explicitly empty environment values override defaults.
- Shared parser type resolution removes positional/optional duplication, and obsolete
  Pydantic v1 `__root__` filtering was removed.

### Packaging and release automation

- Removed the redundant `wheel` build dependency and packaging-smoke bootstrap entry,
  applying [PR #3](https://github.com/hotsyk/kliamka/pull/3) proposed by
  [@webknjaz](https://github.com/webknjaz).
- Removed the duplicate Ruff target-version setting, incorporating merged
  [PR #5](https://github.com/hotsyk/kliamka/pull/5) by
  [@webknjaz](https://github.com/webknjaz); Ruff now derives it from `requires-python`.
- Distribution construction and smoke tests now run in a separate least-privileged job;
  only verified artifacts reach the OIDC publishing job, and CI now runs Zizmor workflow
  security analysis. This implements [issue #4](https://github.com/hotsyk/kliamka/issues/4),
  requested by [@webknjaz](https://github.com/webknjaz).
- Package metadata now identifies the modified license as `LicenseRef-MIT-NORUS`, and the
  setuptools floor is 77 for PEP 639 `license-files` support.

## 0.6.0

### New features

- **Custom type converters** — register global converters or provide per-field overrides for CLI args and environment variables
  ```python
  from kliamka import register_converter, KliamkaArg
  from pathlib import Path

  register_converter(Path, Path)  # global

  class Args(BaseModel):
      config: Path = KliamkaArg("--config", "Config file")
      tags: list[str] = KliamkaArg("--tags", "Tags", converter=lambda s: s.split(","))
  ```
  - `register_converter()` / `unregister_converter()` for global type registration
  - `converter=` parameter on `KliamkaArg` for per-field overrides
  - 5-step resolution order: explicit converter → global registry → enum → `List[T]` → fallback
  - See `examples/custom_converters.py`

- **Python 3.14 support** — added to the CI test matrix

- **Docker-based multi-Python testing** — `docker-compose.test.yml` runs the suite across supported interpreters

- **Packaging smoke tests** — validate wheel/sdist builds in `tests/test_packaging_smoke.py`

### Improvements

- **Package restructure** — moved from single-file `src/kliamka.py` to a proper `src/kliamka/` package split into focused modules (`_core`, `_parser`, `_decorators`, `_helpers`, `_converters`)
- **Cleaner error output** — stripped Pydantic error prefixes so CLI validation messages are user-friendly
- **Public API hygiene** — internal helpers no longer leak through `__init__.py`
- **Test isolation** — improved `sys.path` management in the test suite
- **CI updates** — publish workflow and CI pipeline refinements
- **Expanded README** — documents custom converters and new 0.6 features

## 0.5.0

### New features

- **Short flags** — define `-v` alongside `--verbose` via `short="-v"` parameter
  ```python
  verbose: bool | None = KliamkaArg("--verbose", "Verbose", short="-v")
  ```

- **Help customization** — `ParserMeta` class for program name, usage, epilog, and `--version`
  ```python
  parser_meta = ParserMeta(prog="myapp", version="myapp 1.0", epilog="See docs.")
  ```

- **`--version` flag** — automatically added when `version` is set in `ParserMeta`

- **Mutually exclusive argument groups** — prevents conflicting flags
  ```python
  json_out: bool | None = KliamkaArg("--json", "JSON", mutually_exclusive="format")
  csv_out: bool | None = KliamkaArg("--csv", "CSV", mutually_exclusive="format")
  ```

- **Pydantic validation** — `@model_validator` for range checks, cross-field validation, regex
  ```python
  @model_validator(mode="after")
  def validate_port(self) -> "MyArgs":
      if self.port is not None and not (1 <= self.port <= 65535):
          raise ValueError(f"Port must be 1-65535, got {self.port}")
      return self
  ```

- **Programmatic argv** — pass custom argument lists for testing/embedding
  ```python
  @kliamka_cli(MyArgs, argv=["--verbose", "--count", "5"])
  ```

- **PEP 561 `py.typed` marker** — ships type information for downstream consumers

### Improvements

- Migrated from `setup.py` to `pyproject.toml` (PEP 621)
- Eliminated major code duplication between `create_parser()` and `_populate_parser()`
- Added `__all__` to prevent internal helpers from leaking as public API
- Fixed version mismatch (`__version__` was `"0.2.0"` while package was `0.4.0`)
- Replaced fragile bool type detection with robust `_is_bool_annotation()` helper
- Makefile uses `.venv/bin/` prefix for reliable tool invocations
- Benchmarks now run in GitHub Actions CI
- README fully rewritten to document all features
- Test count: 60 → 96 (+36 new tests)

## 0.4.0

New features:

- **Benchmark suite** - Performance comparison with other CLI libraries
  ```bash
  python benchmark/run_benchmarks.py --table
  ```
- Compares kliamka vs argparse, click, and typer
- Markdown table output for easy documentation
- Auto-installs pytest-benchmark dependency

## 0.3.0

New features:

- **Positional arguments support** - Arguments without `--` prefix
  ```python
  filename: str = KliamkaArg("filename", "Input file", positional=True)
  ```

- **List/array arguments support** - Multiple values with `List[T]` type
  ```python
  files: List[str] = KliamkaArg("--files", "Input files")
  ```

- **Environment variable fallback** - CLI > ENV > default priority
  ```python
  api_key: str = KliamkaArg("--api-key", "API key", env="API_KEY")
  ```

- **Subcommands support** - Git-style CLI with `@kliamka_subcommands`
  ```python
  @kliamka_subcommands(MainArgs, {"add": AddArgs, "remove": RemoveArgs})
  def main(args, command, cmd_args):
      ...
  ```

## 0.2.0

- Added Enum support (string and integer valued enums)
- Enum parsing by name or value
- Improved type handling

## 0.1.0

- Initial release
- Basic CLI argument parsing with Pydantic validation
- Support for string, int, bool argument types
- `@kliamka_cli` decorator for automatic argument injection
- Optional arguments with default values
