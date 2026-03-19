# =============================================================================
# @file Makefile
# @description Orchestrates common development tasks for the AfriFlow project,
#              including dependency installation, testing, linting, and cleanup.
# @author Thabo Kunene
# @created 2026-03-19
# =============================================================================

# Mark targets as 'phony' to prevent conflicts with files of the same name
.PHONY: install test lint format clean help

# Define the Python interpreter and associated tools
PYTHON := python
PIP := pip
pytest := pytest

# --- Documentation / Help ---
# Displays a list of available Makefile targets and their purposes
help:
	@echo "Available commands:"
	@echo "  install    Install development dependencies"
	@echo "  test       Run the full pytest suite"
	@echo "  lint       Validate code quality (black, isort, flake8, mypy)"
	@echo "  format     Apply automated code formatting (black, isort)"
	@echo "  clean      Remove temporary build artifacts and caches"

# --- Dependency Management ---
# Installs the current package in editable mode with development extras
install:
	$(PIP) install -e .[dev]

# --- Testing ---
# Executes all discovered unit and integration tests
test:
	$(pytest)

# --- Code Quality ---
# Runs a comprehensive suite of static analysis and linting tools
lint:
	# Check formatting compliance without making changes
	black --check .
	# Verify import statement ordering compliance
	isort --check-only .
	# Check for PEP 8 violations and potential logical errors
	flake8 .
	# Perform static type checking based on type annotations
	mypy .

# --- Formatting ---
# Automatically formats the codebase to adhere to project standards
format:
	# Reformat Python files according to Black rules
	black .
	# Sort and group import statements
	isort .

# --- Cleanup ---
# Deletes temporary files, build artifacts, and Python cache directories
clean:
	# Remove Python build and distribution folders
	rm -rf build/
	rm -rf dist/
	# Remove package metadata information
	rm -rf *.egg-info
	# Delete compiled Python bytecode files
	find . -name '*.pyc' -delete
	# Remove Python bytecode cache directories
	find . -name '__pycache__' -delete
