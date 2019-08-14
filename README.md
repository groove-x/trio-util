[![Build status](https://img.shields.io/circleci/build/github/groove-x/trio-util)](https://circleci.com/gh/groove-x/trio-util)
[![Package version](https://img.shields.io/pypi/v/trio-util.svg)](https://pypi.org/project/trio-util)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/trio-util.svg)](https://pypi.org/project/trio-util)
[![Documentation Status](https://readthedocs.org/projects/trio-util/badge/?version=latest)](https://trio-util.readthedocs.io/en/latest/?badge=latest)

# trio-util

An assortment of utilities for the Trio async/await framework,
including:

  * `await_any`, `await_all` - avoid nursery blocks for simple cases
  * `AsyncBool`, `AsyncValue` - value wrappers with the ability to wait for
    a specific value or transition
  * `AsyncDictionary` - dictionary with waitable get and pop
  * `periodic` - a periodic loop which accounts for its own execution
    time
  * `azip`, `azip_longest` - async zip with parallel iteration
  * `UnqueuedRepeatedEvent`, `MailboxRepeatedEvent` - if you really, really
    want to reuse an event
  * and more (... obscure stuff you probably don't need)!

See the [online documentation](https://trio-util.readthedocs.io/en/latest/) for details.

## Installation

```shell
pip install trio-util
```

## Disclaimer

This software is not supported by GROOVE X, Inc., and GROOVE X
specifically disclaims all warranties as to its quality,
merchantability, or fitness for a particular purpose.
