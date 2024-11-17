.PHONY: all
all: test lint type_check

# ignore exceptions utilities when MultiError is not available or deprecated
ifneq ($(shell python -c 'from trio import MultiError' 2>&1), )
IGNORE_FILES_REGEX=".*_exceptions.py"
IGNORE_FILES_GLOB="*_exceptions.py"
else
IGNORE_FILES_REGEX="^$$"
IGNORE_FILES_GLOB=""
endif

.PHONY: test
test:
	PYTHONPATH=src python -m pytest --cov=src/ --no-cov-on-fail $(PYTEST_ARGS) --ignore-glob $(IGNORE_FILES_GLOB) tests/

.PHONY: lint
lint:
	PYTHONPATH=src python -m pylint --ignore-patterns $(IGNORE_FILES_REGEX) src/ tests/

.PHONY: type_check
type_check:
	PYTHONPATH=src mypy --show-error-codes --check-untyped-defs --ignore-missing-imports --exclude $(IGNORE_FILES_REGEX) src/ tests/

# explicitly update .txt after changing .in:
#   make -W test-requirements.{in,txt} PIP_COMPILE_ARGS="-q"
# upgrade all deps:
#   make -W test-requirements.{in,txt} PIP_COMPILE_ARGS="-U"
# upgrade specific deps:
#   make -W test-requirements.{in,txt} PIP_COMPILE_ARGS="-P foo"
ifneq ($(PIP_COMPILE_ARGS),)
test-requirements.txt: setup.py test-requirements.in
	pip-compile -q $(PIP_COMPILE_ARGS) --output-file $@ $^
endif
