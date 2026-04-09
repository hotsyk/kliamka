"""Tests for kliamka module."""

import argparse
import importlib
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional
from unittest.mock import patch

import pytest
from pydantic import model_validator

from kliamka import (
    KliamkaArg,
    KliamkaArgClass,
    KliamkaError,
    ParserMeta,
    __version__,
    kliamka_cli,
    kliamka_subcommands,
    register_converter,
    unregister_converter,
)


class TestKliamkaError:
    def test_kliamka_error_inheritance(self) -> None:
        assert issubclass(KliamkaError, Exception)

    def test_kliamka_error_raise(self) -> None:
        with pytest.raises(KliamkaError):
            raise KliamkaError("Test error")


class TestKliamkaArg:
    def test_kliamka_arg_creation(self) -> None:
        arg = KliamkaArg("--verbose", "Enable verbose output", False)
        assert arg.flag == "--verbose"
        assert arg.help_text == "Enable verbose output"
        assert arg.default is False

    def test_kliamka_arg_set_name(self) -> None:
        arg = KliamkaArg("--debug")
        arg.__set_name__(type, "debug")
        assert arg.name == "debug"

    def test_kliamka_arg_short_flag(self) -> None:
        arg = KliamkaArg("--verbose", "Verbose", short="-v")
        assert arg.short == "-v"
        assert arg.flag == "--verbose"

    def test_kliamka_arg_mutually_exclusive(self) -> None:
        arg = KliamkaArg("--json", "JSON output", mutually_exclusive="format")
        assert arg.mutually_exclusive == "format"


class TestKliamkaArgClass:
    def test_create_parser_boolean(self) -> None:
        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Enable verbose output")

        parser = TestArgs.create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

        args = parser.parse_args([])
        assert args.verbose is False

    def test_create_parser_string(self) -> None:
        class TestArgs(KliamkaArgClass):
            name: Optional[str] = KliamkaArg("--name", "Your name", "default")

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--name", "Alice"])
        assert args.name == "Alice"

        args = parser.parse_args([])
        assert args.name == "default"

    def test_from_args(self) -> None:
        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Enable verbose")
            count: Optional[int] = KliamkaArg("--count", "Count", 1)

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--verbose", "--count", "5"])
        instance = TestArgs.from_args(args)

        assert instance.verbose is True
        assert instance.count == 5


class TestKliamkaDecorators:
    def test_kliamka_cli_decorator(self) -> None:
        class TestArgs(KliamkaArgClass):
            test_flag: Optional[bool] = KliamkaArg("--test", "Test flag")

        @kliamka_cli(TestArgs)
        def test_func(args: TestArgs) -> str:
            return f"test_flag: {args.test_flag}"

        assert hasattr(test_func, "_kliamka_func")
        assert hasattr(test_func, "_kliamka_arg_class")
        assert test_func._kliamka_arg_class == TestArgs

    @patch("sys.argv", ["test", "--test"])
    def test_kliamka_cli_execution(self) -> None:
        class TestArgs(KliamkaArgClass):
            test_flag: Optional[bool] = KliamkaArg("--test", "Test flag")

        result_holder = []

        @kliamka_cli(TestArgs)
        def test_func(args: TestArgs) -> None:
            result_holder.append(args.test_flag)

        test_func()
        assert result_holder[0] is True


class TestModuleInfo:
    def test_version_exists(self) -> None:
        assert __version__ == "0.5.0"

    def test_imports_use_local_src_tree(self) -> None:
        kliamka_module = importlib.import_module("kliamka")
        module_path = getattr(kliamka_module, "__file__", "")

        assert module_path
        assert "site-packages" not in module_path
        assert (
            Path(module_path)
            .resolve()
            .is_relative_to(Path(__file__).resolve().parents[1] / "src")
        )

    def test_public_import_uses_package_api(self) -> None:
        kliamka_module = importlib.import_module("kliamka")

        assert KliamkaArg is kliamka_module.KliamkaArg
        assert KliamkaArgClass is kliamka_module.KliamkaArgClass
        assert kliamka_cli is kliamka_module.kliamka_cli
        assert kliamka_subcommands is kliamka_module.kliamka_subcommands
        assert kliamka_module.__version__ == __version__

    def test_all_exports(self) -> None:
        expected_exports = {
            "KliamkaError",
            "KliamkaArg",
            "KliamkaArgClass",
            "ParserMeta",
            "kliamka_cli",
            "kliamka_subcommands",
            "__version__",
            "__author__",
            "__email__",
        }

        kliamka_module = importlib.import_module("kliamka")
        public_exports = set(getattr(kliamka_module, "__all__", ()))

        assert expected_exports.issubset(public_exports)


