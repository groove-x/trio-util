from collections import namedtuple
from contextlib import contextmanager, ExitStack
from functools import partial

from ._async_value import AsyncValue


def _IDENTITY(x):
    return x


@contextmanager
def compose_values(_transform_=None, **value_map):
    """Context manager providing a composite of multiple AsyncValues

    The composite object itself is an AsyncValue, with the `value` of each
    underlying object accessible as attributes on the composite `value`.

    `compose_values()` expects named AsyncValue instances to be provided as
    keyword arguments.  The attributes of the composite value will correspond
    to the given names.

    It's mostly an implementation detail, but the composite value type is a
    namedtuple.  Users should not write to the composite `value` attribute
    since it is exclusively managed by the context.

    Synopsis:

        >>> async_x, async_y = AsyncValue(-1), AsyncValue(10)
        >>>
        >>> with compose_values(x=async_x, y=async_y) as async_xy:
        >>>     result = await async_xy.wait_value(lambda val: val.x < 0 < val.y))
        >>>
        >>> result
        CompositeValue(x=-1, y=10)

    The `_transform_` parameter specifies an optional function to transform the
    final value.  This is equivalent but more efficient than chaining a single
    open_transform() to the default compose_values() output.  For example:

        >>> with compose_values(x=async_x, y=async_y,
        >>>                     _transform_=lambda val: val.x * val.y) as x_mul_y:
        >>>     ...

    is equivalent to:

        >>> with compose_values(x=async_x, y=async_y) as async_xy, \\
        >>>         async_xy.open_transform(lambda val: val.x * val.y) as x_mul_y:
        >>>     ...
    """
    transform = _transform_ or _IDENTITY
    async_vals = value_map.values()
    if not (async_vals and all(isinstance(av, AsyncValue) for av in async_vals)):
        raise TypeError('expected instances of AsyncValue')
    value_type = namedtuple('CompositeValue', value_map.keys())
    composite_value = value_type._make(av.value for av in async_vals)
    composite = AsyncValue(transform(composite_value))

    # This dummy wait_value() predicate hooks into each value and updates
    # the composite as a side effect.
    def _update_composite(name, val):
        nonlocal composite_value
        composite_value = composite_value._replace(**{name: val})
        composite.value = transform(composite_value)
        return False

    with ExitStack() as stack:
        for name_, async_val in value_map.items():
            # NOTE: by using AsyncValue internals we avoid running wait_value()
            # as a child task for each event.
            stack.enter_context(
                async_val._level_results.open_ref(partial(_update_composite, name_)))

        yield composite
