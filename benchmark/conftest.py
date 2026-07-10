"""Pytest integration for opt-in cross-library benchmark reporting."""

from __future__ import annotations

from typing import Any

import pytest

from benchmark.comparison import LibraryBenchmarkResult, render_comparison_table

_COMPARISON_METADATA: pytest.StashKey[dict[str, tuple[str, str]]] = pytest.StashKey()


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the opt-in library comparison table."""
    group = parser.getgroup("benchmark")
    group.addoption(
        "--benchmark-compare-libraries",
        action="store_true",
        help=(
            "show benchmark workloads as rows with argparse, kliamka, click, "
            "and typer median columns"
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register comparison metadata and initialize per-run storage."""
    config.addinivalue_line(
        "markers",
        "library_benchmark(workload, library): identify equivalent library benchmarks",
    )
    config.stash[_COMPARISON_METADATA] = {}


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Collect comparison metadata without altering pytest-benchmark grouping."""
    metadata = config.stash[_COMPARISON_METADATA]
    for item in items:
        marker = item.get_closest_marker("library_benchmark")
        if marker is None:
            continue
        workload = marker.kwargs.get("workload")
        library = marker.kwargs.get("library")
        if isinstance(workload, str) and isinstance(library, str):
            metadata[item.nodeid] = (workload, library)


@pytest.hookimpl(trylast=True)
def pytest_terminal_summary(terminalreporter: Any) -> None:
    """Print the optional median comparison after pytest-benchmark's report."""
    config = terminalreporter.config
    if not config.getoption("benchmark_compare_libraries"):
        return

    metadata = config.stash[_COMPARISON_METADATA]
    benchmark_session = getattr(config, "_benchmarksession", None)
    results: list[LibraryBenchmarkResult] = []
    for benchmark in getattr(benchmark_session, "benchmarks", ()):
        identity = metadata.get(benchmark.fullname)
        if identity is None or benchmark.has_error:
            continue
        stats = benchmark.as_dict(include_data=False).get("stats", {})
        median = stats.get("median")
        if not isinstance(median, (int, float)):
            continue
        workload, library = identity
        results.append(LibraryBenchmarkResult(workload, library, float(median)))

    terminalreporter.section("benchmark library comparison", sep="-")
    if not results:
        terminalreporter.write_line("No comparable benchmark results were collected.")
        return
    for line in render_comparison_table(results):
        terminalreporter.write_line(line)
