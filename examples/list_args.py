"""Example demonstrating list/array arguments in kliamka."""

import sys
from enum import Enum
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kliamka import KliamkaArg, KliamkaArgClass, kliamka_cli


class FileType(Enum):
    """Supported file types."""

    TXT = "txt"
    CSV = "csv"
    JSON = "json"
    XML = "xml"


class BatchProcessArgs(KliamkaArgClass):
    """Batch process multiple files with various options."""

    files: List[str] = KliamkaArg("--files", "Input files to process")
    exclude: List[str] = KliamkaArg("--exclude", "Patterns to exclude", default=[])
    ports: List[int] = KliamkaArg("--ports", "Port numbers to use", default=[8080])
    types: List[FileType] = KliamkaArg("--types", "File types to include")
    verbose: Optional[bool] = KliamkaArg("--verbose", "Enable verbose output")


@kliamka_cli(BatchProcessArgs)
def main(args: BatchProcessArgs) -> None:
    """Demonstrate list argument usage."""
    print("Kliamka List Arguments Example")
    print(f"Files to process: {args.files}")
    print(f"Exclusion patterns: {args.exclude}")
    print(f"Ports: {args.ports}")
    print(f"File types: {[t.value for t in args.types] if args.types else []}")

    if args.verbose:
        print("\nVerbose mode enabled:")
        print(f"  Number of files: {len(args.files)}")
        print(f"  Number of exclusions: {len(args.exclude)}")
        print(f"  Number of ports: {len(args.ports)}")
        for i, f in enumerate(args.files, 1):
            print(f"  File {i}: {f}")


if __name__ == "__main__":
    main()
