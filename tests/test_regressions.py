"""Regression tests for the bugs confirmed in the 2026-07 code review (PLAN.md #1)."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

import pytest

from kliamka import (
    KliamkaArg,
    KliamkaArgClass,
    KliamkaError,
    kliamka_cli,
    kliamka_subcommands,
    register_converter,
)


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    ERROR = "error"


# ── 1.1: PEP 604 unions (`bool | None`) must work like Optional[bool] ──


class TestPep604Unions:
    def test_readme_quick_start_shape(self) -> None:
        class Args(KliamkaArgClass):
            verbose: bool | None = KliamkaArg("--verbose", "Verbose", short="-v")
            count: int | None = KliamkaArg("--count", "Count", default=1, short="-c")

        parser = Args.create_parser()

        instance = Args.from_args(parser.parse_args(["-v", "-c", "3"]))
        assert instance.verbose is True
        assert instance.count == 3

        instance = Args.from_args(parser.parse_args([]))
        assert instance.verbose is False
        assert instance.count == 1

    def test_pep604_str_and_enum(self) -> None:
        class Args(KliamkaArgClass):
            name: str | None = KliamkaArg("--name", "Name", default="anon")
            level: LogLevel | None = KliamkaArg("--level", "Level")

        parser = Args.create_parser()

        instance = Args.from_args(parser.parse_args(["--level", "debug"]))
        assert instance.name == "anon"
        assert instance.level == LogLevel.DEBUG

        instance = Args.from_args(parser.parse_args([]))
        assert instance.level is None

    def test_pep604_list(self) -> None:
        class Args(KliamkaArgClass):
            counts: list[int] | None = KliamkaArg("--counts", "Counts")

        parser = Args.create_parser()

        instance = Args.from_args(parser.parse_args(["--counts", "1", "2"]))
        assert instance.counts == [1, 2]

        instance = Args.from_args(parser.parse_args([]))
        assert instance.counts == []

    def test_pep604_env_fallback(self, monkeypatch) -> None:
        monkeypatch.setenv("PEP604_COUNT", "42")
        monkeypatch.setenv("PEP604_DEBUG", "yes")

        class Args(KliamkaArgClass):
            count: int | None = KliamkaArg("--count", "Count", env="PEP604_COUNT")
            debug: bool | None = KliamkaArg("--debug", "Debug", env="PEP604_DEBUG")

        instance = Args.from_args(Args.create_parser().parse_args([]))
        assert instance.count == 42
        assert instance.debug is True


# ── 1.2: hyphenated positional names must round-trip ────────────────


class TestHyphenatedPositional:
    def test_hyphenated_positional_round_trip(self) -> None:
        class Args(KliamkaArgClass):
            input_file: str = KliamkaArg("input-file", "Input file", positional=True)

        parser = Args.create_parser()
        instance = Args.from_args(parser.parse_args(["hello.txt"]))
        assert instance.input_file == "hello.txt"

    def test_hyphenated_positional_keeps_display_name(self) -> None:
        class Args(KliamkaArgClass):
            input_file: str = KliamkaArg("input-file", "Input file", positional=True)

        help_text = Args.create_parser().format_help()
        assert "input-file" in help_text

    def test_hyphenated_positional_with_default(self) -> None:
        class Args(KliamkaArgClass):
            out_dir: Optional[str] = KliamkaArg(
                "out-dir", "Output dir", default="build", positional=True
            )

        parser = Args.create_parser()
        assert Args.from_args(parser.parse_args([])).out_dir == "build"
        assert Args.from_args(parser.parse_args(["dist"])).out_dir == "dist"


# ── 1.3: explicit CLI value equal to the default must beat env var ──


class TestCliEnvPrecedence:
    def test_cli_value_equal_to_default_beats_env(self, monkeypatch) -> None:
        monkeypatch.setenv("PREC_COUNT", "99")

        class Args(KliamkaArgClass):
            count: Optional[int] = KliamkaArg(
                "--count", "Count", default=1, env="PREC_COUNT"
            )

        parser = Args.create_parser()
        instance = Args.from_args(parser.parse_args(["--count", "1"]))
        assert instance.count == 1

    def test_env_still_beats_default(self, monkeypatch) -> None:
        monkeypatch.setenv("PREC_COUNT", "99")

        class Args(KliamkaArgClass):
            count: Optional[int] = KliamkaArg(
                "--count", "Count", default=1, env="PREC_COUNT"
            )

        parser = Args.create_parser()
        assert Args.from_args(parser.parse_args([])).count == 99

    def test_cli_string_equal_to_default_beats_env(self, monkeypatch) -> None:
        monkeypatch.setenv("PREC_NAME", "from-env")

        class Args(KliamkaArgClass):
            name: Optional[str] = KliamkaArg(
                "--name", "Name", default="anon", env="PREC_NAME"
            )

        parser = Args.create_parser()
        instance = Args.from_args(parser.parse_args(["--name", "anon"]))
        assert instance.name == "anon"

    def test_explicit_empty_list_beats_env(self, monkeypatch) -> None:
        monkeypatch.setenv("PREC_FILES", "a.txt,b.txt")

        class Args(KliamkaArgClass):
            files: List[str] = KliamkaArg("--files", "Files", env="PREC_FILES")

        parser = Args.create_parser()
        assert Args.from_args(parser.parse_args(["--files"])).files == []
        assert Args.from_args(parser.parse_args([])).files == ["a.txt", "b.txt"]


# ── 1.4: bool with default=True must be env-overridable ─────────────


class TestBoolDefaultTrue:
    def test_env_false_overrides_default_true(self, monkeypatch) -> None:
        monkeypatch.setenv("BDT_DEBUG", "false")

        class Args(KliamkaArgClass):
            debug: Optional[bool] = KliamkaArg(
                "--debug", "Debug", default=True, env="BDT_DEBUG"
            )

        instance = Args.from_args(Args.create_parser().parse_args([]))
        assert instance.debug is False

    def test_default_true_kept_without_env(self) -> None:
        class Args(KliamkaArgClass):
            debug: Optional[bool] = KliamkaArg("--debug", "Debug", default=True)

        instance = Args.from_args(Args.create_parser().parse_args([]))
        assert instance.debug is True

    def test_flag_still_sets_true(self, monkeypatch) -> None:
        monkeypatch.setenv("BDT_DEBUG", "false")

        class Args(KliamkaArgClass):
            debug: Optional[bool] = KliamkaArg(
                "--debug", "Debug", default=True, env="BDT_DEBUG"
            )

        instance = Args.from_args(Args.create_parser().parse_args(["--debug"]))
        assert instance.debug is True


# ── 1.5: invalid env values must raise KliamkaError, not a traceback ─


class TestEnvErrorHandling:
    def test_bad_env_value_with_converter_raises_kliamka_error(
        self, monkeypatch, clean_converter_registry
    ) -> None:
        register_converter(datetime, datetime.fromisoformat)
        monkeypatch.setenv("ENV_TS", "not-a-date")

        class Args(KliamkaArgClass):
            ts: Optional[datetime] = KliamkaArg("--ts", "Timestamp", env="ENV_TS")

        args = Args.create_parser().parse_args([])
        with pytest.raises(KliamkaError, match=r"ENV_TS"):
            Args.from_args(args)

    def test_bad_env_enum_value_raises_kliamka_error(self, monkeypatch) -> None:
        monkeypatch.setenv("ENV_LEVEL", "loud")

        class Args(KliamkaArgClass):
            level: Optional[LogLevel] = KliamkaArg("--level", "Level", env="ENV_LEVEL")

        args = Args.create_parser().parse_args([])
        with pytest.raises(KliamkaError, match=r"ENV_LEVEL"):
            Args.from_args(args)

    def test_bad_env_value_renders_clean_cli_error(
        self, monkeypatch, capsys, clean_converter_registry
    ) -> None:
        register_converter(datetime, datetime.fromisoformat)
        monkeypatch.setenv("ENV_TS", "not-a-date")

        class Args(KliamkaArgClass):
            ts: Optional[datetime] = KliamkaArg("--ts", "Timestamp", env="ENV_TS")

        @kliamka_cli(Args, argv=[])
        def main(args: Args) -> None:
            pytest.fail("Decorator should exit before invoking the wrapped function")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "error:" in captured.err
        assert "ENV_TS" in captured.err
        assert "Traceback" not in captured.err


# ── 1.6: main/subcommand flag collisions must fail fast ─────────────


class TestSubcommandCollision:
    def test_colliding_flag_raises_at_decoration(self) -> None:
        class Main(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        class Sub(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Sub verbose")

        with pytest.raises(KliamkaError, match=r"--verbose"):

            @kliamka_subcommands(Main, {"run": Sub})
            def main(args, command, cmd_args) -> None:
                pass

    def test_reserved_command_dest_raises(self) -> None:
        class Main(KliamkaArgClass):
            cmd: Optional[str] = KliamkaArg("--_command", "Reserved")

        class Sub(KliamkaArgClass):
            name: str = KliamkaArg("name", "Name", positional=True)

        with pytest.raises(KliamkaError, match=r"_command"):

            @kliamka_subcommands(Main, {"run": Sub})
            def main(args, command, cmd_args) -> None:
                pass

    def test_distinct_flags_still_work(self) -> None:
        class Main(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        class Sub(KliamkaArgClass):
            loud: Optional[bool] = KliamkaArg("--loud", "Loud")

        result_holder = []

        @kliamka_subcommands(Main, {"run": Sub}, argv=["--verbose", "run"])
        def main(args, command, cmd_args) -> None:
            result_holder.append((args.verbose, cmd_args.loud))

        main()
        assert result_holder[0] == (True, False)

    def test_same_flag_in_two_subcommands_is_allowed(self) -> None:
        class Main(KliamkaArgClass):
            pass

        class SubA(KliamkaArgClass):
            force: Optional[bool] = KliamkaArg("--force", "Force")

        class SubB(KliamkaArgClass):
            force: Optional[bool] = KliamkaArg("--force", "Force")

        result_holder = []

        @kliamka_subcommands(Main, {"a": SubA, "b": SubB}, argv=["b", "--force"])
        def main(args, command, cmd_args) -> None:
            result_holder.append((command, cmd_args.force))

        main()
        assert result_holder[0] == ("b", True)


# ── 1.7: env-var lists must honor per-field converter= ──────────────


class TestEnvListConverter:
    def test_env_list_applies_per_field_converter(self, monkeypatch) -> None:
        monkeypatch.setenv("ELC_FILES", "a.txt,b.txt")

        class Args(KliamkaArgClass):
            files: List[Path] = KliamkaArg(
                "--files",
                "Files",
                env="ELC_FILES",
                converter=lambda s: Path(s).resolve(),
            )

        parser = Args.create_parser()
        from_env = Args.from_args(parser.parse_args([])).files
        cli_args = parser.parse_args(["--files", "a.txt", "b.txt"])
        from_cli = Args.from_args(cli_args).files

        assert from_env == from_cli
        assert all(p.is_absolute() for p in from_env)
