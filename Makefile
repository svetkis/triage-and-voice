.PHONY: install test eval serve

install:
	pip install -e ".[dev]"

test:
	pytest -v

eval:
	python scripts/run_eval.py

serve:
	uvicorn src.api:app --reload
