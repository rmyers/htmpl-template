# Important Paths
base_dir ?= $(shell git rev-parse --show-toplevel)
app_dir ?= $(shell git rev-parse --show-prefix)
venv_dir ?= $(base_dir)/env
venv_bin ?= $(venv_dir)/bin

# Export environment variables
export PYTHONPATH = $(base_dir)

UV_EXE ?= uv
UV_LOCK_FILE ?= uv.lock
UV_SYNC := $(UV_EXE) sync
# Commands
uv_run := $(UV_EXE) run

default: help

check-env:
	@if [ -z "$(UV_EXE)" ]; then \
		echo "Error: Please install 'conda' first"; \
		exit 1; \
	fi

$(UV_LOCK_FILE): pyproject.toml
	$(UV_SYNC)

lock: check-env $(UV_LOCK_FILE)  ## Lock dependencies in project

lock-force: check-env  ## Force lock dependencies in project
	$(UV_SYNC) --refresh

setup: check-env $(UV_LOCK_FILE)  ## Setup local environment
	$(UV_SYNC) --extra dev

type-check:  ## Run mypy to check static types
	$(uv_run) mypy $(args)

test:  ## Run all the unit tests
	$(uv_run) pytest -vv $(ARGS) $(args) tests/

test-pdb:  ## Run all the unit tests, start the Python debugger on errros
	$(uv_run) pytest -vv $(ARGS) $(args) tests/ --log-cli-level=warning --pdb

test-integration:  ## Run the integration tests
	$(uv_run) pytest --no-cov -vv $(ARGS) $(args) tests/ --integration -m integration

test-all:  ## Run all the tests, including integration tests
	$(uv_run) pytest -vv $(ARGS) $(args) tests/ --integration

test-failed:  ## Run tests that failed or all if none failed
	$(uv_run) pytest -vv --lf --no-cov $(ARGS) $(args) tests/

test-only:  ## Run only the tests specified (make test-only args=tests/api/endpoints)
	$(uv_run) pytest -vv --no-cov $(ARGS) $(args)

install-hooks:  ## Install pre-commit hooks
	pre-commit install-hooks

pre-commit:  ## Run pre-commit on the repo
	pre-commit run --verbose --show-diff-on-failure --color=always --all-files

repl:  ## Get a python repl that is configured properly
	$(uv_run) python

fmt:  ## Format code with ruff
	$(uv_run) ruff format

clean:  ## Clean up cache and temporary files and stop containers
	find . -name \*.py[cod] -delete
	rm -rf .pytest_cache .mypy_cache .coverage coverage.xml htmlcov junit dist

build:  ## Run build
	@rm -rf dist
	$(uv_run) python build_release.py
	$(UV_EXE) build

dev:  ## Run the rendered app
	$(uv_run) uvicorn "rendered.app:app" --reload

#% Available Commands:
help: ## Help is on the way
	grep '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-20s%s\n", $$1, $$2}' | sort
