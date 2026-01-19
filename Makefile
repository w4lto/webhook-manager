.PHONY: help install dev uninstall test clean format lint build publish docs

help:
	@echo "╔════════════════════════════════════════╗"
	@echo "║   🚇 Webhook Tunnel - Makefile         ║"
	@echo "╚════════════════════════════════════════╝"
	@echo ""
	@echo "Available commands:"
	@echo "  make install     - Install from source"
	@echo "  make dev         - Install in development mode"
	@echo "  make uninstall   - Uninstall package"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make format      - Format code with black"
	@echo "  make lint        - Lint code with flake8"
	@echo "  make build       - Build distribution packages"
	@echo "  make publish     - Publish to PyPI"
	@echo "  make test-pypi   - Publish to TestPyPI"
	@echo "  make docs        - Generate documentation"
	@echo "  make run-tui     - Run TUI interface"
	@echo "  make run-server  - Run example webhook server"

install:
	@echo "📦 Installing webhook-tunnel..."
	pip install .
	@echo "✅ Installation complete!"

dev:
	@echo "🔧 Installing in development mode..."
	pip install -e ".[dev,webhook-server]"
	@echo "✅ Development installation complete!"

uninstall:
	@echo "🗑️  Uninstalling webhook-tunnel..."
	pip uninstall -y webhook-tunnel
	@echo "✅ Uninstallation complete!"

test:
	@echo "🧪 Running tests..."
	pytest tests/ -v --cov=webhook_tunnel --cov-report=html --cov-report=term
	@echo "✅ Tests complete! Coverage report: htmlcov/index.html"

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .eggs/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .tox/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✅ Cleanup complete!"

format:
	@echo "✨ Formatting code..."
	black webhook_tunnel/
	black tests/ 2>/dev/null || true
	@echo "✅ Formatting complete!"

lint:
	@echo "🔍 Linting code..."
	flake8 webhook_tunnel/ --max-line-length=88 --extend-ignore=E203
	@echo "✅ Linting complete!"

typecheck:
	@echo "🔍 Type checking..."
	mypy webhook_tunnel/
	@echo "✅ Type checking complete!"

build: clean
	@echo "🏗️  Building distribution packages..."
	python -m build
	@echo "✅ Build complete!"
	@echo ""
	@echo "Packages created:"
	@ls -lh dist/

check-build: build
	@echo "🔍 Checking distribution packages..."
	twine check dist/*
	@echo "✅ Check complete!"

test-pypi: check-build
	@echo "📤 Publishing to TestPyPI..."
	twine upload --repository testpypi dist/*
	@echo "✅ Published to TestPyPI!"
	@echo ""
	@echo "Test installation:"
	@echo "  pip install --index-url https://test.pypi.org/simple/ webhook-tunnel"

publish: check-build
	@echo "⚠️  About to publish to PyPI..."
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	@echo "📤 Publishing to PyPI..."
	twine upload dist/*
	@echo "✅ Published to PyPI!"
	@echo ""
	@echo "Install with:"
	@echo "  pip install webhook-tunnel"

docs:
	@echo "📚 Generating documentation..."
	@echo "Documentation is in README.md and PUBLISHING.md"

run-tui:
	@echo "🚀 Launching TUI interface..."
	python -m webhook_tunnel.tui

run-server:
	@echo "🚀 Starting example webhook server..."
	python -m webhook_tunnel.webhook_server

run-cli:
	@echo "🚀 Running CLI..."
	python -m webhook_tunnel.cli --help

demo: dev
	@echo "🎮 Running demo..."
	@echo ""
	@echo "Starting example webhook server on port 5000..."
	@python -m webhook_tunnel.webhook_server &
	@sleep 2
	@echo ""
	@echo "Creating tunnel..."
	@python -m webhook_tunnel.cli start demo 5000
	@echo ""
	@echo "Press Ctrl+C to stop"

version:
	@echo "📌 Current version:"
	@python -c "from webhook_tunnel import __version__; print(__version__)"

requirements:
	@echo "📋 Updating requirements.txt..."
	pip freeze | grep -E "(click|textual|rich|psutil|flask)" > requirements.txt
	@echo "✅ Requirements updated!"

setup-dev:
	@echo "🔧 Setting up development environment..."
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Activating virtual environment..."
	@echo "Run: source venv/bin/activate"
	@echo "Then run: make dev"

all: clean format lint test build check-build
	@echo "✅ All tasks complete!"
