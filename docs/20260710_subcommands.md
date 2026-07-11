# Subcommands

`@kliamka_subcommands` builds Git-style command interfaces with one main argument model and one model per command.

## Complete example

```python
from typing import Any

from kliamka import KliamkaArg, KliamkaArgClass, ParserMeta, kliamka_subcommands


class MainArgs(KliamkaArgClass):
    """Manage project tasks."""

    parser_meta = ParserMeta(prog="tasks", version="tasks 1.0.0")
    verbose: bool = KliamkaArg("--verbose", "Show details", short="-v")


class AddArgs(KliamkaArgClass):
    """Add a task."""

    title: str = KliamkaArg("title", "Task title", positional=True)
    labels: list[str] = KliamkaArg("--labels", "Labels to attach")


class CompleteArgs(KliamkaArgClass):
    """Complete a task."""

    task_id: int = KliamkaArg("task-id", "Task identifier", positional=True)
    force: bool = KliamkaArg("--force", "Skip confirmation", short="-f")


@kliamka_subcommands(
    MainArgs,
    {"add": AddArgs, "complete": CompleteArgs},
)
def main(main_args: MainArgs, command: str, command_args: Any) -> None:
    if main_args.verbose:
        print(f"Running {command}")

    if command == "add":
        assert isinstance(command_args, AddArgs)
        print(f"Adding {command_args.title}")
    elif command == "complete":
        assert isinstance(command_args, CompleteArgs)
        print(f"Completing {command_args.task_id}")


if __name__ == "__main__":
    main()
```

```bash
tasks --verbose add "Write docs" --labels docs urgent
tasks complete 42 --force
```

The decorated function receives:

1. the validated main model;
2. the selected command name;
3. the validated model associated with that command;
4. any additional positional or keyword arguments passed to the wrapper.

## Required command selection

The generated subparser is required. Calling the program without a command fails through `argparse`; there is no `None` command case inside the decorated function.

## Main and command options

Main options are defined before the command token, while command-specific options follow their command in conventional `argparse` style:

```bash
tasks --verbose add "Write docs" --labels docs
```

Fields resolve CLI, environment, and default values separately for the main and selected command models.

## Per-command parser metadata

Every model may define `ParserMeta`:

```python
class AddArgs(KliamkaArgClass):
    """Add a task."""

    parser_meta = ParserMeta(
        prog="tasks add",
        usage="tasks add TITLE [--labels LABEL ...]",
        epilog="Titles should be concise.",
        version="tasks-add 1.0.0",
    )
```

For a command model, `prog`, `usage`, `epilog`, and `version` apply to that subparser. Validation errors for command fields use the command parser's presentation.

## Destination collision rules

A subparser writes values into the same `argparse.Namespace` as main options. To prevent silent overwrites, Kliamka validates destinations when the decorator is created.

- A CLI-backed command field cannot share its destination with a main field.
- A main CLI-backed field cannot share its destination with an ordinary command model field.
- `_command` is reserved for Kliamka's selected-command destination.
- Different subcommands may reuse a field or flag because only one command parses at a time.

Conflicts raise `KliamkaError` early, before the application handles input.

## Testing subcommands

Supply an explicit argument sequence:

```python
seen: tuple[MainArgs, str, AddArgs] | None = None


@kliamka_subcommands(
    MainArgs,
    {"add": AddArgs},
    argv=["--verbose", "add", "Write tests", "--labels", "quality"],
)
def invoke(main_args: MainArgs, command: str, command_args: AddArgs) -> None:
    global seen
    seen = (main_args, command, command_args)


invoke()
assert seen is not None
assert seen[0].verbose is True
assert seen[1] == "add"
assert seen[2].labels == ["quality"]
```

For static typing, narrow the command model using the command string, `isinstance`, overloads in your own dispatch layer, or a small handler mapping.
