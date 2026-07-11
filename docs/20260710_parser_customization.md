# Parser customization

Kliamka exposes parser metadata, direct parser construction, and explicit argument sequences for applications that need more than a minimal decorator call.

## `ParserMeta`

Assign `parser_meta` on an argument model:

```python
from kliamka import KliamkaArg, KliamkaArgClass, ParserMeta


class Args(KliamkaArgClass):
    """Synchronize a local directory."""

    parser_meta = ParserMeta(
        prog="sync-files",
        usage="sync-files SOURCE DESTINATION [options]",
        epilog="Exit status is non-zero when synchronization fails.",
        version="sync-files 2.1.0",
    )

    source: str = KliamkaArg("source", "Source directory", positional=True)
    destination: str = KliamkaArg(
        "destination", "Destination directory", positional=True
    )
```

| Attribute | Effect |
| --- | --- |
| `prog` | Program name in usage and help; defaults to the executable name |
| `usage` | Replaces generated usage text |
| `epilog` | Adds text after arguments in help |
| `version` | Adds `--version` using the supplied output string |

The model class docstring becomes the parser description. If metadata is inherited, Kliamka searches the class hierarchy for the nearest `ParserMeta` instance.

## Build a parser directly

`create_parser()` returns an `argparse.ArgumentParser`:

```python
parser = Args.create_parser()
print(parser.format_help())

namespace = parser.parse_args(["source", "backup"])
args = Args.from_args(namespace)
```

Direct access is useful for tests, embedding, help generation, or integrating parsing into an existing process. Treat the returned parser as application-owned, but avoid depending on Kliamka's internal parser subclass or private attributes.

## Programmatic `argv`

Both decorators accept an optional sequence:

```python
from kliamka import kliamka_cli


@kliamka_cli(Args, argv=["source", "backup"])
def invoke(args: Args) -> None:
    assert args.source == "source"
```

When `argv` is `None`, `argparse` reads the process command line. Passing an empty list means “parse no arguments”; it does not fall back to `sys.argv`.

The subcommand decorator has the same option:

```python
@kliamka_subcommands(MainArgs, {"add": AddArgs}, argv=["add", "item"])
def invoke(main_args: MainArgs, command: str, command_args: AddArgs) -> None:
    ...
```

## Call decorated functions

Kliamka preserves the wrapped function's metadata with `functools.wraps`. Extra arguments supplied when calling the wrapper are forwarded after the injected CLI models:

```python
@kliamka_cli(Args, argv=["source", "backup"])
def run(args: Args, dry_run_reason: str) -> None:
    print(dry_run_reason, args.source)


run("integration test")
```

For most applications, keep the decorated function as a thin entry point and call ordinary application services from it.

## Help and errors

- `-h` and `--help` are generated automatically.
- The class docstring is the description.
- Argument help includes an environment hint when `env` is configured.
- `ParserMeta.version` controls whether `--version` exists.
- Parser errors follow standard `argparse` output and termination behavior.
- Main-model validation errors use the main parser; command-model errors use the selected command parser.

## Caching behavior

Kliamka caches immutable parser construction plans for speed while returning a fresh parser and fresh model for each call. Mutating a `KliamkaArg` or changing the converter registry invalidates relevant plans.

Do not mutate argument descriptors during normal request handling. Define models and converters at import or startup time, then treat the CLI schema as immutable.

## Design boundaries

Kliamka intentionally does not expose every `argparse.add_argument()` option. If an application requires unsupported behavior, consider:

1. expressing the rule with a converter or Pydantic validator;
2. using `create_parser()` as part of a controlled integration;
3. contributing a focused public feature;
4. using `argparse` directly when full parser-level control is the primary requirement.
