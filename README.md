[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner2-direct.svg)](https://stand-with-ukraine.pp.ua)

# Kliamka

A small Python CLI library that provides Pydantic-based argument parser with type safety.

![PyPI - Version](https://img.shields.io/pypi/v/kliamka)

## Features

- **Type-safe CLI arguments** with Pydantic validation
- **Decorator-based design** for clean, readable code
- **Automatic argument parsing** from class definitions
- **Modern Python 3.11+** with full type hints

## Installation

```bash
# Install via pip
pip install kliamka

# Install from source
git clone https://github.com/hotsyk/kliamka.git
cd kliamka
make install

# Or install in development mode
pip install -e .
```

## Quick Start

```python
from kliamka import KliamkaArg, KliamkaArgClass, kliamka_cli

class MyArgs(KliamkaArgClass):
    """My CLI application arguments."""
    verbose: bool | None = KliamkaArg("--verbose", "Enable verbose output")
    count: int | None = KliamkaArg("--count", "Number of iterations", default=1)

@kliamka_cli(MyArgs)
def main(args: MyArgs) -> None:
    """Main application logic."""
    if args.verbose:
        print("Verbose mode enabled")

    for i in range(args.count or 1):
        print(f"Iteration {i + 1}")

if __name__ == "__main__":
    main()
```

Run your CLI:
```bash
python my_app.py --verbose --count 3
```

## API Reference

### Core Components

#### `KliamkaArg`
Descriptor for defining CLI arguments with automatic type inference.

```python
class KliamkaArg:
    def __init__(self, flag: str, help_text: str = "", default: Any = None)
```

#### `KliamkaArgClass`
Base class for CLI argument definitions using Pydantic models.

```python
class MyArgs(KliamkaArgClass):
    debug: bool | None = KliamkaArg("--debug", "Enable debug mode")
    config: str | None = KliamkaArg("--config", "Configuration file path")
```

#### `@kliamka_cli`
Decorator that automatically parses CLI arguments and injects them as the first parameter.

```python
@kliamka_cli(MyArgs)
def main(args: MyArgs) -> None:
    # args is automatically populated from command line
    pass
```

## Examples

See the [examples/](examples/) directory for more comprehensive usage examples:

- `examples/basic_usage.py` - Basic CLI argument handling
- `examples/enums.py` - Handling of enumerated types

## Development

### Requirements

- Python 3.11+
- Pydantic 2.0+

### Setup

```bash
# Clone and setup
git clone https://github.com/hotsyk/kliamka.git
cd kliamka
make install

# Run tests
make test

# Lint and type check
make lint

# Run example
python examples/basic_usage.py --help
```

### Versions
See [VERSIONS.md](VERSIONS.md) for detailed version history and changelog.

### Available Make Commands

- `make install` - Install package in development mode
- `make run` - Run the CLI application
- `make test` - Run tests with pytest
- `make lint` - Run type checking and linting
- `make format` - Format code with ruff
- `make clean` - Clean build artifacts

## Documentation

- [Examples](examples/) - Usage examples and demos

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `make lint` and `make test`
5. Submit a pull request

## License

[MIT-NORUS](LICENSE) License - see LICENSE file for details.

## Author

Volodymyr Hotsyk - [https://github.com/hotsyk](https://github.com/hotsyk)
