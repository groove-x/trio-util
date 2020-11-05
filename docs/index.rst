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

.. autoclass:: AsyncValue

    .. autoattribute:: value
    .. automethod:: wait_value
    .. automethod:: wait_transition
    .. automethod:: transitions
        :async-for: value, old_value

.. autoclass:: AsyncBool
    :members:

Sometimes you want to wait on a condition involving multiple async values.
This can be achieved without resorting to polling by employing the
:func:`compose_values` context manager.

.. autofunction:: compose_values
    :async-with: composed

repeated events
---------------
:class:`trio.Event` does not offer a clear() method, so it can't be
triggered multiple times.  It's for your own good.

The following are event classes which can be triggered repeatedly in a
relatively safe manner.

.. autoclass:: UnqueuedRepeatedEvent
    :members:
.. autoclass:: MailboxRepeatedEvent
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
