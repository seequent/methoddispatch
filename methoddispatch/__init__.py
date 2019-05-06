# -*- coding: utf-8 -*-
"""
# methoddispatch

[![Build Status](https://travis-ci.com/seequent/methoddispatch.svg?branch=master)](https://travis-ci.com/seequent/methoddispatch)

Python 3.4 added the ``singledispatch`` decorator to the ``functools`` standard library module.
This library adds this functionality to instance methods.

To define a generic method , decorate it with the ``@singledispatch`` decorator. Note that the dispatch happens on the type of the first argument, create your function accordingly.
To add overloaded implementations to the function, use the ``register()`` attribute of the generic function. It is a decorator, taking a type parameter and decorating a function implementing the operation for that type
The ``register()`` attribute returns the undecorated function which enables decorator stacking, pickling, as well as creating unit tests for each variant independently

    >>> from methoddispatch import singledispatch, register, SingleDispatch
    >>> from decimal import Decimal
    >>> class MyClass(SingleDispatch):
    ...     @singledispatch
    ...     def fun(self, arg, verbose=False):
    ...         if verbose:
    ...             print("Let me just say,", end=" ")
    ...         print(arg)
    ...
    ...     @fun.register(int)
    ...     def fun_int(self, arg, verbose=False):
    ...         if verbose:
    ...             print("Strength in numbers, eh?", end=" ")
    ...         print(arg)
    ...
    ...     @fun.register(list)
    ...     def fun_list(self, arg, verbose=False):
    ...         if verbose:
    ...             print("Enumerate this:")
    ...         for i, elem in enumerate(arg):
    ...             print(i, elem)
    ...
    ...     @fun.register(float)
    ...     @fun.register(Decimal)
    ...     def fun_num(obj, arg, verbose=False):
    ...         if verbose:
    ...             print("Half of your number:", end=" ")
    ...         print(arg / 2)

The ``register()`` attribute only works inside a class statement, relying on ``SingleDispatch.__init_subclass__``
to create the actual dispatch table.  This also means that (unlike functools.singledispatch) two methods
with the same name cannot be registered as only the last one will be in the class dictionary.

Functions not defined in the class can be registered using the ``add_overload`` attribute.

    >>> def nothing(obj, arg, verbose=False):
    ...    print('Nothing.')
    >>> MyClass.fun.add_overload(type(None), nothing)

When called, the generic function dispatches on the type of the first argument::

    >>> a = MyClass()
    >>> a.fun("Hello, world.")
    Hello, world.
    >>> a.fun("test.", verbose=True)
    Let me just say, test.
    >>> a.fun(42, verbose=True)
    Strength in numbers, eh? 42
    >>> a.fun(['spam', 'spam', 'eggs', 'spam'], verbose=True)
    Enumerate this:
    0 spam
    1 spam
    2 eggs
    3 spam
    >>> a.fun(None)
    Nothing.
    >>> a.fun(1.23)
    0.615

Where there is no registered implementation for a specific type, its method resolution order is used to find a more generic implementation. The original function decorated with ``@singledispatch`` is registered for the base ``object`` type, which means it is used if no better implementation is found.

To check which implementation will the generic function choose for a given type, use the ``dispatch()`` attribute::

    >>> a.fun.dispatch(float)
    <function MyClass.fun_num at 0x1035a2840>
    >>> a.fun.dispatch(dict)    # note: default implementation
    <function MyClass.fun at 0x103fe0000>

To access all registered implementations, use the read-only ``registry`` attribute::

    >>> a.fun.registry.keys()
    dict_keys([<class 'NoneType'>, <class 'int'>, <class 'object'>,
              <class 'decimal.Decimal'>, <class 'list'>,
              <class 'float'>])
    >>> a.fun.registry[float]
    <function MyClass.fun_num at 0x1035a2840>
    >>> a.fun.registry[object]
    <function MyClass.fun at 0x103fe0000>

    >>> class BaseClass(SingleDispatch):
    ...     @singledispatch
    ...     def foo(self, bar):
    ...         return 'default'
    ...
    ...     @foo.register(int)
    ...     def foo_int(self, bar):
    ...         return 'int'
    ...
    >>> b = BaseClass()
    >>> b.foo('hello')
    'default'
    >>> b.foo(1)
    'int'

Subclasses can extend the type registry of the function on the base class with their own overrides.
Because we do not want to modify the base class ``foo`` registry the ``foo.overload`` decorator must be used
instead of ``foo.register``.

    >>> class SubClass(BaseClass):
    ...     @BaseClass.foo.register(float)
    ...     def foo_float(self, bar):
    ...         return 'float'
    ...
    ...     @BaseClass.foo.register(str)
    ...     def foo_str(self, bar):
    ...         return 'str'
    ...
    >>> s = SubClass()
    >>> s.foo('')
    'str'
    >>> s.foo(1.0)
    'float'

The ``SingleDispatch`` mixin class ensures that each subclass has it's own independant copy of the dispatch registry

    >>> b = BaseClass()
    >>> b.foo(1.0)
    'default'

Method overrides do not need to provide the ``register`` decorator again to be used in the dispatch of ``foo``

    >>> class SubClass2(BaseClass):
    ...     def foo_int(self, bar):
    ...         return 'my int'
    ...
    >>> s = SubClass2()
    >>> s.foo(1)
    'my int'

However, providing the register decorator with the same type will also work.
Decorating a method override with a different type (not a good idea) will register the different type and leave the base-class handler in place for the orginal type.

Method overrides can be specified on individual instances if necessary

    >>> def foo_set(obj, bar):
    ...    return 'set'
    >>> b = BaseClass()
    >>> b.foo.register(set, foo_set)
    <function foo_set at 0x000002376A3D32F0>
    >>> b.foo(set())
    'set'
    >>> b2 = BaseClass()
    >>> b2.foo(set())
    'default'

In Python 3.6 and later, for functions annotated with types, the decorator will infer the type of the first argument automatically as shown below

    >>> class BaseClassAnno(SingleDispatch):
    ...     @singledispatch
    ...     def foo(self, bar):
    ...         return 'default'
    ...
    ...     @foo.register
    ...     def foo_int(self, bar: int):
    ...         return 'int'
    ...
    >>> class SubClassAnno(BaseClassAnno):
    ...     @BaseClassAnno.foo.register
    ...     def foo_float(self, bar: float):
    ...         return 'float'

In Python 3.6 and earlier, the ``SingleDispatch`` class uses a meta-class ``SingleDispatchMeta`` to manage the dispatch registries.  However in Python 3.6 and later the ``__init_subclass__`` method is used instead.
If your class also inherits from an ABC interface you can use the ``SingleDispatchABCMeta`` metaclass in Python 3.6 and earlier.

Finally, accessing the method ``foo`` via a class will use the dispatch registry for that class

      >>> SubClass2.foo(s, 1)
      'my int'
      >>> BaseClass.foo(s, 1)
      'int'

"""

import sys
if sys.version_info[0] < 3:
    from .methoddispatch2 import *
    del methoddispatch2
elif sys.version_info >= (3, 6):
    from .methoddispatch36 import *
    del methoddispatch36
else:
    from .methoddispatch3 import *
    del methoddispatch3

__version__ = '3.0.0'
__author__ = 'Seequent'
__license__ = 'BSD'
__copyright__ = 'Copyright 2019 Seequent'
