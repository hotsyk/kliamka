#!/bin/bash
set -euo pipefail

pytest tests/ -q -m "not packaging"
python -m mypy src/
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/

python - <<'PY'
import contextlib
import io
import sys

from kliamka import KliamkaArg, KliamkaArgClass


class CachedArgs(KliamkaArgClass):
    name: str = KliamkaArg("--name", help_text="before")


first = CachedArgs.create_parser()
second = CachedArgs.create_parser()
first.add_argument("--extra")
assert first.parse_args(["--name", "one", "--extra", "value"]).extra == "value"
assert second.parse_known_args(["--name", "two", "--extra", "value"])[1] == [
    "--extra",
    "value",
]
assert first.format_help().count("-h, --help") == 1
assert first.format_help() == first.format_help()
second.format_help()
assert first._actions[1] is not second._actions[1]

argument = CachedArgs.model_fields["name"].default
assert isinstance(argument, KliamkaArg)
argument.help_text = "after"
assert "after" in CachedArgs.create_parser().format_help()

old_argv = sys.argv
try:
    sys.argv = ["/tmp/one"]
    assert CachedArgs.create_parser().prog == "one"
    sys.argv = ["/tmp/two"]
    assert CachedArgs.create_parser().prog == "two"
finally:
    sys.argv = old_argv

with contextlib.redirect_stdout(io.StringIO()) as output:
    try:
        CachedArgs.create_parser().parse_args(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("--help did not exit")
assert "-h, --help" in output.getvalue()
PY
