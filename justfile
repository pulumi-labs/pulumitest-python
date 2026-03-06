# Default recipe - show help
default:
    @just --list

# Run all tests
test:
    uv run pytest tests/

# Run linter
lint:
    uv run ruff check .
    uv run ruff format --check .

# Auto-fix lint issues
lint-fix:
    uv run ruff check --fix .
    uv run ruff format .

# Install development dependencies
install:
    uv sync --dev

# Install git hooks (pre-push)
install-hooks:
    @echo "Installing git hooks..."
    cp scripts/hooks/pre-push .git/hooks/pre-push
    chmod +x .git/hooks/pre-push
    @echo "Git hooks installed"

# Clean build artifacts
clean:
    rm -rf dist/ build/ *.egg-info
