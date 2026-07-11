# Environment variables

A `KliamkaArg` can name an environment variable used when the command line does not supply that field.

```python
from kliamka import KliamkaArg, KliamkaArgClass


class Args(KliamkaArgClass):
    endpoint: str = KliamkaArg(
        "--endpoint",
        "Service endpoint",
        default="https://api.example.com",
        env="APP_ENDPOINT",
    )
    timeout: int = KliamkaArg(
        "--timeout",
        "Request timeout in seconds",
        default=30,
        env="APP_TIMEOUT",
    )
```

Generated help includes an `[env: NAME]` hint.

## Resolution order

Kliamka resolves every field independently:

1. **CLI** — an explicitly supplied option or positional always wins;
2. **environment** — used only when the CLI omitted the field;
3. **default** — the descriptor default, then the type-specific fallback.

```bash
APP_TIMEOUT=60 app                  # timeout is 60
APP_TIMEOUT=60 app --timeout 5      # timeout is 5
app                                 # timeout is 30
```

A CLI value still wins when it happens to equal the declared default.

## Empty values

An environment variable counts as present even when its value is empty. For a string, `APP_ENDPOINT=` therefore produces `""` rather than falling back to the descriptor default. Use Pydantic validation if an empty value is invalid for your application.

## Boolean values

Environment booleans are stripped, case-insensitive, and intentionally strict.

| True | False |
| --- | --- |
| `true` | `false` |
| `1` | `0` |
| `yes` | `no` |
| `on` | `off` |

Other spellings fail with a `KliamkaError` that names the environment variable. CLI booleans remain presence flags and do not accept these string values.

## List values

Environment lists use comma-separated items:

```python
class Args(KliamkaArgClass):
    ports: list[int] = KliamkaArg(
        "--ports", "Ports to bind", env="APP_PORTS"
    )
```

```bash
APP_PORTS=8000,8001,9000 app
```

Whitespace around each item is removed. An empty environment value produces an empty list. Comma escaping and CSV quoting are not supported.

## Enums and custom types

Environment values use the same enum and converter resolution as command-line tokens:

```python
from pathlib import Path


class Args(KliamkaArgClass):
    config: Path = KliamkaArg(
        "--config",
        "Configuration file",
        env="APP_CONFIG",
        converter=Path,
    )
```

For list fields, conversion is applied to each comma-separated item. See [Converters and validation](20260710_converters_and_validation.md) for precedence details.

## Errors

Conversion errors are raised from `from_args()` as `KliamkaError` and identify the source variable:

```text
environment variable APP_TIMEOUT: invalid literal for int() with base 10: 'soon'
```

When parsing through `@kliamka_cli` or `@kliamka_subcommands`, that message is rendered as a standard CLI error without an application traceback.

## Operational guidance

- Treat environment names as part of your CLI's public configuration contract.
- Use application-specific prefixes to avoid collisions.
- Do not place secret values in help text, logs, defaults, or error messages.
- Validate URLs, ranges, paths, and required non-empty strings with Pydantic.
- In tests, isolate environment changes with fixtures such as pytest's `monkeypatch`.
