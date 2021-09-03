[![Build status](https://img.shields.io/circleci/build/github/groove-x/trio-util)](https://circleci.com/gh/groove-x/trio-util)
[![Code coverage](https://img.shields.io/codecov/c/gh/groove-x/trio-util)](https://app.codecov.io/gh/groove-x/trio-util)
[![Package version](https://img.shields.io/pypi/v/trio-util.svg)](https://pypi.org/project/trio-util)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/trio-util.svg)](https://pypi.org/project/trio-util)
[![Documentation Status](https://readthedocs.org/projects/trio-util/badge/?version=latest)](https://trio-util.readthedocs.io/en/latest/?badge=latest)

# trio-util

An assortment of utilities for the Python Trio async/await framework,
including:

  * `wait_any`, `wait_all`, `move_on_when` - avoid nursery blocks for simple cases
  * `AsyncBool`, `AsyncValue` - value wrappers with the ability to wait for
    a specific value or transition
  * `periodic` - periodic loop which accounts for its own execution
    time
  * `@trio_async_generator` - decorator which adapts a generator containing
     Trio constructs for safe use
  * `azip`, `azip_longest` - async zip with parallel iteration
  * `RepeatedEvent` - if you really, really want to reuse an event
  * and more (... obscure stuff you probably don't need)!

See the [online documentation](https://trio-util.readthedocs.io/en/latest/) for details.

## Installation

```shell
pip install trio-util
```

## Contributing

What attributes make a good utility function or class?

  * of general use, intuitive, hard to use incorrectly
  * makes code more readable and reduces cognitive load
  * already vetted for a length of time within a project, ideally used
    by multiple developers

If you have something that would be a good fit for trio-util, please
open an issue on GitHub.  We'll want to review the design, naming, and
documentation.

## Disclaimer

This software is not supported by GROOVE X, Inc., and GROOVE X
specifically disclaims all warranties as to its quality,
merchantability, or fitness for a particular purpose.
