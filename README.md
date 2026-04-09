[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner2-direct.svg)](https://stand-with-ukraine.pp.ua)

# Kliamka

A small Python CLI library that provides Pydantic-based argument parser with type safety.

For detailed specifications, see `CLAUDE.md`.

![PyPI - Version](https://img.shields.io/pypi/v/kliamka)

## Features

- **Type-safe CLI arguments** with Pydantic validation
- **Decorator-based design** for clean, readable code
- **Automatic argument parsing** from class definitions
- **Enum support** — string and integer valued enums, parsed by name or value
- **Positional arguments** — with optional defaults
- **List/array arguments** — `List[str]`, `List[int]`, `List[Enum]`
- **Environment variable fallback** — CLI > ENV > default priority
- **Subcommands** — git-style CLI with `@kliamka_subcommands`
- **Short flags** — `-v` alongside `--verbose`
- **Mutually exclusive groups** — e.g. `--json` vs `--csv`
- **`--version` flag** — automatic version display
- **Help customization** — program name, usage, epilog
- **Custom type converters** — per-argument `converter=` or a global `register_converter(type, fn)` registry
- **Pydantic validators** — range checks, cross-field validation, regex patterns
- **Programmatic argv** — pass custom argument lists for testing/embedding
- **PEP 561 compatible** — ships `py.typed` marker
- **Modern Python 3.11+** with full type hints

## Installation

```bash
pip install kliamka
```

## Quick Start

```python
from kliamka import KliamkaArg, KliamkaArgClass, kliamka_cli

class MyArgs(KliamkaArgClass):
    """My CLI application arguments."""
    verbose: bool | None = KliamkaArg("--verbose", "Enable verbose output", short="-v")
    count: int | None = KliamkaArg("--count", "Number of iterations", default=1, short="-c")

@kliamka_cli(MyArgs)
def main(args: MyArgs) -> None:
    if args.verbose:
        print("Verbose mode enabled")
    for i in range(args.count or 1):
        print(f"Iteration {i + 1}")

if __name__ == "__main__":
    main()
```

```bash
python my_app.py -v -c 3
```

## API Reference

### `KliamkaArg`

Descriptor for defining CLI arguments.

```python
KliamkaArg(
    flag: str,              # Flag name: "--verbose" or "filename"
    help_text: str = "",    # Help text
    default: Any = None,    # Default value
    positional: bool = False,  # Positional argument
    env: str | None = None,    # Environment variable fallback
    short: str | None = None,  # Short flag: "-v"
    mutually_exclusive: str | None = None,  # Exclusion group name
)
```

### `KliamkaArgClass`

Base class for CLI argument definitions using Pydantic models.

```python
class MyArgs(KliamkaArgClass):
    """Description shown in --help."""
    debug: bool | None = KliamkaArg("--debug", "Enable debug mode", short="-d")
    config: str | None = KliamkaArg("--config", "Config file path")
```

### `ParserMeta`

Customize help output and add `--version`:

```python
from kliamka import ParserMeta

class MyArgs(KliamkaArgClass):
    """My application."""
    parser_meta = ParserMeta(
        prog="myapp",
        usage="myapp [options] FILE",
        epilog="See https://example.com for docs.",
        version="myapp 1.0.0",
    )
    verbose: bool | None = KliamkaArg("--verbose", "Verbose", short="-v")
```

### `@kliamka_cli`

Decorator that parses CLI arguments and injects them as the first parameter.

```python
@kliamka_cli(MyArgs)
def main(args: MyArgs) -> None:
    pass

# Or with custom argv for testing:
@kliamka_cli(MyArgs, argv=["--verbose", "--count", "5"])
def main(args: MyArgs) -> None:
    pass
```

### `@kliamka_subcommands`

Decorator for git-style subcommand CLIs.

```python
from kliamka import kliamka_subcommands

class MainArgs(KliamkaArgClass):
    verbose: bool | None = KliamkaArg("--verbose", "Verbose output", short="-v")

class AddArgs(KliamkaArgClass):
    """Add a new item."""
    name: str = KliamkaArg("name", "Item name", positional=True)

class RemoveArgs(KliamkaArgClass):
    """Remove an item."""
    id: int = KliamkaArg("id", "Item ID", positional=True)
    force: bool | None = KliamkaArg("--force", "Force removal", short="-f")

@kliamka_subcommands(MainArgs, {"add": AddArgs, "remove": RemoveArgs})
def main(args: MainArgs, command: str, cmd_args) -> None:
    if command == "add":
        print(f"Adding {cmd_args.name}")
    elif command == "remove":
        print(f"Removing {cmd_args.id} (force={cmd_args.force})")
```

## Feature Examples

### Enum Arguments

```python
from enum import Enum

class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    ERROR = "error"

class MyArgs(KliamkaArgClass):
    level: LogLevel = KliamkaArg("--level", "Log level", LogLevel.INFO)
```

Accepts `--level debug`, `--level DEBUG`, or `--level info`.

### Environment Variable Fallback

```python
class MyArgs(KliamkaArgClass):
    api_key: str | None = KliamkaArg("--api-key", "API key", env="MY_API_KEY")
    debug: bool | None = KliamkaArg("--debug", "Debug mode", env="DEBUG")
```

Priority: CLI argument > environment variable > default value.

### List Arguments

```python
from typing import List

class MyArgs(KliamkaArgClass):
    files: List[str] = KliamkaArg("--files", "Input files")
    counts: List[int] = KliamkaArg("--counts", "Counts")
```

```bash
python app.py --files a.txt b.txt --counts 1 2 3
```

### Positional Arguments

```python
class MyArgs(KliamkaArgClass):
    source: str = KliamkaArg("source", "Source file", positional=True)
    dest: str = KliamkaArg("dest", "Destination file", positional=True)
```

### Mutually Exclusive Arguments

```python
class MyArgs(KliamkaArgClass):
    json_out: bool | None = KliamkaArg(
        "--json", "JSON output", mutually_exclusive="format"
    )
    csv_out: bool | None = KliamkaArg(
        "--csv", "CSV output", mutually_exclusive="format"
    )
```

`--json` and `--csv` cannot be used together.

### Custom Type Converters

kliamka has built-in support for `bool`, `int`, `float`, `str`, `Enum`, and `List[...]`. For anything else — `pathlib.Path`, `datetime`, `uuid.UUID`, custom classes — you can plug in a converter.

Two ways, first match wins:

**1. Per-argument converter** (explicit, scoped):

```python
from pathlib import Path
from kliamka import KliamkaArg, KliamkaArgClass

class MyArgs(KliamkaArgClass):
    config: Path = KliamkaArg(
        "--config",
        "Path to config file",
        converter=lambda s: Path(s).expanduser().resolve(),
    )
```

**2. Global registry** (reusable across all arguments of a given type):

```python
from datetime import datetime
from kliamka import KliamkaArgClass, KliamkaArg, register_converter

register_converter(datetime, datetime.fromisoformat)

class MyArgs(KliamkaArgClass):
    since: datetime = KliamkaArg("--since", "Start timestamp")
    until: datetime = KliamkaArg("--until", "End timestamp")
```

**Resolution order** (first match wins, used by both CLI and env var parsing):

1. Explicit `KliamkaArg(converter=...)` on the field
2. A type registered via `register_converter(...)`
3. `Enum` subclass — built-in enum parser
4. `List[T]` — recursive lookup on element type `T`
5. Fallback: the annotation itself (e.g. `int`, `float`, `str`)

Converters can raise `ValueError` or `TypeError` on invalid input; kliamka wraps that into a clean CLI error like:

```text
error: argument --port: invalid int value: '99999' (out of range: 99999)
```

Use `unregister_converter(type)` to remove a registered converter. See [`examples/custom_converters.py`](examples/custom_converters.py) for a runnable demo.

### Pydantic Validation

```python
from pydantic import model_validator

class MyArgs(KliamkaArgClass):
    port: int | None = KliamkaArg("--port", "Port number", default=8080)

    @model_validator(mode="after")
    def validate_port(self) -> "MyArgs":
        if self.port is not None and not (1 <= self.port <= 65535):
            raise ValueError(f"Port must be 1-65535, got {self.port}")
        return self
```

When validation fails during `from_args()`, kliamka raises `KliamkaError` with a simplified message. When validation fails inside `@kliamka_cli` or `@kliamka_subcommands`, the library renders that message through `argparse`, so users see standard CLI output such as:

```text
error: Port must be 1-65535, got 99999
```

## Documentation

- `CLAUDE.md` — source of truth for project specifications
- `docs/TODO.md` — development log and task tracker
- `docs/20260408_product_requirements.md` — current product requirements and roadmap baseline

## Development

### Requirements

- Python 3.11+
- Pydantic 2.0+

### Setup

```bash
git clone https://github.com/hotsyk/kliamka.git
cd kliamka
make init-dev
make install
```

### Available Make Commands

| Command        | Description                       |
|----------------|-----------------------------------|
| `make install` | Install package in development mode |
| `make test`    | Run unit tests with pytest (`-m "not packaging"`) |
| `make test-package` | Build wheel/sdist and run packaging smoke tests |
| `make test-all` | Run the full pytest suite, including packaging smoke coverage |
| `make test-docker VERSION=3.11` | Run tests in Docker for a specific Python version |
| `make test-docker-all` | Run Docker test matrix for Python 3.11–3.14 |
| `make lint`    | Run type checking and linting     |
| `make format`  | Format code with ruff             |
| `make clean`   | Clean build artifacts             |

### Packaging and Compatibility Workflow

The repository now uses a modular package layout internally. The public import surface remains `from kliamka import ...`, while the active implementation lives under `src/kliamka/` and the legacy top-level module path is kept as a compatibility facade.

Validation failures are also split more cleanly by context:
- `KliamkaArgClass.from_args()` raises `KliamkaError` with simplified, joined validation messages for programmatic use.
- `@kliamka_cli` and `@kliamka_subcommands` hand those messages back to `argparse`, so CLI users still see standard `error:` output.

GitHub Actions verifies both compatibility and packaging confidence on Python 3.11, 3.12, 3.13, and 3.14. The default local workflow mirrors that split:
- `make test` for unit coverage excluding packaging smoke markers
- `make test-package` for built wheel/sdist installation smoke tests
- `make test-all` for the complete pytest suite

### Docker Test Matrix

To mirror the pytest compatibility check locally across interpreter versions, use `Dockerfile.test`.

Run the full local Docker matrix:

```bash
make test-docker-all
```

This target runs four isolated Docker test jobs sequentially for Python 3.11, 3.12, 3.13, and 3.14.

Run one Dockerized test job for a specific Python version:

```bash
make test-docker VERSION=3.12
```

An optional `docker-compose.test.yml` file is included as a simple service definition reference for the supported Python versions.

These Docker targets bootstrap their own isolated environment inside the container and do not rely on the host `.venv` or on `make test`. Each container installs the package and runs:

```bash
pip install -e .
pip install pytest
pytest tests/ -v --tb=short
```

Success means the selected container exits cleanly and `pytest` passes for that Python version with no test failures. `make test-docker-all` is successful only when all four Python versions pass.

This intentionally keeps the Docker scope minimal and aligned with the CI pytest step, without pulling in linting, typing, or benchmark jobs.

### Versions

See [VERSIONS.md](VERSIONS.md) for detailed version history and changelog.

## Examples

See the [examples/](examples/) directory:

- `examples/basic_usage.py` — Basic CLI argument handling
- `examples/enums.py` — Enum types
- `examples/positional_args.py` — Positional arguments
- `examples/list_args.py` — List arguments
- `examples/env_vars.py` — Environment variable fallback
- `examples/subcommands.py` — Git-style subcommands
- `examples/custom_converters.py` — Custom type converters (per-arg and global registry)

## License

[MIT-NORUS](LICENSE) License — see LICENSE file for details.

## Author

Volodymyr Hotsyk — [https://github.com/hotsyk](https://github.com/hotsyk)
