# Arguments and types

`KliamkaArg` connects a Pydantic field to an `argparse` argument. The field annotation controls conversion; the descriptor controls CLI presentation and fallback behavior.

## Descriptor parameters

```python
KliamkaArg(
    flag,
    help_text="",
    default=None,
    positional=False,
    env=None,
    short=None,
    mutually_exclusive=None,
    converter=None,
)
```

| Parameter | Meaning |
| --- | --- |
| `flag` | Long option such as `--output`, or a positional display name such as `source` |
| `help_text` | Text shown in generated help |
| `default` | Value used when neither CLI nor environment supplies the field |
| `positional` | Treat the field as positional; a flag without a leading `-` is also positional |
| `env` | Environment variable fallback name |
| `short` | Short alias such as `-o` |
| `mutually_exclusive` | Name shared by options that cannot appear together |
| `converter` | Callable from one raw string to the target value |

## Supported annotations

Kliamka directly supports:

- `str`, `int`, `float`, and `bool`;
- `Enum` subclasses with string or integer values;
- `list[T]` and `typing.List[T]`;
- `Optional[T]` and `T | None` for one supported `T`;
- custom types accepted by `argparse` or handled by a converter.

Wider unions such as `int | str`, `Union[int, str]`, and `int | str | None` are not supported. Parser creation raises `KliamkaError` rather than guessing which branch should parse a token.

## Options and short aliases

```python
class Args(KliamkaArgClass):
    output: str | None = KliamkaArg(
        "--output",
        "Output file",
        short="-o",
    )
```

Both commands populate `output`:

```bash
app --output result.txt
app -o result.txt
```

The model field name is the canonical destination. This avoids accidental collisions between spellings that normalize similarly.

## Boolean flags

Boolean arguments are presence flags:

```python
class Args(KliamkaArgClass):
    verbose: bool = KliamkaArg("--verbose", "Enable verbose output", short="-v")
```

`--verbose` stores `True`; do not pass a following value such as `--verbose true`. If no CLI value, environment value, or explicit default is available, boolean fields fall back to `False`.

Kliamka does not currently generate a `--no-verbose` counterpart.

## Positional arguments

Set `positional=True`, or use a name without a leading hyphen:

```python
class Args(KliamkaArgClass):
    source: str = KliamkaArg("source-file", "Input file", positional=True)
    destination: str | None = KliamkaArg(
        "destination",
        "Optional output file",
        positional=True,
        default="stdout",
    )
```

The Pydantic field remains `source`, even when the displayed positional name is `source-file`. Optional annotations and explicit defaults make a positional accept zero or one value.

## Lists

A list option consumes zero or more following tokens:

```python
class Args(KliamkaArgClass):
    include: list[str] = KliamkaArg("--include", "Paths to include")
    retries: list[int] = KliamkaArg("--retries", "Retry counts")
```

```bash
app --include src tests --retries 1 2 3
```

An absent list without an explicit default falls back to a new empty list. Because list options use `nargs="*"`, another option marks the end of their values.

## Enums

Enum members can be selected case-insensitively by member name or serialized value:

```python
from enum import Enum


class Level(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = 3


class Args(KliamkaArgClass):
    level: Level = KliamkaArg("--level", "Logging level", default=Level.INFO)
```

Examples include `--level info`, `--level INFO`, `--level warning`, `--level ERROR`, and `--level 3`. Invalid values produce a list of valid choices.

## Defaults and precedence

For each CLI-backed field, `from_args()` resolves:

1. an explicitly supplied CLI value, even if it equals the default;
2. the configured environment variable, including an empty string;
3. `KliamkaArg.default` when it is not `None`;
4. `False` for booleans, `[]` for lists, or `None` otherwise.

This distinction is why application code should consume the Pydantic model, not the intermediate `argparse.Namespace`.

## Mutually exclusive options

Give incompatible options the same group name:

```python
class Args(KliamkaArgClass):
    json_output: bool = KliamkaArg(
        "--json", "Write JSON", mutually_exclusive="format"
    )
    csv_output: bool = KliamkaArg(
        "--csv", "Write CSV", mutually_exclusive="format"
    )
```

`app --json --csv` fails during parsing. Mutual exclusion prevents simultaneous use; it does not make one member required.

## Ordinary Pydantic fields

A model may contain fields whose default is not `KliamkaArg`. `from_args()` copies matching namespace values when available and otherwise uses the Pydantic field default. Keep CLI-facing fields explicit so help output and conversion remain predictable.
