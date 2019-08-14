.PHONY: all
all: test lint type_check

.PHONY: test
test:
	PYTHONPATH=src python -m pytest --cov=src/ --no-cov-on-fail tests/

.PHONY: lint
lint:
	PYTHONPATH=src python -m pylint src/ tests/

.PHONY: type_check
type_check:
	PYTHONPATH=src mypy --ignore-missing-imports src/ tests/

test-requirements.txt: test-requirements.in
	pip-compile --output-file $@ $<
