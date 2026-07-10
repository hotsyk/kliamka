"""Formatting helpers for the opt-in benchmark library comparison table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

LIBRARIES = ("argparse", "kliamka", "click", "typer")
WORKLOADS = (
    ("creation_simple", "Creation · simple"),
    ("creation_complex", "Creation · complex"),
    ("parsing_simple", "Parsing · simple"),
    ("parsing_list", "Parsing · list"),
    ("parsing_complex", "Parsing · complex"),
    ("full_simple", "Full workflow · simple"),
    ("full_complex", "Full workflow · complex"),
    ("validation", "Validation"),
    ("repeated_100", "Repeated parsing · 100"),
)
_MISSING_VALUE = "—"


@dataclass(frozen=True)
class LibraryBenchmarkResult:
    """One library's median runtime for a comparable workload."""

    workload: str
    library: str
    median_seconds: float


def format_duration(seconds: float) -> str:
    """Format seconds using a readable benchmark time unit."""
    if seconds >= 1:
        return f"{seconds:.2f} s"
    if seconds >= 1e-3:
        return f"{seconds * 1e3:.2f} ms"
    if seconds >= 1e-6:
        return f"{seconds * 1e6:.2f} µs"
    return f"{seconds * 1e9:.2f} ns"


def render_comparison_table(results: Iterable[LibraryBenchmarkResult]) -> list[str]:
    """Render workload rows with one result column per library."""
    matrix: dict[str, dict[str, float]] = {}
    for result in results:
        matrix.setdefault(result.workload, {})[result.library] = result.median_seconds

    headers = ("Workload", *LIBRARIES)
    rows: list[tuple[str, ...]] = []
    known_workloads = {workload for workload, _label in WORKLOADS}
    ordered_workloads = [
        (workload, label) for workload, label in WORKLOADS if workload in matrix
    ]
    ordered_workloads.extend(
        (workload, workload.replace("_", " ").title())
        for workload in sorted(matrix)
        if workload not in known_workloads
    )

    for workload, label in ordered_workloads:
        timings = matrix[workload]
        baseline = timings.get("argparse")
        cells = [label]
        for library in LIBRARIES:
            timing = timings.get(library)
            if timing is None:
                cells.append(_MISSING_VALUE)
                continue
            cell = format_duration(timing)
            if library != "argparse" and baseline:
                cell += f" ({timing / baseline:.2f}×)"
            cells.append(cell)
        rows.append(tuple(cells))

    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def format_row(row: tuple[str, ...]) -> str:
        return " | ".join(
            cell.ljust(widths[index]) if index == 0 else cell.rjust(widths[index])
            for index, cell in enumerate(row)
        )

    separator = "-+-".join("-" * width for width in widths)
    lines = [format_row(headers), separator]
    lines.extend(format_row(row) for row in rows)
    lines.append("Ratios are relative to the argparse median; — means unavailable.")
    return lines