class TestKliamkaEnums:
    def test_enum_argument_creation(self) -> None:
        class Status(Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        class TestArgs(KliamkaArgClass):
            status: Status = KliamkaArg("--status", "Status type", Status.ACTIVE)

        parser = TestArgs.create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_enum_argument_parsing(self) -> None:
        class LogLevel(Enum):
            DEBUG = "debug"
            INFO = "info"
            ERROR = "error"

        class TestArgs(KliamkaArgClass):
            log_level: LogLevel = KliamkaArg("--log-level", "Log level", LogLevel.INFO)

        parser = TestArgs.create_parser()

        args = parser.parse_args(["--log-level", "debug"])
        instance = TestArgs.from_args(args)
        assert instance.log_level == LogLevel.DEBUG

        args = parser.parse_args([])
        instance = TestArgs.from_args(args)
        assert instance.log_level == LogLevel.INFO

    def test_optional_enum_argument(self) -> None:
        class Priority(Enum):
            LOW = "low"
            HIGH = "high"

        class TestArgs(KliamkaArgClass):
            priority: Optional[Priority] = KliamkaArg(
                "--priority", "Priority level", None
            )

        parser = TestArgs.create_parser()

        args = parser.parse_args([])
        instance = TestArgs.from_args(args)
        assert instance.priority is None

        args = parser.parse_args(["--priority", "high"])
        instance = TestArgs.from_args(args)
        assert instance.priority == Priority.HIGH

    def test_multiple_enum_arguments(self) -> None:
        class Format(Enum):
            JSON = "json"
            XML = "xml"

        class Mode(Enum):
            FAST = "fast"
            SLOW = "slow"

        class TestArgs(KliamkaArgClass):
            output_format: Format = KliamkaArg("--format", "Output format", Format.JSON)
            processing_mode: Mode = KliamkaArg("--mode", "Processing mode", Mode.FAST)

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--format", "xml", "--mode", "slow"])
        instance = TestArgs.from_args(args)

        assert instance.output_format == Format.XML
        assert instance.processing_mode == Mode.SLOW

    @patch("sys.argv", ["test", "--log-level", "error"])
    def test_kliamka_cli_with_enum(self) -> None:
        class LogLevel(Enum):
            DEBUG = "debug"
            INFO = "info"
            ERROR = "error"

        class TestArgs(KliamkaArgClass):
            log_level: LogLevel = KliamkaArg("--log-level", "Log level", LogLevel.INFO)

        result_holder = []

        @kliamka_cli(TestArgs)
        def test_func(args: TestArgs) -> None:
            result_holder.append(args.log_level)

        test_func()
        assert result_holder[0] == LogLevel.ERROR


class TestKliamkaEnumsWithIntegerValues:
    def test_integer_enum_argument_creation(self) -> None:
        class Priority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3

        class TestArgs(KliamkaArgClass):
            priority: Priority = KliamkaArg(
                "--priority", "Priority level", Priority.LOW
            )

        parser = TestArgs.create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_integer_enum_parsing_by_value(self) -> None:
        class Priority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3

        class TestArgs(KliamkaArgClass):
            priority: Priority = KliamkaArg(
                "--priority", "Priority level", Priority.LOW
            )

        parser = TestArgs.create_parser()

        args = parser.parse_args(["--priority", "3"])
        instance = TestArgs.from_args(args)
        assert instance.priority == Priority.HIGH
        assert instance.priority.value == 3

    def test_integer_enum_parsing_by_name(self) -> None:
        class Priority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3

        class TestArgs(KliamkaArgClass):
            priority: Priority = KliamkaArg(
                "--priority", "Priority level", Priority.LOW
            )

        parser = TestArgs.create_parser()

        args = parser.parse_args(["--priority", "HIGH"])
        instance = TestArgs.from_args(args)
        assert instance.priority == Priority.HIGH
        assert instance.priority.value == 3

        args = parser.parse_args(["--priority", "medium"])
        instance = TestArgs.from_args(args)
        assert instance.priority == Priority.MEDIUM
        assert instance.priority.value == 2

    def test_integer_enum_default_value(self) -> None:
        class Priority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3

        class TestArgs(KliamkaArgClass):
            priority: Priority = KliamkaArg(
                "--priority", "Priority level", Priority.MEDIUM
            )

        parser = TestArgs.create_parser()

        args = parser.parse_args([])
        instance = TestArgs.from_args(args)
        assert instance.priority == Priority.MEDIUM
        assert instance.priority.value == 2

    def test_integer_enum_invalid_value_error(self) -> None:
        """Test error handling for invalid enum values."""

        class Priority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3

        class TestArgs(KliamkaArgClass):
            priority: Priority = KliamkaArg(
                "--priority", "Priority level", Priority.LOW
            )

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--priority", "5"])

        with pytest.raises(SystemExit):
            parser.parse_args(["--priority", "invalid"])

    def test_mixed_enum_types(self) -> None:
        class Status(Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        class Priority(Enum):
            LOW = 1
            HIGH = 3

        class TestArgs(KliamkaArgClass):
            status: Status = KliamkaArg("--status", "Status", Status.ACTIVE)
            priority: Priority = KliamkaArg("--priority", "Priority", Priority.LOW)

        parser = TestArgs.create_parser()

        args = parser.parse_args(["--status", "inactive", "--priority", "3"])
        instance = TestArgs.from_args(args)
        assert instance.status == Status.INACTIVE
        assert instance.priority == Priority.HIGH
        assert instance.priority.value == 3

    def test_optional_integer_enum(self) -> None:
        """Test optional enum with integer values."""

        class Priority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3

        class TestArgs(KliamkaArgClass):
            priority: Optional[Priority] = KliamkaArg(
                "--priority", "Priority level", None
            )

        parser = TestArgs.create_parser()

        args = parser.parse_args([])
        instance = TestArgs.from_args(args)
        assert instance.priority is None

        args = parser.parse_args(["--priority", "2"])
        instance = TestArgs.from_args(args)
        assert instance.priority == Priority.MEDIUM

    @patch("sys.argv", ["test", "--priority", "1"])
    def test_kliamka_cli_with_integer_enum(self) -> None:
        class Priority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3

        class TestArgs(KliamkaArgClass):
            priority: Priority = KliamkaArg(
                "--priority", "Priority level", Priority.MEDIUM
            )

        result_holder = []

        @kliamka_cli(TestArgs)
        def test_func(args: TestArgs) -> None:
            result_holder.append(args.priority)

        test_func()
        assert result_holder[0] == Priority.LOW
        assert result_holder[0].value == 1


class TestKliamkaPositionalArguments:
    def test_positional_argument_creation(self) -> None:
        """Test creating a class with a positional argument."""

        class TestArgs(KliamkaArgClass):
            filename: str = KliamkaArg("filename", "Input file", positional=True)

        parser = TestArgs.create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_positional_argument_parsing(self) -> None:
        """Test parsing a positional argument."""

        class TestArgs(KliamkaArgClass):
            filename: str = KliamkaArg("filename", "Input file", positional=True)

        parser = TestArgs.create_parser()
        args = parser.parse_args(["test.txt"])
        instance = TestArgs.from_args(args)

        assert instance.filename == "test.txt"

    def test_positional_without_flag_prefix(self) -> None:
        """Test that arguments without -- are automatically treated as positional."""

        class TestArgs(KliamkaArgClass):
            filename: str = KliamkaArg("filename", "Input file")

        parser = TestArgs.create_parser()
        args = parser.parse_args(["test.txt"])
        instance = TestArgs.from_args(args)

        assert instance.filename == "test.txt"

    def test_positional_with_type(self) -> None:
        """Test positional argument with int type."""

        class TestArgs(KliamkaArgClass):
            count: int = KliamkaArg("count", "Number of items", positional=True)

        parser = TestArgs.create_parser()
        args = parser.parse_args(["42"])
        instance = TestArgs.from_args(args)

        assert instance.count == 42

    def test_optional_positional_argument(self) -> None:
        """Test optional positional argument with default value."""

        class TestArgs(KliamkaArgClass):
            filename: Optional[str] = KliamkaArg(
                "filename", "Input file", default="default.txt"
            )

        parser = TestArgs.create_parser()

        # With value
        args = parser.parse_args(["test.txt"])
        instance = TestArgs.from_args(args)
        assert instance.filename == "test.txt"

        # Without value - uses default
        args = parser.parse_args([])
        instance = TestArgs.from_args(args)
        assert instance.filename == "default.txt"

    def test_multiple_positional_arguments(self) -> None:
        """Test multiple positional arguments."""

        class TestArgs(KliamkaArgClass):
            source: str = KliamkaArg("source", "Source file", positional=True)
            destination: str = KliamkaArg(
                "destination", "Destination file", positional=True
            )

        parser = TestArgs.create_parser()
        args = parser.parse_args(["input.txt", "output.txt"])
        instance = TestArgs.from_args(args)

        assert instance.source == "input.txt"
        assert instance.destination == "output.txt"

    def test_positional_and_optional_arguments(self) -> None:
        """Test mixing positional and optional arguments."""

        class TestArgs(KliamkaArgClass):
            filename: str = KliamkaArg("filename", "Input file", positional=True)
            verbose: Optional[bool] = KliamkaArg("--verbose", "Enable verbose output")
            count: Optional[int] = KliamkaArg("--count", "Number of items", default=1)

        parser = TestArgs.create_parser()

        # Positional + optional
        args = parser.parse_args(["test.txt", "--verbose", "--count", "5"])
        instance = TestArgs.from_args(args)

        assert instance.filename == "test.txt"
        assert instance.verbose is True
        assert instance.count == 5

        # Positional only
        args = parser.parse_args(["test.txt"])
        instance = TestArgs.from_args(args)

        assert instance.filename == "test.txt"
        assert instance.verbose is False
        assert instance.count == 1

    @patch("sys.argv", ["test", "myfile.txt", "--verbose"])
    def test_kliamka_cli_with_positional(self) -> None:
        """Test decorator with positional arguments."""

        class TestArgs(KliamkaArgClass):
            filename: str = KliamkaArg("filename", "Input file", positional=True)
            verbose: Optional[bool] = KliamkaArg("--verbose", "Enable verbose output")

        result_holder = []

        @kliamka_cli(TestArgs)
        def test_func(args: TestArgs) -> None:
            result_holder.append((args.filename, args.verbose))

        test_func()
        assert result_holder[0] == ("myfile.txt", True)

    def test_positional_enum_argument(self) -> None:
        """Test positional argument with enum type."""

        class LogLevel(Enum):
            DEBUG = "debug"
            INFO = "info"
            ERROR = "error"

        class TestArgs(KliamkaArgClass):
            level: LogLevel = KliamkaArg("level", "Log level", positional=True)

        parser = TestArgs.create_parser()
        args = parser.parse_args(["debug"])
        instance = TestArgs.from_args(args)

        assert instance.level == LogLevel.DEBUG


class TestKliamkaListArguments:
    def test_list_string_argument(self) -> None:
        """Test list of strings argument."""

        class TestArgs(KliamkaArgClass):
            files: List[str] = KliamkaArg("--files", "Input files")

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--files", "a.txt", "b.txt", "c.txt"])
        instance = TestArgs.from_args(args)

        assert instance.files == ["a.txt", "b.txt", "c.txt"]

    def test_list_int_argument(self) -> None:
        """Test list of integers argument."""

        class TestArgs(KliamkaArgClass):
            counts: List[int] = KliamkaArg("--counts", "Counts")

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--counts", "1", "2", "3"])
        instance = TestArgs.from_args(args)

        assert instance.counts == [1, 2, 3]

    def test_list_default_value(self) -> None:
        """Test list with default value."""

        class TestArgs(KliamkaArgClass):
            files: List[str] = KliamkaArg(
                "--files", "Input files", default=["default.txt"]
            )

        parser = TestArgs.create_parser()

        # Without args - uses default
        args = parser.parse_args([])
        instance = TestArgs.from_args(args)
        assert instance.files == ["default.txt"]

        # With args
        args = parser.parse_args(["--files", "a.txt", "b.txt"])
        instance = TestArgs.from_args(args)
        assert instance.files == ["a.txt", "b.txt"]

    def test_list_empty_default(self) -> None:
        """Test list with empty default."""

        class TestArgs(KliamkaArgClass):
            files: List[str] = KliamkaArg("--files", "Input files")

        parser = TestArgs.create_parser()
        args = parser.parse_args([])
        instance = TestArgs.from_args(args)

        assert instance.files == []

    def test_list_enum_argument(self) -> None:
        """Test list of enums argument."""

        class LogLevel(Enum):
            DEBUG = "debug"
            INFO = "info"
            ERROR = "error"

        class TestArgs(KliamkaArgClass):
            levels: List[LogLevel] = KliamkaArg("--levels", "Log levels")

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--levels", "debug", "info"])
        instance = TestArgs.from_args(args)

        assert instance.levels == [LogLevel.DEBUG, LogLevel.INFO]

    def test_list_with_other_arguments(self) -> None:
        """Test list argument mixed with other types."""

        class TestArgs(KliamkaArgClass):
            files: List[str] = KliamkaArg("--files", "Input files")
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")
            count: Optional[int] = KliamkaArg("--count", "Count", default=1)

        parser = TestArgs.create_parser()
        args = parser.parse_args(
            ["--files", "a.txt", "b.txt", "--verbose", "--count", "5"]
        )
        instance = TestArgs.from_args(args)

        assert instance.files == ["a.txt", "b.txt"]
        assert instance.verbose is True
        assert instance.count == 5

    def test_positional_list_argument(self) -> None:
        """Test positional list argument."""

        class TestArgs(KliamkaArgClass):
            files: List[str] = KliamkaArg("files", "Input files", positional=True)

        parser = TestArgs.create_parser()
        args = parser.parse_args(["a.txt", "b.txt", "c.txt"])
        instance = TestArgs.from_args(args)

        assert instance.files == ["a.txt", "b.txt", "c.txt"]

    def test_multiple_list_arguments(self) -> None:
        """Test multiple list arguments."""

        class TestArgs(KliamkaArgClass):
            inputs: List[str] = KliamkaArg("--inputs", "Input files")
            outputs: List[str] = KliamkaArg("--outputs", "Output files")

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--inputs", "a.txt", "b.txt", "--outputs", "c.txt"])
        instance = TestArgs.from_args(args)

        assert instance.inputs == ["a.txt", "b.txt"]
        assert instance.outputs == ["c.txt"]

    @patch("sys.argv", ["test", "--files", "x.txt", "y.txt", "--verbose"])
    def test_kliamka_cli_with_list(self) -> None:
        """Test decorator with list arguments."""

        class TestArgs(KliamkaArgClass):
            files: List[str] = KliamkaArg("--files", "Input files")
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")

        result_holder = []

        @kliamka_cli(TestArgs)
        def test_func(args: TestArgs) -> None:
            result_holder.append((args.files, args.verbose))

        test_func()
        assert result_holder[0] == (["x.txt", "y.txt"], True)


class TestKliamkaEnvVarFallback:
    def test_env_var_string(self, monkeypatch) -> None:
        """Test environment variable fallback for string."""
        monkeypatch.setenv("MY_API_KEY", "secret123")

        class TestArgs(KliamkaArgClass):
            api_key: Optional[str] = KliamkaArg(
                "--api-key", "API key", env="MY_API_KEY"
            )

        parser = TestArgs.create_parser()
        args = parser.parse_args([])
        instance = TestArgs.from_args(args)

        assert instance.api_key == "secret123"

    def test_env_var_int(self, monkeypatch) -> None:
        """Test environment variable fallback for int."""
        monkeypatch.setenv("MY_COUNT", "42")

        class TestArgs(KliamkaArgClass):
            count: Optional[int] = KliamkaArg("--count", "Count", env="MY_COUNT")

        parser = TestArgs.create_parser()
        args = parser.parse_args([])
        instance = TestArgs.from_args(args)

        assert instance.count == 42

    def test_env_var_bool_true(self, monkeypatch) -> None:
        """Test environment variable fallback for bool (true values)."""
        for true_val in ["true", "1", "yes", "on", "TRUE", "Yes"]:
            monkeypatch.setenv("MY_DEBUG", true_val)

            class TestArgs(KliamkaArgClass):
                debug: Optional[bool] = KliamkaArg(
                    "--debug", "Debug mode", env="MY_DEBUG"
                )

            parser = TestArgs.create_parser()
            args = parser.parse_args([])
            instance = TestArgs.from_args(args)

            assert instance.debug is True, f"Failed for value: {true_val}"

    def test_env_var_bool_false(self, monkeypatch) -> None:
        """Test environment variable fallback for bool (false values)."""
        monkeypatch.setenv("MY_DEBUG", "false")

        class TestArgs(KliamkaArgClass):
            debug: Optional[bool] = KliamkaArg("--debug", "Debug mode", env="MY_DEBUG")

        parser = TestArgs.create_parser()
        args = parser.parse_args([])
        instance = TestArgs.from_args(args)

        assert instance.debug is False

    def test_env_var_enum(self, monkeypatch) -> None:
        """Test environment variable fallback for enum."""
        monkeypatch.setenv("MY_LOG_LEVEL", "debug")

        class LogLevel(Enum):
            DEBUG = "debug"
            INFO = "info"
            ERROR = "error"

        class TestArgs(KliamkaArgClass):
            log_level: Optional[LogLevel] = KliamkaArg(
                "--log-level", "Log level", env="MY_LOG_LEVEL"
            )

        parser = TestArgs.create_parser()
        args = parser.parse_args([])
        instance = TestArgs.from_args(args)

        assert instance.log_level == LogLevel.DEBUG

    def test_env_var_list(self, monkeypatch) -> None:
        """Test environment variable fallback for list (comma-separated)."""
        monkeypatch.setenv("MY_FILES", "a.txt, b.txt, c.txt")

        class TestArgs(KliamkaArgClass):
            files: List[str] = KliamkaArg("--files", "Input files", env="MY_FILES")

        parser = TestArgs.create_parser()
        args = parser.parse_args([])
        instance = TestArgs.from_args(args)

        assert instance.files == ["a.txt", "b.txt", "c.txt"]

    def test_cli_overrides_env(self, monkeypatch) -> None:
        """Test that CLI value takes priority over env var."""
        monkeypatch.setenv("MY_API_KEY", "env_secret")

        class TestArgs(KliamkaArgClass):
            api_key: Optional[str] = KliamkaArg(
                "--api-key", "API key", env="MY_API_KEY"
            )

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--api-key", "cli_secret"])
        instance = TestArgs.from_args(args)

        assert instance.api_key == "cli_secret"

    def test_env_var_not_set_uses_default(self) -> None:
        """Test that default is used when env var is not set."""

        class TestArgs(KliamkaArgClass):
            api_key: Optional[str] = KliamkaArg(
                "--api-key", "API key", default="default_key", env="MY_API_KEY"
            )

        parser = TestArgs.create_parser()
        args = parser.parse_args([])
        instance = TestArgs.from_args(args)

        assert instance.api_key == "default_key"

    def test_help_shows_env_var(self) -> None:
        """Test that help text includes env var name."""

        class TestArgs(KliamkaArgClass):
            api_key: Optional[str] = KliamkaArg(
                "--api-key", "API key", env="MY_API_KEY"
            )

        parser = TestArgs.create_parser()
        help_text = parser.format_help()

        assert "[env: MY_API_KEY]" in help_text

    @patch("sys.argv", ["test", "--verbose"])
    def test_kliamka_cli_with_env(self, monkeypatch) -> None:
        """Test decorator with environment variable."""
        monkeypatch.setenv("MY_COUNT", "99")

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")
            count: Optional[int] = KliamkaArg(
                "--count", "Count", default=1, env="MY_COUNT"
            )

        result_holder = []

        @kliamka_cli(TestArgs)
        def test_func(args: TestArgs) -> None:
            result_holder.append((args.verbose, args.count))

        test_func()
        assert result_holder[0] == (True, 99)


class TestKliamkaSubcommands:
    def test_subcommand_decorator_creation(self) -> None:
        """Test creating a decorator with subcommands."""

        class MainArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")

        class AddArgs(KliamkaArgClass):
            name: str = KliamkaArg("name", "Item name", positional=True)

        @kliamka_subcommands(MainArgs, {"add": AddArgs})
        def test_func(args, command, cmd_args):
            pass

        assert hasattr(test_func, "_kliamka_func")
        assert hasattr(test_func, "_kliamka_main_class")
        assert hasattr(test_func, "_kliamka_subcommands")
        assert test_func._kliamka_main_class == MainArgs
        assert "add" in test_func._kliamka_subcommands

    @patch("sys.argv", ["test", "add", "myitem"])
    def test_subcommand_add(self) -> None:
        """Test subcommand parsing with add command."""

        class MainArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")

        class AddArgs(KliamkaArgClass):
            """Add a new item."""

            name: str = KliamkaArg("name", "Item name", positional=True)

        result_holder = []

        @kliamka_subcommands(MainArgs, {"add": AddArgs})
        def test_func(args, command, cmd_args):
            result_holder.append((args.verbose, command, cmd_args.name))

        test_func()
        assert result_holder[0] == (False, "add", "myitem")

    @patch("sys.argv", ["test", "--verbose", "add", "myitem"])
    def test_subcommand_with_global_args(self) -> None:
        """Test subcommand with global arguments."""

        class MainArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")

        class AddArgs(KliamkaArgClass):
            name: str = KliamkaArg("name", "Item name", positional=True)

        result_holder = []

        @kliamka_subcommands(MainArgs, {"add": AddArgs})
        def test_func(args, command, cmd_args):
            result_holder.append((args.verbose, command, cmd_args.name))

        test_func()
        assert result_holder[0] == (True, "add", "myitem")

    @patch("sys.argv", ["test", "remove", "123", "--force"])
    def test_multiple_subcommands(self) -> None:
        """Test multiple subcommands."""

        class MainArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")

        class AddArgs(KliamkaArgClass):
            name: str = KliamkaArg("name", "Item name", positional=True)

        class RemoveArgs(KliamkaArgClass):
            id: int = KliamkaArg("id", "Item ID", positional=True)
            force: Optional[bool] = KliamkaArg("--force", "Force removal")

        result_holder = []

        @kliamka_subcommands(MainArgs, {"add": AddArgs, "remove": RemoveArgs})
        def test_func(args, command, cmd_args):
            if command == "remove":
                result_holder.append((command, cmd_args.id, cmd_args.force))

        test_func()
        assert result_holder[0] == ("remove", 123, True)

    @patch("sys.argv", ["test", "list", "--format", "json", "--count", "10"])
    def test_subcommand_with_optional_args(self) -> None:
        """Test subcommand with optional arguments."""

        class MainArgs(KliamkaArgClass):
            pass

        class ListArgs(KliamkaArgClass):
            format: Optional[str] = KliamkaArg(
                "--format", "Output format", default="text"
            )
            count: Optional[int] = KliamkaArg("--count", "Number of items", default=5)

        result_holder = []

        @kliamka_subcommands(MainArgs, {"list": ListArgs})
        def test_func(args, command, cmd_args):
            result_holder.append((cmd_args.format, cmd_args.count))

        test_func()
        assert result_holder[0] == ("json", 10)

    @patch("sys.argv", ["test", "list"])
    def test_subcommand_with_defaults(self) -> None:
        """Test subcommand uses default values."""

        class MainArgs(KliamkaArgClass):
            pass

        class ListArgs(KliamkaArgClass):
            format: Optional[str] = KliamkaArg(
                "--format", "Output format", default="text"
            )
            count: Optional[int] = KliamkaArg("--count", "Number of items", default=5)

        result_holder = []

        @kliamka_subcommands(MainArgs, {"list": ListArgs})
        def test_func(args, command, cmd_args):
            result_holder.append((cmd_args.format, cmd_args.count))

        test_func()
        assert result_holder[0] == ("text", 5)

    @patch("sys.argv", ["test", "files", "--files", "a.txt", "b.txt"])
    def test_subcommand_with_list_args(self) -> None:
        """Test subcommand with list arguments."""

        class MainArgs(KliamkaArgClass):
            pass

        class FilesArgs(KliamkaArgClass):
            files: List[str] = KliamkaArg("--files", "Input files")

        result_holder = []

        @kliamka_subcommands(MainArgs, {"files": FilesArgs})
        def test_func(args, command, cmd_args):
            result_holder.append(cmd_args.files)

        test_func()
        assert result_holder[0] == ["a.txt", "b.txt"]

    @patch("sys.argv", ["test", "log", "--level", "debug"])
    def test_subcommand_with_enum(self) -> None:
        """Test subcommand with enum argument."""

        class LogLevel(Enum):
            DEBUG = "debug"
            INFO = "info"
            ERROR = "error"

        class MainArgs(KliamkaArgClass):
            pass

        class LogArgs(KliamkaArgClass):
            level: LogLevel = KliamkaArg("--level", "Log level", default=LogLevel.INFO)

        result_holder = []

        @kliamka_subcommands(MainArgs, {"log": LogArgs})
        def test_func(args, command, cmd_args):
            result_holder.append(cmd_args.level)

        test_func()
        assert result_holder[0] == LogLevel.DEBUG


# ── #8: Short flags ─────────────────────────────────────────────


class TestShortFlags:
    def test_short_flag_parsing(self) -> None:
        """Test that short flags like -v work alongside --verbose."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg(
                "--verbose", "Verbose output", short="-v"
            )

        parser = TestArgs.create_parser()

        args = parser.parse_args(["-v"])
        assert args.verbose is True

        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

        args = parser.parse_args([])
        assert args.verbose is False

    def test_short_flag_with_value(self) -> None:
        """Test short flag with a value argument."""

        class TestArgs(KliamkaArgClass):
            count: Optional[int] = KliamkaArg("--count", "Count", default=1, short="-c")

        parser = TestArgs.create_parser()

        args = parser.parse_args(["-c", "5"])
        instance = TestArgs.from_args(args)
        assert instance.count == 5

        args = parser.parse_args(["--count", "10"])
        instance = TestArgs.from_args(args)
        assert instance.count == 10

    def test_short_flag_in_help(self) -> None:
        """Test that short flag appears in help text."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg(
                "--verbose", "Verbose output", short="-v"
            )

        parser = TestArgs.create_parser()
        help_text = parser.format_help()
        assert "-v" in help_text
        assert "--verbose" in help_text

    def test_multiple_short_flags(self) -> None:
        """Test multiple short flags together."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose", short="-v")
            output: Optional[str] = KliamkaArg("--output", "Output file", short="-o")

        parser = TestArgs.create_parser()
        args = parser.parse_args(["-v", "-o", "out.txt"])
        instance = TestArgs.from_args(args)

        assert instance.verbose is True
        assert instance.output == "out.txt"

    @patch("sys.argv", ["test", "-v", "-c", "3"])
    def test_short_flags_with_decorator(self) -> None:
        """Test short flags work through the decorator."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose", short="-v")
            count: Optional[int] = KliamkaArg("--count", "Count", default=1, short="-c")

        result_holder = []

        @kliamka_cli(TestArgs)
        def test_func(args: TestArgs) -> None:
            result_holder.append((args.verbose, args.count))

        test_func()
        assert result_holder[0] == (True, 3)


