.PHONY: install test lint typecheck check eval serve

install:
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check .

typecheck:
	mypy

check: lint typecheck test

eval:
	python scripts/run_eval.py

serve:
	uvicorn src.api:app --reload
