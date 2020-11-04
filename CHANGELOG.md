# Release history

## trio-util (pending)
### Added
- `transitions()` is a new method of `AsyncValue` that allows subscription
  to value transitions via an iterator.
### Fixed
- `multi_error_defer_to()` would use the wrong context when raising `RuntimeError`

## trio-util 0.3.0 (2020-10-27)
### Added
- `@trio_async_generator` is a decorator which adapts a generator containing
  Trio constructs for safe use.  (Normally, it's not allowed to yield from a
  nursery or cancel scope when implementing async generators.)
### Changed
- `TaskStats` now reports all slow task step events over a given threshold,
  rather than the maximum observed task step.
### Removed
- `AsyncDictionary` has been removed.  It didn't work well for the advertised
  use case of multiplexing a network connection, and trying to address that
  while keeping the regular dict interface (itself of unproven value) seemed to
  result in an overly complex API.  See [discussion](https://github.com/groove-x/trio-util/issues/4).

## trio-util 0.2.0 (2020-09-09)
### Added
- `AsyncValue.wait_value() / wait_transition()` additionally accept a plain
  value to match by equality, and `AsyncBool` is now a subclass
  of `AsyncValue`.
- `held_for` is a new option of `AsyncValue.wait_value()`,
  requiring a match for the specified duration.
- `compose_values()` is a context manager that enables waiting on conditions
  involving multiple async values
- `multi_error_defer_to()` is a context manager that allows deferring
  `trio.MultiError` exceptions to a single, privileged exception.

## trio-util 0.1.1 (2020-06-04)
### Fixed
- Support rename of `trio.hazmat` to `trio.lowlevel`
 
## trio-util 0.1.0 (2019-08-22)
Initial version