# ── #9: Help customization ──────────────────────────────────────


class TestHelpCustomization:
    def test_custom_prog(self) -> None:
        """Test custom program name in help."""

        class TestArgs(KliamkaArgClass):
            """My cool app."""

            parser_meta = ParserMeta(prog="myapp")
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        parser = TestArgs.create_parser()
        assert parser.prog == "myapp"
        assert "myapp" in parser.format_usage()

    def test_custom_epilog(self) -> None:
        """Test custom epilog text."""

        class TestArgs(KliamkaArgClass):
            """Main description."""

            parser_meta = ParserMeta(epilog="See https://example.com for more info.")
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        parser = TestArgs.create_parser()
        assert parser.epilog == "See https://example.com for more info."
        help_text = parser.format_help()
        assert "https://example.com" in help_text

    def test_custom_usage(self) -> None:
        """Test custom usage string."""

        class TestArgs(KliamkaArgClass):
            parser_meta = ParserMeta(usage="myapp [options] FILE")
            filename: str = KliamkaArg("filename", "Input file")

        parser = TestArgs.create_parser()
        assert "myapp [options] FILE" in parser.format_usage()

    def test_docstring_as_description(self) -> None:
        """Test that class docstring is used as description."""

        class TestArgs(KliamkaArgClass):
            """Process files with advanced options."""

            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        parser = TestArgs.create_parser()
        assert parser.description == "Process files with advanced options."

    def test_all_customizations_together(self) -> None:
        """Test prog, usage, epilog, and description together."""

        class TestArgs(KliamkaArgClass):
            """My app description."""

            parser_meta = ParserMeta(
                prog="myapp",
                usage="myapp [-v] FILE",
                epilog="Example: myapp -v test.txt",
            )
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose", short="-v")

        parser = TestArgs.create_parser()
        help_text = parser.format_help()
        assert "myapp" in help_text
        assert "myapp [-v] FILE" in help_text
        assert "Example: myapp -v test.txt" in help_text


