"""Tests for kliamka module."""

import argparse
import pytest
import sys
from enum import Enum
from pathlib import Path
from typing import Optional
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kliamka import (
    KliamkaError,
    __version__,
    KliamkaArg,
    KliamkaArgClass,
    kliamka_cli,
)


class TestKliamkaError:
    """Test cases for KliamkaError exception."""

    def test_kliamka_error_inheritance(self) -> None:
        """Test that KliamkaError inherits from Exception."""
        assert issubclass(KliamkaError, Exception)

    def test_kliamka_error_raise(self) -> None:
        """Test raising KliamkaError."""
        with pytest.raises(KliamkaError):
            raise KliamkaError("Test error")


class TestKliamkaArg:
    """Test cases for KliamkaArg descriptor."""

    def test_kliamka_arg_creation(self) -> None:
        """Test KliamkaArg initialization."""
        arg = KliamkaArg("--verbose", "Enable verbose output", False)
        assert arg.flag == "--verbose"
        assert arg.help_text == "Enable verbose output"
        assert arg.default is False

    def test_kliamka_arg_set_name(self) -> None:
        """Test KliamkaArg name setting."""
        arg = KliamkaArg("--debug")
        arg.__set_name__(type, "debug")
        assert arg.name == "debug"


class TestKliamkaArgClass:
    """Test cases for KliamkaArgClass."""

    def test_create_parser_boolean(self) -> None:
        """Test parser creation for boolean arguments."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Enable verbose output")

        parser = TestArgs.create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

        args = parser.parse_args([])
        assert args.verbose is False

    def test_create_parser_string(self) -> None:
        """Test parser creation for string arguments."""

        class TestArgs(KliamkaArgClass):
            name: Optional[str] = KliamkaArg("--name", "Your name", "default")

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--name", "Alice"])
        assert args.name == "Alice"

        args = parser.parse_args([])
        assert args.name == "default"

    def test_from_args(self) -> None:
        """Test creating instance from parsed arguments."""

        class TestArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Enable verbose")
            count: Optional[int] = KliamkaArg("--count", "Count", 1)

        parser = TestArgs.create_parser()
        args = parser.parse_args(["--verbose", "--count", "5"])
        instance = TestArgs.from_args(args)

        assert instance.verbose is True
        assert instance.count == 5


class TestKliamkaDecorators:
    """Test cases for kliamka decorators."""

    def test_kliamka_cli_decorator(self) -> None:
        """Test kliamka_cli decorator functionality."""

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
        """Test kliamka_cli decorator execution with mocked args."""

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
        assert __version__ == "0.1.0"

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

        # Test with valid enum value
        args = parser.parse_args(["--log-level", "debug"])
        instance = TestArgs.from_args(args)
        assert instance.log_level == LogLevel.DEBUG

        # Test with default value
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
        """Test multiple enum arguments in same class."""

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
