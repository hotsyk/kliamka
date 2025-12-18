"""Benchmark tests comparing kliamka with other CLI argument parsing libraries.

This module benchmarks:
- kliamka (this library)
- argparse (stdlib)
- click (popular CLI framework)
- typer (modern type-hinted CLI)

Run with: pytest benchmark/test_benchmark.py -v --benchmark-only
Or: pytest benchmark/test_benchmark.py -v --benchmark-compare
"""

import argparse
import sys
from enum import Enum
from pathlib import Path
from typing import List, Optional

import pytest

# Add src to path for kliamka imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kliamka import KliamkaArg, KliamkaArgClass

# Try to import optional dependencies
try:
    import click

    HAS_CLICK = True
except ImportError:
    HAS_CLICK = False

try:
    import typer

    HAS_TYPER = True
except ImportError:
    HAS_TYPER = False


# ============================================================================
# Common test data
# ============================================================================

SIMPLE_ARGS = ["--name", "test", "--count", "42", "--verbose"]
LIST_ARGS = ["--files", "a.txt", "b.txt", "c.txt", "--verbose"]
COMPLEX_ARGS = [
    "--name",
    "myapp",
    "--count",
    "100",
    "--verbose",
    "--tags",
    "dev",
    "test",
    "prod",
    "--port",
    "8080",
]


# ============================================================================
# Kliamka implementations
# ============================================================================


class KliamkaSimpleArgs(KliamkaArgClass):
    """Simple argument class for kliamka."""

    name: str = KliamkaArg("--name", "Name value", default="default")
    count: int = KliamkaArg("--count", "Count value", default=0)
    verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")


class KliamkaListArgs(KliamkaArgClass):
    """List argument class for kliamka."""

    files: List[str] = KliamkaArg("--files", "Input files")
    verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")


class KliamkaComplexArgs(KliamkaArgClass):
    """Complex argument class for kliamka."""

    name: str = KliamkaArg("--name", "Application name", default="app")
    count: int = KliamkaArg("--count", "Count value", default=0)
    verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")
    tags: List[str] = KliamkaArg("--tags", "Tags list")
    port: int = KliamkaArg("--port", "Port number", default=8000)


# ============================================================================
# Argparse implementations
# ============================================================================