# ── #10: Mutually exclusive argument groups ──────────────────────


class TestMutuallyExclusiveGroups:
    def test_mutually_exclusive_basic(self) -> None:
        """Test that mutually exclusive args cannot be used together."""

        class TestArgs(KliamkaArgClass):
            json_out: Optional[bool] = KliamkaArg(
                "--json", "JSON output", mutually_exclusive="format"
            )
            csv_out: Optional[bool] = KliamkaArg(
                "--csv", "CSV output", mutually_exclusive="format"
            )

        parser = TestArgs.create_parser()

        # Each alone works
        args = parser.parse_args(["--json"])
        assert args.json is True

        args = parser.parse_args(["--csv"])
        assert args.csv is True

        # Both together should fail
        with pytest.raises(SystemExit):
            parser.parse_args(["--json", "--csv"])

    def test_mutually_exclusive_with_values(self) -> None:
        """Test mutual exclusion with value arguments."""

        class TestArgs(KliamkaArgClass):
            output_json: Optional[str] = KliamkaArg(
                "--json-file",
                "JSON output file",
                mutually_exclusive="output",
            )
            output_csv: Optional[str] = KliamkaArg(
                "--csv-file",
                "CSV output file",
                mutually_exclusive="output",
            )

        parser = TestArgs.create_parser()

        args = parser.parse_args(["--json-file", "out.json"])
        instance = TestArgs.from_args(args)
        assert instance.output_json == "out.json"
        assert instance.output_csv is None

        with pytest.raises(SystemExit):
            parser.parse_args(["--json-file", "a.json", "--csv-file", "b.csv"])

    def test_mutually_exclusive_with_regular_args(self) -> None:
        """Test exclusive group mixed with regular arguments."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")
            json_out: Optional[bool] = KliamkaArg(
                "--json", "JSON output", mutually_exclusive="format"
            )
            xml_out: Optional[bool] = KliamkaArg(
                "--xml", "XML output", mutually_exclusive="format"
            )

        parser = TestArgs.create_parser()

        # Regular + one exclusive works
        args = parser.parse_args(["--verbose", "--json"])
        instance = TestArgs.from_args(args)
        assert instance.verbose is True
        assert instance.json_out is True
        assert instance.xml_out is False

    def test_multiple_exclusive_groups(self) -> None:
        """Test multiple independent exclusive groups."""

        class TestArgs(KliamkaArgClass):
            json_out: Optional[bool] = KliamkaArg(
                "--json", "JSON", mutually_exclusive="format"
            )
            csv_out: Optional[bool] = KliamkaArg(
                "--csv", "CSV", mutually_exclusive="format"
            )
            quiet: Optional[bool] = KliamkaArg(
                "--quiet", "Quiet", mutually_exclusive="verbosity"
            )
            debug: Optional[bool] = KliamkaArg(
                "--debug", "Debug", mutually_exclusive="verbosity"
            )

        parser = TestArgs.create_parser()

        # One from each group works
        args = parser.parse_args(["--json", "--quiet"])
        instance = TestArgs.from_args(args)
        assert instance.json_out is True
        assert instance.quiet is True

        # Two from same group fails
        with pytest.raises(SystemExit):
            parser.parse_args(["--quiet", "--debug"])


# ── #11: Pydantic validation ────────────────────────────────────


class TestPydanticValidation:
    def test_range_validation(self) -> None:
        """Test that Pydantic validators work for range checks."""

        class TestArgs(KliamkaArgClass):
            port: Optional[int] = KliamkaArg("--port", "Port number", default=8080)

            @model_validator(mode="after")
            def validate_port(self) -> "TestArgs":
                if self.port is not None and not (1 <= self.port <= 65535):
                    raise ValueError(f"Port must be 1-65535, got {self.port}")
                return self

        parser = TestArgs.create_parser()

        # Valid port
        args = parser.parse_args(["--port", "3000"])
        instance = TestArgs.from_args(args)
        assert instance.port == 3000

        # Invalid port
        args = parser.parse_args(["--port", "99999"])
        with pytest.raises(
            KliamkaError,
            match=r"Port must be 1-65535, got 99999",
        ):
            TestArgs.from_args(args)

    def test_cross_field_validation(self) -> None:
        """Test validation that depends on multiple fields."""

        class TestArgs(KliamkaArgClass):
            min_val: Optional[int] = KliamkaArg("--min", "Minimum", default=0)
            max_val: Optional[int] = KliamkaArg("--max", "Maximum", default=100)

            @model_validator(mode="after")
            def validate_range(self) -> "TestArgs":
                if (
                    self.min_val is not None
                    and self.max_val is not None
                    and self.min_val > self.max_val
                ):
                    raise ValueError(
                        f"min ({self.min_val}) must be <= max ({self.max_val})"
                    )
                return self

        parser = TestArgs.create_parser()

        # Valid
        args = parser.parse_args(["--min", "10", "--max", "50"])
        instance = TestArgs.from_args(args)
        assert instance.min_val == 10
        assert instance.max_val == 50

        # Invalid
        args = parser.parse_args(["--min", "100", "--max", "10"])
        with pytest.raises(
            KliamkaError,
            match=r"min \(100\) must be <= max \(10\)",
        ):
            TestArgs.from_args(args)

    def test_string_pattern_validation(self) -> None:
        """Test string pattern validation."""
        import re

        class TestArgs(KliamkaArgClass):
            email: Optional[str] = KliamkaArg("--email", "Email address")

            @model_validator(mode="after")
            def validate_email(self) -> "TestArgs":
                if self.email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", self.email):
                    raise ValueError(f"Invalid email: {self.email}")
                return self

        parser = TestArgs.create_parser()

        # Valid
        args = parser.parse_args(["--email", "user@example.com"])
        instance = TestArgs.from_args(args)
        assert instance.email == "user@example.com"

        # Invalid
        args = parser.parse_args(["--email", "not-an-email"])
        with pytest.raises(KliamkaError, match=r"Invalid email: not-an-email"):
            TestArgs.from_args(args)


# ── #12: --version flag ─────────────────────────────────────────


class TestVersionFlag:
    def test_version_flag(self) -> None:
        """Test that --version prints version and exits."""

        class TestArgs(KliamkaArgClass):
            parser_meta = ParserMeta(version="myapp 1.2.3")
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_version_flag_output(self, capsys) -> None:
        """Test --version output content."""

        class TestArgs(KliamkaArgClass):
            parser_meta = ParserMeta(version="myapp 2.0.0")
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

        captured = capsys.readouterr()
        assert "myapp 2.0.0" in captured.out

    def test_no_version_flag_by_default(self) -> None:
        """Test that --version is not added without version."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        parser = TestArgs.create_parser()

        # --version should be unrecognized
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code != 0

    def test_version_with_subcommands(self) -> None:
        """Test --version with subcommands."""

        class MainArgs(KliamkaArgClass):
            parser_meta = ParserMeta(version="mycli 3.0.0")

        class AddArgs(KliamkaArgClass):
            name: str = KliamkaArg("name", "Name", positional=True)

        @kliamka_subcommands(MainArgs, {"add": AddArgs})
        def main(args, command, cmd_args):
            pass

        assert hasattr(main, "_kliamka_main_class")


