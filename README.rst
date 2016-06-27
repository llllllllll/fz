``fz`` 0.1
==========

Quick and efficient lambda functions.

What is ``fz``?
---------------

``fz`` provides a nicer way to define lambda functions for Python 3. The syntax
is inspired by C++ ``std::bind``, Scala lambdas, and `quicklambda
<https://github.com/abarnert/quicklambda>`_ for python.


Syntax
------

``fz`` lambdas use placeholder objects to represent the arguments to the new
lambda. The placeholders look like: ``_1``, ``_2``, ..., all the way to ``_255``
(the maximum number of positional arguments to a function).

To create a lambda, just build up an expression using these placeholders where
you want the arguments to go.

Example Uses
------------

Simple Arithmetic
~~~~~~~~~~~~~~~~~

Many lambdas are just simple arithmetic. For example:

.. code-block:: python

   >>> from fz import _1
   >>> f = _1 + 1
   >>> f(1)
   2
   >>> f(3)
   4
   >>> (_1 * 2)(3)
   6
   >>> (_1 ** 2)(3)
   9
   >>> list(map(_1 ** 2, range(5)))
   [0, 1, 4, 9, 16]


Attribute and Item Access
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block::

   >>> from fz import _1

   >>> _1[0]([1, 2])
   1
   >>> list(map(_1[1], [(0, 1), (2, 3), (4, 5)]))
   [1, 3, 5]
   >>> _1.imag(1j)
   1.0
   >>> list(map(_1.imag, (1j, 1 + 2j, 2 + 3j)))
   [1, 2, 3]


Function Calls
~~~~~~~~~~~~~~

Because we can only wrap things top-down, we must explicitly wrap a function
to be defered.

.. code-block:: python

   >>> from fz import _f, _1, _2, _3
   >>> def f(a, b):
   ...     return a + b
   >>> _f(f)(_1, _2)(1, 2)
   3
   >>> g = _f(f)(_1, -1)
   >>> g(1)
   0

   >>> flip = _f(_1)(_3, _2)
   >>> flip(print, 1, 2)
   2 1


Supported Operations
~~~~~~~~~~~~~~~~~~~~

- Binary operators
- Unary operators
- Attribute access (some names are used for the implementation)
- Subscript (item access)
- ``iter``
- ``next``
- ``abs``


License
-------

``fz`` is free software, licensed under the GNU General Public
License, version 2. For more information see the ``LICENSE`` file.


Source
------

Source code is hosted on github at https://github.com/llllllllll/fz.
