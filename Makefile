.PHONY: install init-dev run test lint format clean help

VENV := .venv/bin

# Default target
help:
	@echo "Available targets:"
	@echo "  install  - Install the package in development mode"
	@echo "  init-dev - Initialize development environment with uv"
	@echo "  run      - Run the CLI application"
	@echo "  test     - Run tests with pytest"
	@echo "  lint     - Run type checking and linting"
	@echo "  format   - Format code with ruff"
	@echo "  clean    - Clean build artifacts"
	@echo "  help     - Show this help message"

install:
	$(VENV)/pip install -e .
	$(VENV)/pip install pytest mypy ruff

run:
	$(VENV)/python -m src.kliamka

test:
	$(VENV)/pytest tests/ -v

lint:
	$(VENV)/mypy src/
	$(VENV)/ruff check src/ tests/
	$(VENV)/ruff format --check src/ tests/

format:
	$(VENV)/ruff format src/ tests/

init-dev:
	uv venv
	uv pip install -e .
	uv pip install pytest mypy ruff

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