# ── #13: Error handling tests ────────────────────────────────────


class TestErrorHandling:
    def test_missing_required_positional(self) -> None:
        """Test error when required positional arg is missing."""

        class TestArgs(KliamkaArgClass):
            filename: str = KliamkaArg("filename", "Input file", positional=True)

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([])
        assert exc_info.value.code != 0

    def test_invalid_int_value(self) -> None:
        """Test error for non-integer value to int argument."""

        class TestArgs(KliamkaArgClass):
            count: Optional[int] = KliamkaArg("--count", "Count", default=1)

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--count", "abc"])

    def test_invalid_float_value(self) -> None:
        """Test error for non-float value to float argument."""

        class TestArgs(KliamkaArgClass):
            rate: Optional[float] = KliamkaArg("--rate", "Rate", default=1.0)

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--rate", "not-a-number"])

    def test_unknown_flag(self) -> None:
        """Test error for unrecognized flags."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--unknown-flag"])

    def test_missing_subcommand(self) -> None:
        """Test error when no subcommand is provided."""

        class MainArgs(KliamkaArgClass):
            pass

        class AddArgs(KliamkaArgClass):
            name: str = KliamkaArg("name", "Name", positional=True)

        @kliamka_subcommands(MainArgs, {"add": AddArgs}, argv=[])
        def test_func(args, command, cmd_args) -> None:
            pytest.fail("Decorator should exit before invoking the wrapped function")

        with pytest.raises(SystemExit) as exc_info:
            test_func()

        assert exc_info.value.code == 2

    def test_invalid_enum_value(self) -> None:
        """Test error for invalid enum value."""

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        class TestArgs(KliamkaArgClass):
            color: Color = KliamkaArg("--color", "Color", Color.RED)

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--color", "green"])

    def test_missing_flag_value(self) -> None:
        """Test error when flag expects value but none given."""

        class TestArgs(KliamkaArgClass):
            name: Optional[str] = KliamkaArg("--name", "Name")

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--name"])

    def test_extra_positional_args(self) -> None:
        """Test error for too many positional arguments."""

        class TestArgs(KliamkaArgClass):
            filename: str = KliamkaArg("filename", "Input file", positional=True)

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["file1.txt", "file2.txt"])

    def test_pydantic_validation_error_message(self) -> None:
        """Test that Pydantic validation errors contain useful info."""

        class TestArgs(KliamkaArgClass):
            port: Optional[int] = KliamkaArg("--port", "Port", default=80)

            @model_validator(mode="after")
            def check_port(self) -> "TestArgs":
                if self.port is not None and self.port < 1:
                    raise ValueError("Port must be positive")
                return self

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--port", "0"])

        with pytest.raises(KliamkaError, match=r"Port must be positive"):
            TestArgs.from_args(args)

    def test_bool_flag_rejects_value(self) -> None:
        """Test that bool flags don't accept values like --verbose=yes."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        parser = TestArgs.create_parser()

        # store_true doesn't accept =value syntax
        with pytest.raises(SystemExit):
            parser.parse_args(["--verbose=yes"])

    def test_kliamka_cli_renders_validation_errors_via_argparse(self, capsys) -> None:
        """Decorator should render model validation errors as CLI parse errors."""

        class TestArgs(KliamkaArgClass):
            port: Optional[int] = KliamkaArg("--port", "Port", default=80)

            @model_validator(mode="after")
            def check_port(self) -> "TestArgs":
                if self.port is not None and self.port < 1:
                    raise ValueError("Port must be positive")
                return self

        @kliamka_cli(TestArgs, argv=["--port", "0"])
        def test_func(args: TestArgs) -> None:
            pytest.fail("Decorator should exit before invoking the wrapped function")

        with pytest.raises(SystemExit) as exc_info:
            test_func()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "error: Port must be positive" in captured.err
        assert "Value error," not in captured.err

    def test_kliamka_subcommands_renders_validation_errors_via_argparse(
        self, capsys
    ) -> None:
        """Subcommand decorator renders model validation errors as parse errors."""

        class MainArgs(KliamkaArgClass):
            pass

        class AddArgs(KliamkaArgClass):
            port: Optional[int] = KliamkaArg("--port", "Port", default=80)

            @model_validator(mode="after")
            def check_port(self) -> "AddArgs":
                if self.port is not None and self.port < 1:
                    raise ValueError("Port must be positive")
                return self

        @kliamka_subcommands(MainArgs, {"add": AddArgs}, argv=["add", "--port", "0"])
        def test_func(args, command, cmd_args) -> None:
            pytest.fail("Decorator should exit before invoking the wrapped function")

        with pytest.raises(SystemExit) as exc_info:
            test_func()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "error: Port must be positive" in captured.err
        assert "Value error," not in captured.err


