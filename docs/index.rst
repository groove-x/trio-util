Python trio-util documentation
==============================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

.. currentmodule:: trio_util

nursery utilities
-----------------
The following utilities are intended to avoid nursery boilerplate in some
simple cases.

:func:`wait_any` and :func:`wait_all` are used to simultaneously
run async functions which either have side effects and don't return a
value, or signal merely by exiting.  For example, given two :class:`trio.Event`
objects ``a`` and ``b``, we can wait until either event is true::

    await wait_any(a.wait, b.wait)

or wait until both events are true::

    await wait_all(a.wait, b.wait)

.. autofunction:: wait_any
.. autofunction:: wait_all

value wrappers
--------------
:class:`AsyncValue` can wrap any type, offering the ability to wait for a
specific value or transition.  :class:`AsyncBool` is just an :class:`AsyncValue`
that defaults to ``False``.

Here's a quick example based on this real use case posted to one of Trio's forums:

.. epigraph::

    I noticed how hard [writing state machines in Trio] becomes, especially when
    there are requirements like e.g. "when in state paused longer than X toggle
    to stopped"...

:class:`AsyncValue` together with Trio's cancellation make it easy::

    current_state = AsyncValue(States.INIT)
    ...

    async def monitor_paused_too_long():
        while True:
            await current_state.wait_value(States.PAUSED)
            with trio.move_on_after(X):
                await current_state.wait_transition()  # any transition out of PAUSED
                continue
            current_state.value = States.STOPPED

.. autoclass:: AsyncValue

    .. autoattribute:: value
    .. automethod:: wait_value
    .. automethod:: eventual_values
        :async-for: value
    .. automethod:: wait_transition
    .. automethod:: transitions
        :async-for: value, old_value
    .. automethod:: open_transform
        :with: output

.. autoclass:: AsyncBool
    :members:

Sometimes you want to wait on a condition involving multiple async values.
This can be achieved without resorting to polling by employing the
:func:`compose_values` context manager.

.. autofunction:: compose_values
    :with: composed

repeated events
---------------
:class:`trio.Event` does not offer a clear() method, so it can't be
triggered multiple times.  It's for your own good.

:class:`RepeatedEvent` can be triggered repeatedly in a relatively safe manner
while having multiple listeners.

.. autoclass:: RepeatedEvent
    :members:

generators
----------
.. autofunction:: periodic
    :async-for: elapsed, delta
.. autodecorator:: trio_async_generator

iterators
---------
.. autofunction:: azip
    :async:
.. autofunction:: azip_longest
    :async:

exceptions
----------
.. autofunction:: multi_error_defer_to
    :no-auto-options:
    :with:
.. autofunction:: defer_to_cancelled
    :with:

miscellaneous
-------------
.. autoclass:: TaskStats
    :show-inheritance:
