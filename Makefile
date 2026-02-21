.DEFAULT_GOAL := help
.PHONY: help install test lint format typecheck clean

help:  ## Show this help message.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Install the dependencies without creating an in-project virtualenv.
	@poetry config virtualenvs.in-project false
	@poetry install

test: ## Run the test suite with coverage.
	@poetry run pytest --cov=src/agent_vault tests/

lint: ## Lint the codebase using Ruff.
	@poetry run ruff check src/ tests/

format: ## Format the codebase using Ruff.
	@poetry run ruff format src/ tests/

typecheck: ## Run static type checking using MyPy.
	@poetry run mypy src/ tests/

clean: ## Clean up generated cache, coverage, and build files.
	@find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -exec rm -f {} + 2>/dev/null || true
