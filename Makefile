.PHONY: test lint typecheck format build clean all help

# Default target
all: build test

help:
	@echo "Available targets:"
	@echo "  all         - Build and run all tests (default)"
	@echo "  test        - Run all tests (pytest + typecheck + lint)"
	@echo "  pytest      - Run pytest tests only"
	@echo "  typecheck   - Run mypy type checking"
	@echo "  lint        - Run ruff linting"
	@echo "  format      - Format code with ruff"
	@echo "  build       - Build the package"
	@echo "  clean       - Clean build artifacts"

# Run all tests
test: build pytest typecheck lint
	@echo "✅ All tests passed!"

# Run pytest
pytest:
	@echo "🧪 Running pytest tests..."
	uv run python test_scoped_stats.py

# Run type checking
typecheck:
	@echo "🔍 Running mypy type checking..."
	uv run mypy --explicit-package-bases scoped_stats.py test_scoped_stats.py benchmark.py

# Run linting
lint:
	@echo "🔧 Running ruff linting..."
	uv run ruff check .

# Format code
format:
	@echo "🎨 Formatting code with ruff..."
	uv run ruff format .

# Build package  
build:
	@echo "🔨 Building package..."
	@# Ensure dependencies are installed
	uv sync --extra dev
	@echo "📦 Package built successfully"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	@echo "✨ Clean complete"