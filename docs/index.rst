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
objects ``a`` and ``b``, we can wait until either event is set::

    await wait_any(a.wait, b.wait)

or wait until both events are set::

    await wait_all(a.wait, b.wait)

.. autofunction:: wait_any
.. autofunction:: wait_all

In the spirit of Trio's `move_on_after()` cancel scope utility, `move_on_when()`
represents a block of async code that can be interrupted by any async event.

.. autofunction:: move_on_when
    :async-with: cancel_scope

value wrappers
--------------
:class:`AsyncValue` can wrap any type, offering the ability to wait for a
specific value or transition.  It supports various broadcast and "pubsub"
patterns, composition and transformation of values, and synchronizing
values with `eventual consistency <http://en.wikipedia.org/wiki/Eventual_consistency>`_.

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

(Note that the ``while`` loop and ``wait_value()`` combination can be replaced
with ``async for _ in current_state.eventual_values(States.PAUSED): ...``, but the
code above is best for an introduction.)

.. topic:: How does AsyncValue work?

    If you wanted to be notified of specific value changes, one way to implement things
    would be to relay *every* value change to listeners and have them implement the
    filtering locally.  But :class:`AsyncValue` does *not* take this approach because
    it can be fraught with issues like poor performance, queues backing up when there is
    an unresponsive listener, etc.  Rather, listeners pass a predicate representing
    the values or transitions they're interested in, and the ``value`` property
    setter evaluates these `synchronously` and then broadcasts matches as events back
    to the listener.  This is simple for listeners while being efficient and ensuring
    that important value changes aren't lost.

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
