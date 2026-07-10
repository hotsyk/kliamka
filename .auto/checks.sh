#!/bin/bash
set -euo pipefail

pytest tests/ -q -m "not packaging"
python -m mypy src/
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/
