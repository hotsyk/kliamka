# Kliamka Version History

## Unreleased

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
- **Subcommand argument collisions fail fast** — defining the same flag in the main class
  and a subcommand now raises `KliamkaError` at decoration time (argparse silently
  clobbered the main value); the `_command` destination is reserved
- **Env-var lists honor per-field `converter=`** — comma-separated env values are now
  converted per element exactly like CLI tokens

### Behavior notes

- Namespaces returned by a raw `create_parser().parse_args()` now carry the
  `<kliamka.UNSET>` sentinel (falsy) for arguments that were not provided; defaults are
  applied by `from_args()`. Code using the decorators or `from_args()` is unaffected.
- Explicitly passing a list flag with zero values (e.g. `--files`) now counts as
  a provided empty list and overrides env/default values.

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
