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

It may be tempting to use :func:`wait_any` where you have some long-running,
async code that should be interrupted by an event.  In the context of a function
scope, you would likely structure it by defining a local function for the
long-running code::

    async def foo():
        # NOT recommended
        async def _my_endless_task():
            while True:
                await trio.sleep(5)
                if some_condition:
                    counter += 1  # bug (missing `nonlocal` definition)
                elif other_condition:
                    return  # maybe-bug: you intended to exit `foo()`?

        counter = 0
        # run the endless async loop until some_event triggers
        await wait_any(_my_endless_task, some_event.wait)
        if counter > 10: ...

By writing the long-running code as a separate function rather than inline,
we're interfering with the natural flow of control (can't write to local vars
or use ``continue`` / ``break`` / ``return`` in the context of ``foo()``).  For
this we have something better: :func:`move_on_when()`.

In the spirit of Trio's :func:`move_on_after()` cancel scope utility,
:func:`move_on_when()` represents a block of async code that can be interrupted
by any async event.  By letting the primary "task" be written inline, the code
has access to everything wonderful about ``foo()``'s local scope::

    async def foo():
        counter = 0
        async with move_on_when(some_event.wait):
            while True:
                await trio.sleep(5)
                if some_condition:
                    counter += 1
                elif other_condition:
                    return
        if counter > 10: ...

.. autofunction:: move_on_when
    :async-with: cancel_scope

:func:`run_and_cancelling`, on the other hand, is a context manager
that runs a background task that is not able to interrupt your block of code.
At the end of the block, the background task is cancelled if necessary.

.. autofunction:: run_and_cancelling

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
When working with an asynchronous iterator, you may want to cancel iteration or
raise an error when a single iteration takes too long.  :func:`iter_move_on_after`
and :func:`iter_fail_after` can wrap an iterator to provide this.

.. autofunction:: iter_move_on_after
    :async:
.. autofunction:: iter_fail_after
    :async:

:func:`azip` and :func:`azip_longest` are async equivalents of :func:`zip`
and :func:`itertools.zip_longest`.

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
