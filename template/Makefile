BASE_DIR    := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
PROG_NAME   := $(shell basename $(BASE_DIR))
SHELL       := /bin/bash
UV          ?= uv

################################################################
#%
#% Usage:
#%   make <command>
#%
#% Getting Started:
#%   make setup
#%
#% Run the tests locally:
#%   make test
#%
#% Available Commands:
help: ## Help is on the way
	@echo " Tools for building, running, and testing $(PROG_NAME)"
	@grep '^#%' $(MAKEFILE_LIST) | sed -e 's/#%//'
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-20s%s\n", $$1, $$2}' | sort

export PYTHONPATH ?= ./

# Refresh lock if pyproject.toml is newer than uv.lock
uv.lock: pyproject.toml
	$(UV) lock --refresh

.PHONY: setup
setup: uv.lock ## Install dependencies for the project
	$(UV) sync --all-extras

.PHONY: update
update: ## Update all dependencies to latest
	$(UV) lock --upgrade
	$(UV) sync --all-extras

.PHONY: clean
clean: ## Remove virtual environment
	rm -rf .venv

.PHONY: deps
deps: setup .env ## Run any dependencies for local dev and test
	@echo "Starting deps..."

.PHONY: dev
dev: deps ## Run the application in dev mode
	$(UV) run cuneus dev

.PHONY: prod
prod: deps ## Run the application in prod mode
	$(UV) run cuneus prod

.PHONY: test
test: deps ## Run pytests
	$(UV) run pytest

.PHONY: test-failed
test-failed: deps ## Re-Run pytest on tests that failed
	$(UV) run pytest --lf