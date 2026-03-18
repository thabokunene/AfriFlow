.PHONY: install test lint format clean help

PYTHON := python
PIP := pip
pytest := pytest

help:
	@echo "Available commands:"
	@echo "  install    Install dependencies"
	@echo "  test       Run unit tests"
	@echo "  lint       Run linters (black, isort, flake8, mypy)"
	@echo "  format     Format code (black, isort)"
	@echo "  clean      Remove build artifacts"

install:
	$(PIP) install -e .[dev]

test:
	$(pytest)

lint:
	black --check .
	isort --check-only .
	flake8 .
	mypy .

format:
	black .
	isort .

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
