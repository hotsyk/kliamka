"""Example demonstrating custom enum types as CLI arguments."""

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


from kliamka import KliamkaArg, KliamkaArgClass, kliamka_cli


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class OutputFormat(Enum):
    """Output format enumeration."""
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    CSV = "csv"
    TEXT = "text"


class Priority(Enum):
    """Task priority enumeration."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class KliamkaEnumExample(KliamkaArgClass):
    """Example CLI arguments with enum types."""
    log_level: LogLevel = KliamkaArg(
        "--log-level",
        default=LogLevel.INFO,
        help_text="Set the logging level"
    )
    output_format: OutputFormat = KliamkaArg(
        "--format",
        default=OutputFormat.TEXT,
        help_text="Output format for results"
    )
    priority: Optional[Priority] = KliamkaArg(
        "--priority",
        default=None,
        help_text="Task priority level"
    )
    verbose: bool = KliamkaArg(
        "--verbose",
        default=False,
        help_text="Enable verbose output"
    )


@kliamka_cli(KliamkaEnumExample)
def main(args) -> None:
    """Demonstrate enum usage in CLI arguments."""
    print("Kliamka Enum Example")
    print(f"Log Level: {args.log_level.value}")
    print(f"Output Format: {args.output_format.value}")

    if args.priority:
        print(f"Priority: {args.priority.name} (value: {args.priority.value})")
    else:
        print("Priority: Not specified")

    if args.verbose:
        print("\nVerbose mode enabled - showing enum details:")
        print(f"  Log Level enum: {args.log_level}")
        print(f"  Available log levels: {[level.value for level in LogLevel]}")
        print(f"  Output Format enum: {args.output_format}")
        print(f"  Available formats: {[fmt.value for fmt in OutputFormat]}")
        if args.priority:
            print(f"  Priority enum: {args.priority}")
            print(f"  Available priorities: {[p.name + '=' + str(p.value) for p in Priority]}")


if __name__ == "__main__":
    main()
