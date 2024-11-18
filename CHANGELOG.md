# Release history

## trio-util 0.8.0 (2024-11-17)
### Added
- `periodic()` is now type-annotated
### Fixed
- runtime fixes for Python 3.13

## trio-util 0.7.0 (2021-11-14)
### Added
- `iter_move_on_after()` and `iter_fail_after()` are iterator wrappers
  that apply a timeout to a single iteration.
- `run_and_cancelling()` is a context manager that runs a background
  task and cancels it on exit of the block.
- `AsyncValue.eventual_values()` supports a `held_for` option.
### Fixed
- `move_on_when()` now returns a cancel scope other than the implementation's
  nursery, so that cancelled_caught is meaningful.

## trio-util 0.6.0 (2021-09-05)
### Added
- `AsyncValue` and `compose_values()` now have type hints and generic typing.
- `move_on_when()` is a cancel scope that exits when a given async callable
  returns.
### Changed
- `_transform_` parameter of `compose_values()` is now keyword-only.
### Fixed
- slight performance improvement to `AsyncValue.value` setter when there is a
  predicate match.

## trio-util 0.5.0 (2021-04-06)
⚠ includes breaking changes!
### Added
- `eventual_values()` is a new iterator of `AsyncValue` which assures
  "eventual consistency" (i.e. the caller always receives the latest value).
- `open_transform()` is a new context manager of `AsyncValue` enabling derived
  values.
### Changed
- `compose_values()` context manager was changed from async to synchronous.
- `compose_values()` now takes an optional transform function.
- `RepeatedEvent` replaces both `UnqueuedRepeatedEvent` and `MailboxRepeatedEvent`.
  The new class handles both unqueued and eventual consistency cases, while
  supporting multiple listeners.  It also offers a one-shot `wait_event()` method
  for cases where an iterator isn't needed.

## trio-util 0.4.1 (2021-03-27)
### Fixed
- `compose_values()` had a race where the composed value may be incorrect if
  the underlying values are mutated while entering the async context manager.

## trio-util 0.4.0 (2021-02-01)
### Added
- `transitions()` is a new method of `AsyncValue` that allows subscription
  to value transitions via an iterator.
### Changed
- `UnqueuedRepeatedEvent` supports broadcasting to multiple listeners
- `TaskStats` now reports all scheduling rates over a given threshold, rather
  than the maximum observed rate.
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