# ── #14: Programmatic argv ──────────────────────────────────────


class TestProgrammaticArgv:
    def test_custom_argv_in_decorator(self) -> None:
        """Test passing custom argv to kliamka_cli."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose", short="-v")
            name: Optional[str] = KliamkaArg("--name", "Name", default="world")

        result_holder = []

        @kliamka_cli(TestArgs, argv=["-v", "--name", "test"])
        def test_func(args: TestArgs) -> None:
            result_holder.append((args.verbose, args.name))

        test_func()
        assert result_holder[0] == (True, "test")

    def test_custom_argv_in_subcommands(self) -> None:
        """Test passing custom argv to kliamka_subcommands."""

        class MainArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose")

        class AddArgs(KliamkaArgClass):
            name: str = KliamkaArg("name", "Name", positional=True)

        result_holder = []

        @kliamka_subcommands(
            MainArgs,
            {"add": AddArgs},
            argv=["--verbose", "add", "item1"],
        )
        def test_func(args, command, cmd_args):
            result_holder.append((args.verbose, command, cmd_args.name))

        test_func()
        assert result_holder[0] == (True, "add", "item1")

    def test_empty_argv(self) -> None:
        """Test empty argv uses defaults."""

        class TestArgs(KliamkaArgClass):
            count: Optional[int] = KliamkaArg("--count", "Count", default=42)

        result_holder = []

        @kliamka_cli(TestArgs, argv=[])
        def test_func(args: TestArgs) -> None:
            result_holder.append(args.count)

        test_func()
        assert result_holder[0] == 42


# ── #15: Custom type converters ─────────────────────────────────


@pytest.fixture
def clean_converter_registry():
    """Snapshot/restore the global converter registry for test isolation."""
    from kliamka._converters import _CONVERTERS

    snapshot = dict(_CONVERTERS)
    try:
        yield
    finally:
        _CONVERTERS.clear()
        _CONVERTERS.update(snapshot)


class TestCustomConverters:
    def test_per_arg_converter_path(self, tmp_path) -> None:
        """Per-argument converter for pathlib.Path."""

        class TestArgs(KliamkaArgClass):
            target: Path = KliamkaArg(
                "--target",
                "Target path",
                converter=lambda s: Path(s).expanduser().resolve(),
            )

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--target", str(tmp_path)])
        instance = TestArgs.from_args(args)

        assert isinstance(instance.target, Path)
        assert instance.target == tmp_path.resolve()

    def test_registered_datetime_converter(self, clean_converter_registry) -> None:
        """Global registry converter for datetime.datetime."""
        register_converter(datetime, datetime.fromisoformat)

        class TestArgs(KliamkaArgClass):
            since: datetime = KliamkaArg("--since", "Start timestamp")

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--since", "2024-01-15T12:30:00"])
        instance = TestArgs.from_args(args)

        assert isinstance(instance.since, datetime)
        assert instance.since == datetime(2024, 1, 15, 12, 30, 0)

    def test_per_arg_overrides_registered(self, clean_converter_registry) -> None:
        """Explicit per-arg converter beats a registered global one."""
        register_converter(datetime, datetime.fromisoformat)

        class TestArgs(KliamkaArgClass):
            when: datetime = KliamkaArg(
                "--when",
                "Timestamp",
                converter=lambda s: datetime.strptime(s, "%Y/%m/%d"),
            )

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--when", "2024/01/15"])
        instance = TestArgs.from_args(args)

        assert instance.when == datetime(2024, 1, 15)

    def test_converter_via_env_var(self, monkeypatch, clean_converter_registry) -> None:
        """Registered converter applies to env var fallback."""
        register_converter(datetime, datetime.fromisoformat)
        monkeypatch.setenv("TS", "2024-06-01T08:00:00")

        class TestArgs(KliamkaArgClass):
            ts: Optional[datetime] = KliamkaArg("--ts", "Timestamp", env="TS")

        parser = TestArgs.create_parser()
        args = parser.parse_args([])
        instance = TestArgs.from_args(args)

        assert instance.ts == datetime(2024, 6, 1, 8, 0, 0)

    def test_converter_for_list_element(
        self, clean_converter_registry, tmp_path
    ) -> None:
        """Registered element converter applies to every item in List[T]."""
        register_converter(Path, Path)

        class TestArgs(KliamkaArgClass):
            files: List[Path] = KliamkaArg("--files", "Input files")

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--files", "a.txt", "b.txt"])
        instance = TestArgs.from_args(args)

        assert all(isinstance(p, Path) for p in instance.files)
        assert [p.name for p in instance.files] == ["a.txt", "b.txt"]

    def test_converter_error_becomes_argparse_error(self, capsys) -> None:
        """Bad input via converter should produce a clean argparse error."""

        def strict_port(s: str) -> int:
            n = int(s)
            if not (1 <= n <= 65535):
                raise ValueError(f"out of range: {n}")
            return n

        class TestArgs(KliamkaArgClass):
            port: int = KliamkaArg("--port", "Port", converter=strict_port)

        parser = TestArgs.create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--port", "99999"])
        assert exc_info.value.code == 2

        captured = capsys.readouterr()
        assert "invalid" in captured.err
        assert "99999" in captured.err
        assert "Traceback" not in captured.err

    def test_positional_with_converter(self, tmp_path) -> None:
        """Positional argument honors a per-arg converter."""

        class TestArgs(KliamkaArgClass):
            target: Path = KliamkaArg(
                "target",
                "Target path",
                positional=True,
                converter=lambda s: Path(s).resolve(),
            )

        parser = TestArgs.create_parser()
        args = parser.parse_args([str(tmp_path)])
        instance = TestArgs.from_args(args)

        assert isinstance(instance.target, Path)
        assert instance.target == tmp_path.resolve()

    @patch("sys.argv", ["test", "touch", "--path", "/tmp/foo"])
    def test_subcommand_with_converter(self) -> None:
        """Subcommand argument honors a per-arg converter."""

        class MainArgs(KliamkaArgClass):
            pass

        class TouchArgs(KliamkaArgClass):
            path: Path = KliamkaArg("--path", "Target", converter=lambda s: Path(s))

        result_holder = []

        @kliamka_subcommands(MainArgs, {"touch": TouchArgs})
        def run(args, command, cmd_args) -> None:
            result_holder.append((command, cmd_args.path))

        run()
        assert result_holder[0][0] == "touch"
        assert isinstance(result_holder[0][1], Path)
        assert result_holder[0][1] == Path("/tmp/foo")

    def test_unregister_reverts_behavior(self, clean_converter_registry) -> None:
        """unregister_converter makes behavior revert to annotation fallback."""
        sentinel_calls: list[str] = []

        def tagged(s: str) -> datetime:
            sentinel_calls.append(s)
            return datetime.fromisoformat(s)

        register_converter(datetime, tagged)

        class TestArgs(KliamkaArgClass):
            when: datetime = KliamkaArg("--when", "When")

        parser = TestArgs.create_parser()
        parser.parse_args(["--when", "2024-01-01T00:00:00"])
        assert len(sentinel_calls) == 1

        unregister_converter(datetime)

        # After unregister, no converter should be resolved; the fallback
        # becomes the raw annotation (datetime), which argparse calls
        # directly. datetime(str) is invalid, so argparse rejects it.
        parser2 = TestArgs.create_parser()
        with pytest.raises(SystemExit):
            parser2.parse_args(["--when", "2024-01-01T00:00:00"])
        # Tagged converter must not have been called the second time.
        assert len(sentinel_calls) == 1
