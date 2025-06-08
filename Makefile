.PHONY: install run test lint clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  install  - Install the package in development mode"
	@echo "  run      - Run the CLI application"
	@echo "  test     - Run tests with pytest"
	@echo "  lint     - Run type checking and linting"
	@echo "  clean    - Clean build artifacts"
	@echo "  help     - Show this help message"

install:
	pip install -e .
	pip install pytest mypy ruff

run:
	python -m src.kliamka

test:
	pytest tests/ -v

lint:
	mypy src/
	ruff check src/ tests/
	ruff format --check src/ tests/


format:
	ruff format src/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
