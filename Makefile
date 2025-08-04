# Makefile for Workflown development

.PHONY: help install install-dev test lint format clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install workflown in development mode"
	@echo "  make install-dev  - Install with development dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code with black and isort"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make cli-test     - Test CLI functionality"
	@echo "  make example      - Run example workflow"

# Install in development mode
install:
	./activate_env.sh pip install -e .

# Install with development dependencies
install-dev:
	./activate_env.sh pip install -e ".[dev]"

# Run tests
test:
	./activate_env.sh python -m pytest tests/ -v

# Run linting
lint:
	./activate_env.sh flake8 workflown/ && ./activate_env.sh mypy workflown/

# Format code
format:
	./activate_env.sh black workflown/ && ./activate_env.sh isort workflown/

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Test CLI
cli-test:
	./activate_env.sh workflown --help
	./activate_env.sh workflown --version
	./activate_env.sh workflown list-executors

# Run example
example:
	./activate_env.sh python examples/test_example.py

# Check package structure
check:
	./activate_env.sh python -c "import workflown; print('✅ Package imports successfully')" 