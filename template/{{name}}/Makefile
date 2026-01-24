# Setup the env
export PYTHONPATH = ./

# PHONY just means this target does not make any files
.PHONY: setup clean test help

default: help

deps: ## Run any dependencies for local dev and test
	@echo "Starting deps"

.env:
	cp dotenv .env

setup: .env  ## Setup the project
	uv sync

dev: ## Run the application in dev mode
	uv run cuneus run --reload

test: deps ## Run pytests
	uv run pytest

test-failed: deps ## Re-Run pytest on tests that failed
	uv run pytest --lf

#% Available Commands:
help: ## Help is on the way
	grep '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-20s%s\n", $$1, $$2}' | sort
