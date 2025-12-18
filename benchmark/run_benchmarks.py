#!/usr/bin/env python
"""Run benchmark tests and generate a summary report.

Usage:
    python benchmark/run_benchmarks.py [--install-deps] [--with-click] [--with-typer]
    python benchmark/run_benchmarks.py --table  # Generate comparison table
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict


def check_pytest_benchmark_installed():
    """Check if pytest-benchmark is installed."""
    try:
        import pytest_benchmark  # noqa: F401

        return True
    except ImportError:
        return False


def install_dependencies(with_click=False, with_typer=False):
    """Install benchmark dependencies."""
    deps = ["pytest", "pytest-benchmark"]

    if with_click:
        deps.append("click")
    if with_typer:
        deps.append("typer")

    print(f"Installing dependencies: {', '.join(deps)}")
    subprocess.run([sys.executable, "-m", "pip", "install"] + deps, check=True)


def format_time(nanoseconds):
    """Format time in appropriate units."""
    if nanoseconds >= 1_000_000:
        return f"{nanoseconds / 1_000_000:.2f} ms"
    elif nanoseconds >= 1_000:
        return f"{nanoseconds / 1_000:.2f} μs"
    else:
        return f"{nanoseconds:.2f} ns"


def parse_test_name(name):
    """Parse test name to extract library and operation."""
    name = name.replace("test_", "")
    libraries = ["kliamka", "argparse", "click", "typer"]

    for lib in libraries:
        if name.startswith(lib + "_"):
            operation = name[len(lib) + 1:]
            return lib, operation

    return "unknown", name


def generate_comparison_table(json_file):
    """Generate comparison table from benchmark JSON results in markdown format."""
    with open(json_file) as f:
        data = json.load(f)

    results = defaultdict(dict)

    for benchmark in data.get("benchmarks", []):
        name = benchmark["name"].split("::")[-1]
        lib, operation = parse_test_name(name)
        mean_ns = benchmark["stats"]["mean"] * 1e9
        results[operation][lib] = mean_ns

    libraries = ["argparse", "kliamka", "click", "typer"]

    # Print markdown header
    print()
    print("## Benchmark Comparison Table")
    print()
    print("| Operation | argparse | kliamka | click | typer |")
    print("|-----------|----------|---------|-------|-------|")

    for operation in sorted(results.keys()):
        row = f"| {operation} |"
        baseline = results[operation].get("argparse")

        for lib in libraries:
            if lib in results[operation]:
                time_ns = results[operation][lib]
                time_str = format_time(time_ns)

                if baseline and lib != "argparse":
                    ratio = time_ns / baseline
                    row += f" {time_str} ({ratio:.1f}x) |"
                else:
                    row += f" {time_str} |"
            else:
                row += " - |"
        print(row)

    print()
    print("*Note: (Nx) = overhead relative to argparse baseline*")
    print()


def run_benchmarks(save=False, compare=False, json_output=None, table=False):
    """Run the benchmark tests."""
    # Check if pytest-benchmark is installed
    if not check_pytest_benchmark_installed():
        print("pytest-benchmark not installed. Installing...")
        install_dependencies()
        print()

    # If table mode, use temp file for JSON
    if table and not json_output:
        json_output = tempfile.mktemp(suffix=".json")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "benchmark/test_benchmark.py",
        "-v",
        "--benchmark-columns=min,max,mean,stddev,median,ops",
        "--benchmark-sort=mean",
    ]

    if save:
        cmd.append("--benchmark-autosave")
    if compare:
        cmd.append("--benchmark-compare")
    if json_output:
        cmd.append(f"--benchmark-json={json_output}")

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    # Generate table if requested
    if table and json_output and os.path.exists(json_output):
        generate_comparison_table(json_output)
        if table and not save:
            os.unlink(json_output)  # Clean up temp file


def main():
    parser = argparse.ArgumentParser(description="Run kliamka benchmarks")
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install benchmark dependencies",
    )
    parser.add_argument(
        "--with-click",
        action="store_true",
        help="Include click library for comparison",
    )
    parser.add_argument(
        "--with-typer",
        action="store_true",
        help="Include typer library for comparison",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save benchmark results",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare with previous results",
    )
    parser.add_argument(
        "--json",
        type=str,
        metavar="FILE",
        help="Output results to JSON file",
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help="Generate comparison table (kliamka vs argparse vs click vs typer)",
    )

    args = parser.parse_args()

    if args.install_deps:
        install_dependencies(with_click=args.with_click, with_typer=args.with_typer)

    run_benchmarks(save=args.save, compare=args.compare, json_output=args.json, table=args.table)


if __name__ == "__main__":
    main()
