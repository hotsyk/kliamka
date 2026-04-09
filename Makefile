.PHONY: install init-dev run test test-package test-all test-docker test-docker-all lint format clean help

VENV := .venv/bin
PYTHON := $(VENV)/python
PYTEST := $(VENV)/pytest

# Default target
help:
	@echo "Available targets:"
	@echo "  install  - Install the package in development mode"
	@echo "  init-dev - Initialize development environment with uv"
	@echo "  run      - Run the CLI application"
	@echo "  test         - Run unit tests with pytest"
	@echo "  test-package - Build wheel/sdist and smoke-install both artifacts"
	@echo "  test-all     - Run unit and packaging smoke tests"
	@echo "  test-docker VERSION=3.11 - Run tests in Docker for a specific Python version"
	@echo "  test-docker-all - Run Docker test matrix for Python 3.11-3.14"
	@echo "  lint     - Run type checking and linting"
	@echo "  format   - Format code with ruff"
	@echo "  clean    - Clean build artifacts"
	@echo "  help     - Show this help message"

install:
	$(PYTHON) -m pip install -e .
	$(PYTHON) -m pip install pytest mypy ruff

run:
	$(PYTHON) -c "import kliamka; print('kliamka', kliamka.__version__)"

test:
	$(PYTEST) tests/ -v -m "not packaging"

test-package:
	$(PYTEST) tests/test_packaging_smoke.py -v -m packaging

test-all:
	$(PYTEST) tests/ -v

test-docker:
	docker build --build-arg PYTHON_VERSION=$(VERSION) -f Dockerfile.test -t kliamka-test:$(VERSION) .
	docker run --rm kliamka-test:$(VERSION)

test-docker-all:
	@for version in 3.11 3.12 3.13 3.14; do \
		echo "==> Running Docker tests for Python $$version"; \
		$(MAKE) test-docker VERSION=$$version || exit $$?; \
	done

lint:
	$(PYTHON) -m mypy src/
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m ruff format --check src/ tests/

format:
	$(PYTHON) -m ruff format src/ tests/

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
