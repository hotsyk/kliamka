"""Example demonstrating subcommands in kliamka (git-style CLI)."""

import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kliamka import KliamkaArg, KliamkaArgClass, kliamka_subcommands


class GlobalArgs(KliamkaArgClass):
    """Task manager CLI - manage your tasks from the command line."""

    verbose: Optional[bool] = KliamkaArg("--verbose", "Enable verbose output")
    config: Optional[str] = KliamkaArg("--config", "Path to config file", default="~/.tasks.json")


class AddArgs(KliamkaArgClass):
    """Add a new task to your list."""

    name: str = KliamkaArg("name", "Task name", positional=True)
    priority: Optional[int] = KliamkaArg("--priority", "Task priority (1-5)", default=3)
    tags: List[str] = KliamkaArg("--tags", "Tags for the task", default=[])


class RemoveArgs(KliamkaArgClass):
    """Remove a task from your list."""

    task_id: int = KliamkaArg("task_id", "Task ID to remove", positional=True)
    force: Optional[bool] = KliamkaArg("--force", "Skip confirmation")


class ListArgs(KliamkaArgClass):
    """List all tasks."""

    status: Optional[str] = KliamkaArg("--status", "Filter by status", default="all")
    limit: Optional[int] = KliamkaArg("--limit", "Maximum tasks to show", default=10)


@kliamka_subcommands(GlobalArgs, {"add": AddArgs, "remove": RemoveArgs, "list": ListArgs})
def main(global_args: GlobalArgs, command: str, cmd_args) -> None:
    """Task manager demonstrating subcommands usage.

    Usage examples:
        python subcommands.py add "Buy groceries" --priority 2 --tags shopping urgent
        python subcommands.py remove 123 --force
        python subcommands.py list --status pending --limit 5
        python subcommands.py --verbose add "Important task"
    """
    if global_args.verbose:
        print(f"Config file: {global_args.config}")
        print(f"Command: {command}")
        print()

    if command == "add":
        print(f"Adding task: {cmd_args.name}")
        print(f"  Priority: {cmd_args.priority}")
        print(f"  Tags: {cmd_args.tags if cmd_args.tags else 'None'}")

    elif command == "remove":
        if cmd_args.force:
            print(f"Force removing task #{cmd_args.task_id}")
        else:
            print(f"Removing task #{cmd_args.task_id} (would prompt for confirmation)")

    elif command == "list":
        print(f"Listing tasks (status={cmd_args.status}, limit={cmd_args.limit})")
        # Simulate task listing
        print("\nTasks:")
        print("  #1: Buy groceries [pending]")
        print("  #2: Call mom [completed]")
        print("  #3: Finish report [in-progress]")


if __name__ == "__main__":
    main()
