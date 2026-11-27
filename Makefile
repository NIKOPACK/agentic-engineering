.PHONY: check validate lint typecheck test

check: validate lint typecheck test

validate:
	python3 scripts/validate.py

lint:
	uvx ruff check .
	uvx ruff format --check .

typecheck:
	uv run --no-project --with mypy --with types-PyYAML mypy --strict --python-version 3.11 agent/hooks/policy.py scripts tests

test:
	python3 -m unittest discover -s tests
