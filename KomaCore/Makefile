test:
	PYTHONPATH=. pytest -q --maxfail=1 --disable-warnings

coverage:
	PYTHONPATH=. pytest --cov=.

fmt:
	black .
	ruff check --fix

lint:
	ruff check
	black --check .