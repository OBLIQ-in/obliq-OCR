.PHONY: install lint format test check clean

install:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check .
	mypy src/obliq_ocr

format:
	ruff format .

test:
	python -m pytest -v --cov=obliq_ocr

check: lint test

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
