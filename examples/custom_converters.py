"""Custom type converter examples for kliamka.

Demonstrates both ways to wire custom converters:

1. Per-argument ``converter=`` on ``KliamkaArg`` — explicit, scoped to one
   field. Best when the parsing logic is specific to that flag.
2. Global ``register_converter(type, fn)`` — applies to every argument
   annotated with that type across the CLI. Best for common project-wide
   types like ``datetime`` or ``UUID``.

Run directly to see the behavior:

    python examples/custom_converters.py \\
        --config ./my.cfg \\
        --since 2024-01-15T12:30:00
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from kliamka import (
    KliamkaArg,
    KliamkaArgClass,
    kliamka_cli,
    register_converter,
)


# Global registration: every ``datetime`` field now parses ISO-8601 input.
register_converter(datetime, datetime.fromisoformat)


class Args(KliamkaArgClass):
    """Custom converter demo."""

    # Per-argument converter: resolves, expands and validates the path.
    config: Path = KliamkaArg(
        "--config",
        "Path to configuration file",
        converter=lambda s: Path(s).expanduser().resolve(),
    )

    # Uses the globally registered datetime converter.
    since: datetime = KliamkaArg("--since", "Start timestamp (ISO-8601)")


@kliamka_cli(Args)
def main(args: Args) -> None:
    print(f"config : {args.config} (type={type(args.config).__name__})")
    print(f"since  : {args.since} (type={type(args.since).__name__})")


if __name__ == "__main__":
    main()
