#!/bin/bash
set -euo pipefail

python -m compileall -q src/kliamka
pytest benchmark/test_benchmark.py -v --benchmark-compare --benchmark-json=benchmark_results.json

python - <<'PY'
import json
from math import prod
from pathlib import Path


def geometric_mean(values: list[float]) -> float:
    return prod(values) ** (1.0 / len(values))


data = json.loads(Path("benchmark_results.json").read_text())
medians_us = {
    item["name"].removeprefix("test_"): item["stats"]["median"] * 1_000_000
    for item in data["benchmarks"]
}

kliamka_names = sorted(name for name in medians_us if name.startswith("kliamka_"))
expected_count = 9
if len(kliamka_names) != expected_count:
    raise SystemExit(
        f"expected {expected_count} Kliamka benchmarks, found {len(kliamka_names)}: "
        f"{kliamka_names}"
    )


def group_metric(fragment: str) -> float:
    values = [
        value
        for name, value in medians_us.items()
        if name.startswith("kliamka_") and fragment in name
    ]
    if not values:
        raise SystemExit(f"no Kliamka benchmarks matched {fragment!r}")
    return geometric_mean(values)


def matched_ratio(competitor: str, operations: tuple[str, ...]) -> float:
    ratios = []
    for operation in operations:
        ratios.append(
            medians_us[f"kliamka_{operation}"]
            / medians_us[f"{competitor}_{operation}"]
        )
    return geometric_mean(ratios)


creation_ops = ("simple_creation", "complex_creation")
parsing_ops = ("simple_parsing", "list_parsing", "complex_parsing")
argparse_ops = creation_ops + parsing_ops + (
    "full_simple",
    "full_complex",
    "repeated_100",
)

metrics = {
    "kliamka_geomean_us": geometric_mean(
        [medians_us[name] for name in kliamka_names]
    ),
    "creation_geomean_us": geometric_mean(
        [medians_us[f"kliamka_{operation}"] for operation in creation_ops]
    ),
    "parsing_geomean_us": geometric_mean(
        [medians_us[f"kliamka_{operation}"] for operation in parsing_ops]
    ),
    "full_geomean_us": geometric_mean(
        [medians_us["kliamka_full_simple"], medians_us["kliamka_full_complex"]]
    ),
    "validation_us": medians_us["kliamka_validation"],
    "repeated_100_us": medians_us["kliamka_repeated_100"],
    "vs_argparse_ratio": matched_ratio("argparse", argparse_ops),
    "vs_click_parsing_ratio": matched_ratio("click", parsing_ops),
    "vs_typer_parsing_ratio": matched_ratio("typer", parsing_ops),
}

for name, value in metrics.items():
    print(f"METRIC {name}={value:.9f}")
PY
