# Public API

The supported import surface is available from `kliamka`:

```python
from kliamka import (
    KliamkaArg,
    KliamkaArgClass,
    KliamkaError,
    ParserMeta,
    kliamka_cli,
    kliamka_subcommands,
    register_converter,
    unregister_converter,
)
```

Internal modules and names beginning with `_` are implementation details.

## `KliamkaArg`

```text
KliamkaArg(
    flag: str,
    help_text: str = "",
    default: Any = None,
    positional: bool = False,
    env: str | None = None,
    short: str | None = None,
    mutually_exclusive: str | None = None,
    converter: Callable[[str], Any] | None = None,
) -> KliamkaArg
```

Descriptor stored as a Pydantic field default. It records an option or positional's spelling, help, fallback, aliases, exclusion group, and optional converter. See [Arguments and types](20260710_arguments_and_types.md).

## `KliamkaArgClass`

Base class for argument models. It extends Pydantic `BaseModel` and enables arbitrary descriptor types.

### `KliamkaArgClass.create_parser`

```text
@classmethod
def create_parser(cls) -> argparse.ArgumentParser
```

Creates a fresh parser from the class definition and its `ParserMeta`. Raises `KliamkaError` when field metadata cannot be represented, including unsupported wider union annotations.

### `KliamkaArgClass.from_args`

```text
@classmethod
def from_args(cls, args: argparse.Namespace) -> Self
```

Resolves CLI values, environment fallbacks, and defaults; then constructs and validates the model.

Raises `KliamkaError` when environment conversion or Pydantic validation fails. It should be called on namespaces returned by `create_parser()`.

## `ParserMeta`

```text
ParserMeta(
    prog: str | None = None,
    usage: str | None = None,
    epilog: str | None = None,
    version: str | None = None,
) -> ParserMeta
```

Container assigned as a model's `parser_meta` class attribute. `version` adds `--version`; the other fields map to parser presentation. See [Parser customization](20260710_parser_customization.md).

## `KliamkaError`

```python
class KliamkaError(Exception): ...
```

Base exception for Kliamka-specific schema, conversion, and validation failures. Decorators convert it into CLI parser errors; direct `from_args()` callers should catch it when they want to handle invalid input programmatically.

## `kliamka_cli`

```text
def kliamka_cli(
    arg_class: type[KliamkaArgClass],
    argv: Sequence[str] | None = None,
) -> Callable[[F], F]
```

Decorator factory for a single-command CLI. On each call it creates a parser, parses `argv` or the process command line, validates an `arg_class` instance, and injects that model before the wrapper's original arguments.

## `kliamka_subcommands`

```text
def kliamka_subcommands(
    main_class: type[KliamkaArgClass],
    subcommands: dict[str, type[KliamkaArgClass]],
    argv: Sequence[str] | None = None,
) -> Callable[[F], F]
```

Decorator factory for a required subcommand interface. It injects the main model, selected command name, and selected command model.

Raises `KliamkaError` at decoration time if main and command destinations conflict or use the reserved `_command` destination. See [Subcommands](20260710_subcommands.md).

## `register_converter`

```text
def register_converter(
    tp: type,
    fn: Callable[[str], Any],
) -> None
```

Registers or replaces the global converter for `tp` and invalidates cached parser plans. The callable should return a converted value or raise `ValueError`/`TypeError` for invalid input.

## `unregister_converter`

```text
def unregister_converter(tp: type) -> None
```

Removes a global converter and invalidates cached parser plans. It is a no-op when the type is not registered.

## Package metadata

The package also exports:

- `__version__` — installed Kliamka version;
- `__author__` — package author name;
- `__email__` — package author contact.

These values are informational. Use `importlib.metadata.version("kliamka")` when distribution metadata is the required authority.
