VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help dev install lint format test run worker spike clean

help:
	@echo "dev      - create the venv, install .[dev] + pre-commit hooks"
	@echo "install  - install the package (prod)"
	@echo "lint     - ruff check"
	@echo "format   - ruff format"
	@echo "test     - pytest"
	@echo "run      - start the API (uvicorn, reload)"
	@echo "worker   - start the live ingestion worker"
	@echo "spike    - run the Phase 0 spike (stdlib only)"

$(VENV):
	python3 -m venv $(VENV)

dev: $(VENV)
	$(PIP) install -e ".[dev]"
	$(VENV)/bin/pre-commit install

install: $(VENV)
	$(PIP) install -e .

lint:
	$(VENV)/bin/ruff check .

format:
	$(VENV)/bin/ruff format .

test:
	$(VENV)/bin/pytest -q

run:
	$(VENV)/bin/uvicorn app.main:app --reload

worker:
	$(VENV)/bin/python -m app.ingestion.worker

spike:
	python3 spike/phase0_lol_spike.py

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache **/__pycache__ *.db
