"""Tests for kliamka module."""

import argparse
import pytest
import sys
from enum import Enum
from pathlib import Path
from typing import List, Optional
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kliamka import (
    KliamkaError,
    __version__,
    KliamkaArg,
    KliamkaArgClass,
    kliamka_cli,
    kliamka_subcommands,
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
        assert __version__ == "0.2.0"

    def test_all_exports(self) -> None:
        expected_exports = {
            "KliamkaError",
            "KliamkaArg",
            "KliamkaArgClass",
            "kliamka_cli",
            "__version__",
            "__author__",
            "__email__",
        }

        import kliamka

        actual_exports = {
            name
            for name in dir(kliamka)
            if not name.startswith("_") or name.startswith("__")
        }

        assert expected_exports.issubset(actual_exports)


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
