"""Regression tests."""

from typing import Optional, Union, cast

import pytest
from pydantic import ValidationError, field_validator, model_validator

from kliamka import (
    KliamkaArg,
    KliamkaArgClass,
    KliamkaError,
    ParserMeta,
    kliamka_subcommands,
)
from kliamka._core import _format_validation_error


class TestSupportedUnions:
    def test_pep604_wide_union_is_rejected_cleanly(self) -> None:
        class Args(KliamkaArgClass):
            value: int | str = KliamkaArg("--value")

        with pytest.raises(KliamkaError, match=r"only Optional\[T\]"):
            Args.create_parser()

    def test_typing_wide_union_is_rejected_cleanly(self) -> None:
        class Args(KliamkaArgClass):
            value: Union[int, str] = KliamkaArg("--value")

        with pytest.raises(KliamkaError, match=r"unsupported union annotation"):
            Args.create_parser()

    def test_optional_union_remains_supported(self) -> None:
        class Args(KliamkaArgClass):
            value: Optional[int] = KliamkaArg("--value")

        parsed = Args.create_parser().parse_args(["--value", "4"])
        assert Args.from_args(parsed).value == 4


class TestSubcommandParserMeta:
    def test_main_usage_is_honored(self, capsys: pytest.CaptureFixture[str]) -> None:
        class Main(KliamkaArgClass):
            parser_meta = ParserMeta(usage="tool [GLOBAL] COMMAND")

        class Run(KliamkaArgClass):
            pass

        @kliamka_subcommands(Main, {"run": Run}, argv=["--help"])
        def command(*args: object) -> None:
            pytest.fail("help should exit before invoking the command")

        with pytest.raises(SystemExit) as exc_info:
            command()

        assert exc_info.value.code == 0
        assert "usage: tool [GLOBAL] COMMAND" in capsys.readouterr().out

    def test_subcommand_help_honors_meta(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        class Main(KliamkaArgClass):
            parser_meta = ParserMeta(prog="tool")

        class Run(KliamkaArgClass):
            parser_meta = ParserMeta(
                prog="worker",
                usage="worker [OPTIONS]",
                epilog="Worker documentation.",
            )

        @kliamka_subcommands(Main, {"run": Run}, argv=["run", "--help"])
        def command(*args: object) -> None:
            pytest.fail("help should exit before invoking the command")

        with pytest.raises(SystemExit) as exc_info:
            command()

        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "usage: worker [OPTIONS]" in output
        assert "Worker documentation." in output

    def test_subcommand_version_is_honored(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        class Main(KliamkaArgClass):
            pass

        class Run(KliamkaArgClass):
            parser_meta = ParserMeta(version="worker 2.0")

        @kliamka_subcommands(Main, {"run": Run}, argv=["run", "--version"])
        def command(*args: object) -> None:
            pytest.fail("version should exit before invoking the command")

        with pytest.raises(SystemExit) as exc_info:
            command()

        assert exc_info.value.code == 0
        assert capsys.readouterr().out.strip() == "worker 2.0"

    def test_subcommand_validation_error_honors_meta(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("WORKER_COUNT", "many")

        class Main(KliamkaArgClass):
            parser_meta = ParserMeta(prog="tool", usage="tool GLOBAL COMMAND")

        class Run(KliamkaArgClass):
            parser_meta = ParserMeta(prog="worker", usage="worker [OPTIONS]")
            count: int = KliamkaArg("--count", env="WORKER_COUNT")

        @kliamka_subcommands(Main, {"run": Run}, argv=["run"])
        def command(*args: object) -> None:
            pytest.fail("validation should exit before invoking the command")

        with pytest.raises(SystemExit) as exc_info:
            command()

        assert exc_info.value.code == 2
        stderr = capsys.readouterr().err
        assert "usage: worker [OPTIONS]" in stderr
        assert "worker: error:" in stderr
        assert "WORKER_COUNT" in stderr


class TestEnvironmentValidation:
    @pytest.mark.parametrize("raw", ["true", "1", "yes", "on", " TRUE "])
    def test_documented_true_spellings(
        self, raw: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STRICT_BOOL", raw)

        class Args(KliamkaArgClass):
            enabled: bool = KliamkaArg("--enabled", env="STRICT_BOOL")

        assert Args.from_args(Args.create_parser().parse_args([])).enabled is True

    @pytest.mark.parametrize("raw", ["false", "0", "no", "off", " FALSE "])
    def test_documented_false_spellings(
        self, raw: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STRICT_BOOL", raw)

        class Args(KliamkaArgClass):
            enabled: bool = KliamkaArg("--enabled", env="STRICT_BOOL")

        assert Args.from_args(Args.create_parser().parse_args([])).enabled is False

    def test_unknown_bool_names_environment_variable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STRICT_BOOL", "ture")

        class Args(KliamkaArgClass):
            enabled: bool = KliamkaArg("--enabled", env="STRICT_BOOL")

        with pytest.raises(KliamkaError, match=r"STRICT_BOOL.*invalid boolean"):
            Args.from_args(Args.create_parser().parse_args([]))

    def test_builtin_conversion_error_names_environment_variable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STRICT_COUNT", "many")

        class Args(KliamkaArgClass):
            count: int = KliamkaArg("--count", env="STRICT_COUNT")

        with pytest.raises(KliamkaError, match=r"STRICT_COUNT.*invalid literal"):
            Args.from_args(Args.create_parser().parse_args([]))

    def test_field_validation_error_names_environment_variable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("POSITIVE_COUNT", "-1")

        class Args(KliamkaArgClass):
            count: int = KliamkaArg("--count", env="POSITIVE_COUNT")

            @field_validator("count")
            @classmethod
            def require_positive(cls, value: int) -> int:
                if value <= 0:
                    raise ValueError("must be positive")
                return value

        with pytest.raises(KliamkaError, match=r"POSITIVE_COUNT.*must be positive"):
            Args.from_args(Args.create_parser().parse_args([]))

    def test_model_validation_error_names_environment_sources(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MINIMUM", "5")

        class Args(KliamkaArgClass):
            minimum: int = KliamkaArg("--minimum", env="MINIMUM")
            maximum: int = KliamkaArg("--maximum", default=3)

            @model_validator(mode="after")
            def validate_range(self) -> "Args":
                if self.minimum > self.maximum:
                    raise ValueError("minimum must not exceed maximum")
                return self

        with pytest.raises(KliamkaError, match=r"MINIMUM.*minimum must not exceed"):
            Args.from_args(Args.create_parser().parse_args([]))

    def test_empty_environment_value_overrides_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("EMPTY_TEXT", "")

        class Args(KliamkaArgClass):
            text: str = KliamkaArg("--text", default="fallback", env="EMPTY_TEXT")

        assert Args.from_args(Args.create_parser().parse_args([])).text == ""


class TestCanonicalDestinations:
    def test_normalized_option_spellings_do_not_share_values(self) -> None:
        class Args(KliamkaArgClass):
            first: Optional[str] = KliamkaArg("--foo-bar")
            second: Optional[str] = KliamkaArg("--foo_bar")

        parser = Args.create_parser()
        namespace = parser.parse_args(["--foo-bar", "A", "--foo_bar", "B"])
        instance = Args.from_args(namespace)

        assert vars(namespace)["first"] == "A"
        assert vars(namespace)["second"] == "B"
        assert instance.first == "A"
        assert instance.second == "B"

    def test_positional_uses_field_name_as_dest_and_flag_as_metavar(self) -> None:
        class Args(KliamkaArgClass):
            input_file: str = KliamkaArg("input-file", positional=True)

        parser = Args.create_parser()
        namespace = parser.parse_args(["data.txt"])

        assert vars(namespace) == {"input_file": "data.txt"}
        assert "input-file" in parser.format_help()
        assert Args.from_args(namespace).input_file == "data.txt"

    def test_ordinary_main_field_cannot_share_subcommand_destination(self) -> None:
        class Main(KliamkaArgClass):
            loud: bool = False

        class Run(KliamkaArgClass):
            loud: bool = KliamkaArg("--verbose")

        with pytest.raises(KliamkaError, match=r"both parse into 'loud'"):
            kliamka_subcommands(Main, {"run": Run})

    def test_matching_ordinary_fields_without_cli_destinations_are_allowed(
        self,
    ) -> None:
        class Main(KliamkaArgClass):
            label: str = "main"

        class Run(KliamkaArgClass):
            label: str = "run"

        @kliamka_subcommands(Main, {"run": Run}, argv=["run"])
        def command(
            args: Main, command_name: str, cmd_args: Run
        ) -> tuple[str, str, str]:
            return args.label, command_name, cmd_args.label

        assert command() == ("main", "run", "run")


class TestValidationErrorFormatting:
    def test_root_location_is_not_filtered(self) -> None:
        class FakeValidationError:
            def errors(self, *, include_url: bool) -> list[dict[str, object]]:
                assert include_url is False
                return [{"loc": ("__root__",), "msg": "Invalid value"}]

        error = cast(ValidationError, FakeValidationError())
        assert _format_validation_error(error) == "__root__: Invalid value"
