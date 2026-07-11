# Get started

This guide builds a complete CLI, explains the execution flow, and shows how to test it without modifying `sys.argv`.

## Install

Create or activate a Python 3.11+ environment, then install Kliamka:

```bash
python -m pip install kliamka
```

For repository development, see [Development and deployment](20260710_development.md).

## Define an argument model

A CLI starts with a subclass of `KliamkaArgClass`. Each CLI-backed Pydantic field uses a `KliamkaArg` value.

```python
from pathlib import Path

from kliamka import KliamkaArg, KliamkaArgClass, ParserMeta, kliamka_cli


class AppArgs(KliamkaArgClass):
    """Render a text file."""

    parser_meta = ParserMeta(
        prog="render-text",
        epilog="Example: render-text README.md --format html",
        version="render-text 1.0.0",
    )

    input_file: Path = KliamkaArg(
        "input-file",
        "Input document",
        positional=True,
        converter=Path,
    )
    output_format: str = KliamkaArg(
        "--format",
        "Output format",
        default="text",
        short="-f",
        env="RENDER_FORMAT",
    )
    verbose: bool = KliamkaArg(
        "--verbose",
        "Print processing details",
        short="-v",
    )
```

The class docstring becomes the parser description. `ParserMeta` controls the program name, usage, epilog, and optional `--version` action.

## Connect the model to a function

Use `@kliamka_cli` to parse arguments immediately before calling your function:

```python
@kliamka_cli(AppArgs)
def main(args: AppArgs) -> None:
    if args.verbose:
        print(f"Rendering {args.input_file} as {args.output_format}")


if __name__ == "__main__":
    main()
```

The decorated function receives a validated `AppArgs` instance as its first argument.

## Run the CLI

```bash
python app.py --help
python app.py README.md --format html --verbose
RENDER_FORMAT=markdown python app.py README.md
python app.py --version
```

For fields with an environment fallback, values resolve in this order:

1. command-line value;
2. environment variable;
3. declared default or Kliamka fallback.

## What happens during a call?

1. `AppArgs.create_parser()` creates an `argparse.ArgumentParser`.
2. `parse_args()` converts raw command-line tokens into a namespace.
3. `AppArgs.from_args()` resolves environment variables and defaults.
4. Pydantic constructs and validates `AppArgs`.
5. Your decorated function receives the model.

Parsing failures and validation failures from a decorator are rendered with standard `argparse` usage and `error:` output.

## Test with explicit arguments

Pass `argv` to the decorator to avoid patching process arguments:

```python
@kliamka_cli(AppArgs, argv=["README.md", "--format", "html", "-v"])
def test_entrypoint(args: AppArgs) -> None:
    assert args.input_file == Path("README.md")
    assert args.output_format == "html"
    assert args.verbose is True


test_entrypoint()
```

For lower-level tests, build the parser directly:

```python
parser = AppArgs.create_parser()
namespace = parser.parse_args(["README.md", "--format", "html"])
args = AppArgs.from_args(namespace)

assert args.output_format == "html"
```

!!! warning "Always call `from_args()`"
    A namespace returned by a Kliamka-created parser is an intermediate object. Absent CLI values use an internal sentinel so Kliamka can distinguish “not supplied” from explicit values. Convert the namespace through `from_args()` before application use.

## Next steps

- Learn field behavior in [Arguments and types](20260710_arguments_and_types.md).
- Add configuration with [Environment variables](20260710_environment_variables.md).
- Create command groups with [Subcommands](20260710_subcommands.md).
- Enforce domain rules with [Converters and validation](20260710_converters_and_validation.md).
