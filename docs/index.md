# Kliamka

**Kliamka** is a small Python library for building type-safe command-line interfaces from Pydantic models. It combines declarative argument definitions and Pydantic validation with Python's standard `argparse` user experience.

```python
from kliamka import KliamkaArg, KliamkaArgClass, kliamka_cli


class Args(KliamkaArgClass):
    """Copy files safely."""

    source: str = KliamkaArg("source", "File to copy", positional=True)
    destination: str = KliamkaArg("destination", "Copy destination", positional=True)
    verbose: bool = KliamkaArg("--verbose", "Show progress", short="-v")


@kliamka_cli(Args)
def main(args: Args) -> None:
    if args.verbose:
        print(f"Copying {args.source} to {args.destination}")


if __name__ == "__main__":
    main()
```

```console
$ python copy.py --help
$ python copy.py -v input.txt backup/input.txt
```

## Why Kliamka?

- **One typed model** defines parsing, defaults, and validated application input.
- **Familiar CLI behavior** comes from `argparse`, including generated help and standard errors.
- **Pydantic validation** supports field constraints, field validators, and cross-field rules.
- **Practical CLI features** include positionals, short options, lists, enums, environment fallbacks, mutually exclusive groups, versions, and subcommands.
- **Extensible conversion** handles project-specific types through per-field or global converters.
- **Library-friendly testing** is supported through custom `argv` sequences and direct parser access.

## Requirements

- Python 3.11 or newer
- Pydantic 2.x

Install the latest release from PyPI:

```bash
python -m pip install kliamka
```

## Documentation map

| If you want to… | Read… |
| --- | --- |
| Build and run your first CLI | [Get started](20260710_getting_started.md) |
| Understand supported annotations and defaults | [Arguments and types](20260710_arguments_and_types.md) |
| Read configuration from the environment | [Environment variables](20260710_environment_variables.md) |
| Build a Git-style command tree | [Subcommands](20260710_subcommands.md) |
| Parse custom types or enforce domain rules | [Converters and validation](20260710_converters_and_validation.md) |
| Customize help, version output, or parsing | [Parser customization](20260710_parser_customization.md) |
| Look up a public symbol | [Public API](20260710_api_reference.md) |
| Develop Kliamka or build these docs | [Development and deployment](20260710_development.md) |

!!! note "Current scope"
    Kliamka intentionally supports a focused annotation set. Optional single types are supported, but wider unions such as `int | str` are rejected with `KliamkaError` when a parser is built.
