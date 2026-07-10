"""Tests for the opt-in cross-library benchmark table."""

import pytest

from benchmark.comparison import (
    LibraryBenchmarkResult,
    format_duration,
    render_comparison_table,
)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (2.0, "2.00 s"),
        (0.002, "2.00 ms"),
        (0.000002, "2.00 µs"),
        (0.000000002, "2.00 ns"),
    ],
)
def test_format_duration_uses_readable_units(seconds: float, expected: str) -> None:
    assert format_duration(seconds) == expected


def test_render_comparison_table_pivots_libraries_and_shows_ratios() -> None:
    lines = render_comparison_table(
        [
            LibraryBenchmarkResult("parsing_simple", "argparse", 10e-6),
            LibraryBenchmarkResult("parsing_simple", "kliamka", 5e-6),
            LibraryBenchmarkResult("parsing_simple", "click", 25e-6),
        ]
    )
    output = "\n".join(lines)

    assert "Workload" in output
    assert "argparse" in output
    assert "kliamka" in output
    assert "click" in output
    assert "typer" in output
    assert "Parsing · simple" in output
    assert "5.00 µs (0.50×)" in output
    assert "25.00 µs (2.50×)" in output
    assert "—" in output
    assert "Ratios are relative to the argparse median" in output


def test_render_comparison_table_uses_stable_workload_order() -> None:
    lines = render_comparison_table(
        [
            LibraryBenchmarkResult("validation", "kliamka", 1e-6),
            LibraryBenchmarkResult("creation_simple", "kliamka", 2e-6),
        ]
    )
    output = "\n".join(lines)

    assert output.index("Creation · simple") < output.index("Validation")


def test_render_comparison_table_handles_unknown_workloads() -> None:
    lines = render_comparison_table(
        [LibraryBenchmarkResult("custom_case", "kliamka", 3e-6)]
    )

    assert "Custom Case" in "\n".join(lines)
