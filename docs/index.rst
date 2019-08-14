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
These value wrappers offer the ability to wait for a specific value or
transition.  :class:`AsyncValue` can wrap any type, while :class:`AsyncBool`
offers a simplified API for the common case of bool values.

.. autoclass:: AsyncValue
    :members:
.. autoclass:: AsyncBool
    :members:

collections
-----------
:class:`AsyncDictionary` has many uses, such as multiplexing a networking
connection among tasks.

.. autoclass:: AsyncDictionary
    :show-inheritance:
    :members:

repeated events
---------------
:class:`trio.Event` does not offer a clear() method, so it can't be
triggered multiple times.  It's for your own good.

The following are event classes which can be triggered repeatedly in a
relatively safe manner.  This is achieved by allowing only one listener
and automatically clearing the event after it's received.

.. autoclass:: UnqueuedRepeatedEvent
    :members:
.. autoclass:: MailboxRepeatedEvent
    :members:

generators
----------
.. autofunction:: periodic

iterators
---------
.. autofunction:: azip
.. autofunction:: azip_longest

miscellaneous
-------------
.. autoclass:: TaskStats
    :show-inheritance:
.. autofunction:: defer_to_cancelled
