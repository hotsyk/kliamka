#!/usr/bin/env python
"""Generate a comparison table of benchmark results.

Usage:
    # First run benchmarks with JSON output
    pytest benchmark/test_benchmark.py --benchmark-json=results.json

    # Then generate comparison table
    python benchmark/compare_results.py results.json
"""

import json
import sys
from collections import defaultdict


def parse_test_name(name):
    """Parse test name to extract library and operation.

    Example: test_kliamka_simple_parsing -> ('kliamka', 'simple_parsing')
    """
    # Remove 'test_' prefix
    name = name.replace("test_", "")

    # Known libraries
    libraries = ["kliamka", "argparse", "click", "typer"]

    for lib in libraries:
        if name.startswith(lib + "_"):
            operation = name[len(lib) + 1:]
            return lib, operation

    return "unknown", name


def format_time(nanoseconds):
    """Format time in appropriate units."""
    if nanoseconds >= 1_000_000:
        return f"{nanoseconds / 1_000_000:.2f} ms"
    elif nanoseconds >= 1_000:
        return f"{nanoseconds / 1_000:.2f} μs"
    else:
        return f"{nanoseconds:.2f} ns"


def generate_comparison_table(json_file):
    """Generate comparison table from benchmark JSON results."""
    with open(json_file) as f:
        data = json.load(f)

    # Group results by operation
    results = defaultdict(dict)

    for benchmark in data.get("benchmarks", []):
        name = benchmark["name"].split("::")[-1]  # Get just the test name
        lib, operation = parse_test_name(name)
        mean_ns = benchmark["stats"]["mean"] * 1e9  # Convert to nanoseconds
        results[operation][lib] = mean_ns

    # Define library order
    libraries = ["argparse", "kliamka", "click", "typer"]

    # Print header
    header = f"{'Operation':<30}"
    for lib in libraries:
        header += f" {lib:>15}"
    print(header)
    print("-" * len(header))

    # Print rows
    for operation in sorted(results.keys()):
        row = f"{operation:<30}"
        baseline = results[operation].get("argparse")

        for lib in libraries:
            if lib in results[operation]:
                time_ns = results[operation][lib]
                time_str = format_time(time_ns)

                # Add relative comparison to argparse
                if baseline and lib != "argparse":
                    ratio = time_ns / baseline
                    row += f" {time_str:>10} ({ratio:.1f}x)"
                else:
                    row += f" {time_str:>15}"
            else:
                row += f" {'N/A':>15}"
        print(row)

    print()
    print("Note: Values in parentheses show overhead relative to argparse (baseline)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_results.py <results.json>")
        print()
        print("First run benchmarks with JSON output:")
        print("  pytest benchmark/test_benchmark.py --benchmark-json=results.json")
        sys.exit(1)

    generate_comparison_table(sys.argv[1])


if __name__ == "__main__":
    main()