def create_argparse_simple():
    """Create argparse parser for simple arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, default="default", help="Name value")
    parser.add_argument("--count", type=int, default=0, help="Count value")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def create_argparse_list():
    """Create argparse parser for list arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="*", default=[], help="Input files")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def create_argparse_complex():
    """Create argparse parser for complex arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, default="app", help="Application name")
    parser.add_argument("--count", type=int, default=0, help="Count value")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--tags", nargs="*", default=[], help="Tags list")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    return parser


# ============================================================================
# Click implementations (if available)
# ============================================================================

if HAS_CLICK:

    @click.command()
    @click.option("--name", default="default", help="Name value")
    @click.option("--count", default=0, type=int, help="Count value")
    @click.option("--verbose", is_flag=True, help="Verbose output")
    def click_simple(name, count, verbose):
        return {"name": name, "count": count, "verbose": verbose}

    @click.command()
    @click.option("--files", multiple=True, help="Input files")
    @click.option("--verbose", is_flag=True, help="Verbose output")
    def click_list(files, verbose):
        return {"files": list(files), "verbose": verbose}

    @click.command()
    @click.option("--name", default="app", help="Application name")
    @click.option("--count", default=0, type=int, help="Count value")
    @click.option("--verbose", is_flag=True, help="Verbose output")
    @click.option("--tags", multiple=True, help="Tags list")
    @click.option("--port", default=8000, type=int, help="Port number")
    def click_complex(name, count, verbose, tags, port):
        return {
            "name": name,
            "count": count,
            "verbose": verbose,
            "tags": list(tags),
            "port": port,
        }


# ============================================================================
# Typer implementations (if available)
# ============================================================================

if HAS_TYPER:
    typer_simple_app = typer.Typer()
    typer_list_app = typer.Typer()
    typer_complex_app = typer.Typer()

    @typer_simple_app.command()
    def typer_simple(
        name: str = typer.Option("default", help="Name value"),
        count: int = typer.Option(0, help="Count value"),
        verbose: bool = typer.Option(False, help="Verbose output"),
    ):
        return {"name": name, "count": count, "verbose": verbose}

    @typer_list_app.command()
    def typer_list(
        files: Optional[List[str]] = typer.Option(None, help="Input files"),
        verbose: bool = typer.Option(False, help="Verbose output"),
    ):
        return {"files": files or [], "verbose": verbose}

    @typer_complex_app.command()
    def typer_complex(
        name: str = typer.Option("app", help="Application name"),
        count: int = typer.Option(0, help="Count value"),
        verbose: bool = typer.Option(False, help="Verbose output"),
        tags: Optional[List[str]] = typer.Option(None, help="Tags list"),
        port: int = typer.Option(8000, help="Port number"),
    ):
        return {
            "name": name,
            "count": count,
            "verbose": verbose,
            "tags": tags or [],
            "port": port,
        }


# ============================================================================
# Benchmark Tests - Parser Creation
# ============================================================================


class TestParserCreation:
    """Benchmark parser/class creation time."""

    def test_kliamka_simple_creation(self, benchmark):
        """Benchmark kliamka simple parser creation."""
        benchmark(KliamkaSimpleArgs.create_parser)

    def test_argparse_simple_creation(self, benchmark):
        """Benchmark argparse simple parser creation."""
        benchmark(create_argparse_simple)

    @pytest.mark.skipif(not HAS_CLICK, reason="click not installed")
    def test_click_simple_creation(self, benchmark):
        """Benchmark click simple command creation."""

        @benchmark
        def create():
            @click.command()
            @click.option("--name", default="default")
            @click.option("--count", default=0, type=int)
            @click.option("--verbose", is_flag=True)
            def cmd(name, count, verbose):
                pass

            return cmd

    def test_kliamka_complex_creation(self, benchmark):
        """Benchmark kliamka complex parser creation."""
        benchmark(KliamkaComplexArgs.create_parser)

    def test_argparse_complex_creation(self, benchmark):
        """Benchmark argparse complex parser creation."""
        benchmark(create_argparse_complex)


# ============================================================================
# Benchmark Tests - Argument Parsing
# ============================================================================


class TestArgumentParsing:
    """Benchmark argument parsing time."""

    def test_kliamka_simple_parsing(self, benchmark):
        """Benchmark kliamka simple argument parsing."""
        parser = KliamkaSimpleArgs.create_parser()

        def parse():
            args = parser.parse_args(SIMPLE_ARGS)
            return KliamkaSimpleArgs.from_args(args)

        benchmark(parse)

    def test_argparse_simple_parsing(self, benchmark):
        """Benchmark argparse simple argument parsing."""
        parser = create_argparse_simple()
        benchmark(parser.parse_args, SIMPLE_ARGS)

    @pytest.mark.skipif(not HAS_CLICK, reason="click not installed")
    def test_click_simple_parsing(self, benchmark):
        """Benchmark click simple argument parsing."""
        from click.testing import CliRunner

        runner = CliRunner()

        def parse():
            return runner.invoke(click_simple, SIMPLE_ARGS)

        benchmark(parse)

    def test_kliamka_list_parsing(self, benchmark):
        """Benchmark kliamka list argument parsing."""
        parser = KliamkaListArgs.create_parser()

        def parse():
            args = parser.parse_args(LIST_ARGS)
            return KliamkaListArgs.from_args(args)

        benchmark(parse)

    def test_argparse_list_parsing(self, benchmark):
        """Benchmark argparse list argument parsing."""
        parser = create_argparse_list()
        benchmark(parser.parse_args, LIST_ARGS)

    @pytest.mark.skipif(not HAS_CLICK, reason="click not installed")
    def test_click_list_parsing(self, benchmark):
        """Benchmark click list argument parsing."""
        from click.testing import CliRunner

        runner = CliRunner()
        # Click uses multiple --files options
        click_list_args = ["--files", "a.txt", "--files", "b.txt", "--files", "c.txt", "--verbose"]

        def parse():
            return runner.invoke(click_list, click_list_args)

        benchmark(parse)

    def test_kliamka_complex_parsing(self, benchmark):
        """Benchmark kliamka complex argument parsing."""
        parser = KliamkaComplexArgs.create_parser()

        def parse():
            args = parser.parse_args(COMPLEX_ARGS)
            return KliamkaComplexArgs.from_args(args)

        benchmark(parse)

    def test_argparse_complex_parsing(self, benchmark):
        """Benchmark argparse complex argument parsing."""
        parser = create_argparse_complex()
        benchmark(parser.parse_args, COMPLEX_ARGS)

    @pytest.mark.skipif(not HAS_CLICK, reason="click not installed")
    def test_click_complex_parsing(self, benchmark):
        """Benchmark click complex argument parsing."""
        from click.testing import CliRunner

        runner = CliRunner()
        click_complex_args = [
            "--name",
            "myapp",
            "--count",
            "100",
            "--verbose",
            "--tags",
            "dev",
            "--tags",
            "test",
            "--tags",
            "prod",
            "--port",
            "8080",
        ]

        def parse():
            return runner.invoke(click_complex, click_complex_args)

        benchmark(parse)

    @pytest.mark.skipif(not HAS_TYPER, reason="typer not installed")
    def test_typer_simple_parsing(self, benchmark):
        """Benchmark typer simple argument parsing."""
        from typer.testing import CliRunner

        runner = CliRunner()

        def parse():
            return runner.invoke(typer_simple_app, SIMPLE_ARGS)

        benchmark(parse)

    @pytest.mark.skipif(not HAS_TYPER, reason="typer not installed")
    def test_typer_list_parsing(self, benchmark):
        """Benchmark typer list argument parsing."""
        from typer.testing import CliRunner

        runner = CliRunner()
        typer_list_args = ["--files", "a.txt", "--files", "b.txt", "--files", "c.txt", "--verbose"]

        def parse():
            return runner.invoke(typer_list_app, typer_list_args)

        benchmark(parse)

    @pytest.mark.skipif(not HAS_TYPER, reason="typer not installed")
    def test_typer_complex_parsing(self, benchmark):
        """Benchmark typer complex argument parsing."""
        from typer.testing import CliRunner

        runner = CliRunner()
        typer_complex_args = [
            "--name",
            "myapp",
            "--count",
            "100",
            "--verbose",
            "--tags",
            "dev",
            "--tags",
            "test",
            "--tags",
            "prod",
            "--port",
            "8080",
        ]

        def parse():
            return runner.invoke(typer_complex_app, typer_complex_args)

        benchmark(parse)


# ============================================================================
# Benchmark Tests - Full Workflow (Creation + Parsing)
# ============================================================================


class TestFullWorkflow:
    """Benchmark complete workflow: parser creation + parsing."""

    def test_kliamka_full_simple(self, benchmark):
        """Benchmark kliamka full simple workflow."""

        def workflow():
            parser = KliamkaSimpleArgs.create_parser()
            args = parser.parse_args(SIMPLE_ARGS)
            return KliamkaSimpleArgs.from_args(args)

        benchmark(workflow)

    def test_argparse_full_simple(self, benchmark):
        """Benchmark argparse full simple workflow."""

        def workflow():
            parser = create_argparse_simple()
            return parser.parse_args(SIMPLE_ARGS)

        benchmark(workflow)

    def test_kliamka_full_complex(self, benchmark):
        """Benchmark kliamka full complex workflow."""

        def workflow():
            parser = KliamkaComplexArgs.create_parser()
            args = parser.parse_args(COMPLEX_ARGS)
            return KliamkaComplexArgs.from_args(args)

        benchmark(workflow)

    def test_argparse_full_complex(self, benchmark):
        """Benchmark argparse full complex workflow."""

        def workflow():
            parser = create_argparse_complex()
            return parser.parse_args(COMPLEX_ARGS)

        benchmark(workflow)

    @pytest.mark.skipif(not HAS_CLICK, reason="click not installed")
    def test_click_full_simple(self, benchmark):
        """Benchmark click full simple workflow."""
        from click.testing import CliRunner

        runner = CliRunner()

        def workflow():
            @click.command()
            @click.option("--name", default="default")
            @click.option("--count", default=0, type=int)
            @click.option("--verbose", is_flag=True)
            def cmd(name, count, verbose):
                return {"name": name, "count": count, "verbose": verbose}

            return runner.invoke(cmd, SIMPLE_ARGS)

        benchmark(workflow)


# ============================================================================
# Benchmark Tests - Memory Usage (requires memory_profiler)
# ============================================================================


class TestMemoryFootprint:
    """Test memory footprint of different approaches."""

    def test_kliamka_class_size(self):
        """Check kliamka class instance size."""
        import sys

        parser = KliamkaComplexArgs.create_parser()
        args = parser.parse_args(COMPLEX_ARGS)
        instance = KliamkaComplexArgs.from_args(args)

        # Basic size check (not comprehensive but indicative)
        size = sys.getsizeof(instance)
        print(f"\nKliamka instance size: {size} bytes")
        assert size > 0

    def test_argparse_namespace_size(self):
        """Check argparse namespace size."""
        import sys

        parser = create_argparse_complex()
        args = parser.parse_args(COMPLEX_ARGS)

        size = sys.getsizeof(args)
        print(f"\nArgparse namespace size: {size} bytes")
        assert size > 0


# ============================================================================
# Validation Benchmarks
# ============================================================================


class TestValidation:
    """Benchmark validation overhead (kliamka uses Pydantic)."""

    def test_kliamka_validation(self, benchmark):
        """Benchmark kliamka with Pydantic validation."""
        parser = KliamkaComplexArgs.create_parser()
        args = parser.parse_args(COMPLEX_ARGS)

        benchmark(KliamkaComplexArgs.from_args, args)

    def test_argparse_no_validation(self, benchmark):
        """Benchmark argparse without validation (baseline)."""
        parser = create_argparse_complex()
        parsed = parser.parse_args(COMPLEX_ARGS)

        def access_values():
            return {
                "name": parsed.name,
                "count": parsed.count,
                "verbose": parsed.verbose,
                "tags": parsed.tags,
                "port": parsed.port,
            }

        benchmark(access_values)


# ============================================================================
# Repeated Parsing Benchmarks
# ============================================================================


class TestRepeatedParsing:
    """Benchmark repeated parsing (simulating CLI tool invocations)."""

    def test_kliamka_repeated_100(self, benchmark):
        """Benchmark kliamka 100 repeated parsings."""
        parser = KliamkaSimpleArgs.create_parser()

        def parse_100():
            for _ in range(100):
                args = parser.parse_args(SIMPLE_ARGS)
                KliamkaSimpleArgs.from_args(args)

        benchmark(parse_100)

    def test_argparse_repeated_100(self, benchmark):
        """Benchmark argparse 100 repeated parsings."""
        parser = create_argparse_simple()

        def parse_100():
            for _ in range(100):
                parser.parse_args(SIMPLE_ARGS)

        benchmark(parse_100)
