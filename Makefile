.PHONY: install install-dev test lint clean

# Install the package in editable mode
install:
	pip install -e .

# Install development dependencies
install-dev: install
	pip install pytest pytest-mock ruff

# Run tests
test:
	python -m pytest tests/ -v

# Lint with ruff
lint:
	ruff check src/ tests/ scripts/

# Clean up build artifacts and cache
clean:
	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf tests/__pycache__
	rm -rf scripts/__pycache__
	rm -rf *.egg-info
	rm -rf dist
	rm -rf build
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
