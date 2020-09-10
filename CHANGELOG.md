# Release history

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
