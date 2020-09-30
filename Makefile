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

# upgrade all deps:
#   make -W test-requirements.{in,txt} PIP_COMPILE_ARGS="-U"
# upgrade specific deps:
#   make -W test-requirements.{in,txt} PIP_COMPILE_ARGS="-P foo"
test-requirements.txt: setup.py test-requirements.in
	pip-compile -q $(PIP_COMPILE_ARGS) --output-file $@ $^
