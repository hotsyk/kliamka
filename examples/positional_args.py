"""Example demonstrating positional arguments in kliamka."""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kliamka import KliamkaArg, KliamkaArgClass, kliamka_cli


class FileCopyArgs(KliamkaArgClass):
    """Copy a file from source to destination."""

    source: str = KliamkaArg("source", "Source file path", positional=True)
    destination: str = KliamkaArg("destination", "Destination file path", positional=True)
    verbose: Optional[bool] = KliamkaArg("--verbose", "Enable verbose output")
    force: Optional[bool] = KliamkaArg("--force", "Overwrite existing files")


@kliamka_cli(FileCopyArgs)
def main(args: FileCopyArgs) -> None:
    """Demonstrate positional arguments usage."""
    print("Kliamka Positional Arguments Example")
    print(f"Source: {args.source}")
    print(f"Destination: {args.destination}")

    if args.verbose:
        print("\nVerbose mode enabled:")
        print(f"  Would copy '{args.source}' to '{args.destination}'")
        if args.force:
            print("  Force mode: would overwrite existing files")


if __name__ == "__main__":
    main()
