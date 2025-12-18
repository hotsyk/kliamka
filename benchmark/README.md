# Kliamka Benchmarks

Benchmark tests comparing kliamka with other CLI argument parsing libraries.

## Libraries Compared

- **kliamka** - This library (Pydantic-based)
- **argparse** - Python standard library
- **click** - Popular CLI framework (optional)
- **typer** - Modern type-hinted CLI built on click (optional)

## Requirements

```bash
# Required
pip install pytest pytest-benchmark

# Optional (for comparison)
pip install click typer
```

## Running Benchmarks

### Basic benchmark run
```bash
pytest benchmark/test_benchmark.py -v
```

### Benchmark only (skip non-benchmark tests)
```bash
pytest benchmark/test_benchmark.py -v --benchmark-only
```

### Compare results
```bash
pytest benchmark/test_benchmark.py -v --benchmark-compare
```

### Save benchmark results
```bash
pytest benchmark/test_benchmark.py -v --benchmark-autosave
```

### Generate JSON output
```bash
pytest benchmark/test_benchmark.py -v --benchmark-json=benchmark_results.json
```

### Detailed statistics
```bash
pytest benchmark/test_benchmark.py -v --benchmark-columns=min,max,mean,stddev,median,ops
```

## Benchmark Categories

### Parser Creation
Tests the time to create a parser/command definition.

### Argument Parsing
Tests the time to parse command-line arguments.

### Full Workflow
Tests the complete workflow: parser creation + argument parsing.

### Validation
Compares kliamka's Pydantic validation overhead against raw argparse.

### Repeated Parsing
Simulates real-world usage with multiple parse operations.

## Expected Results

Kliamka has a small overhead compared to raw argparse due to:
1. Pydantic model validation
2. Type-safe instance creation

However, it provides:
1. Type safety at runtime
2. Better IDE support
3. Automatic validation
4. Cleaner API

## Sample Output

```
benchmark/test_benchmark.py::TestArgumentParsing::test_kliamka_simple_parsing PASSED
benchmark/test_benchmark.py::TestArgumentParsing::test_argparse_simple_parsing PASSED

------------------------ benchmark: 2 tests ------------------------
Name                                     Mean          StdDev
---------------------------------------------------------------------
test_argparse_simple_parsing          15.2 us        0.8 us
test_kliamka_simple_parsing           45.3 us        2.1 us
---------------------------------------------------------------------
```
