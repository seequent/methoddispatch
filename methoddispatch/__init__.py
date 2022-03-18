# -*- coding: utf-8 -*-
"""
methoddispatch
==============


Python 3.4 added the ``singledispatch`` decorator to the ``functools`` standard library module.
Python 3.8 added the ``singledispatchmethod`` decorator to the ``functools`` standard library module,
however it does not allow sub-classes to modify the dispatch table independantly of the base class.

This library adds this functionality.

To define a generic method , decorate it with the ``@singledispatch`` decorator. Note that the dispatch happens on the type of the first argument, create your function accordingly.
To add overloaded implementations to the function, use the ``register()`` attribute of the generic function.
It is a decorator, taking a type parameter and decorating a function implementing the operation for that type.
The ``register()`` attribute returns the undecorated function which enables decorator stacking, pickling, as well as creating unit tests for each variant independently

>>> from methoddispatch import singledispatch
>>> from decimal import Decimal
>>> class MyClass:
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

The ``register()`` attribute only works inside a class statement as the dispatch table is assembled
from class attributes.  This also means that (unlike functools.singledispatch) two methods
with the same name cannot be registered as only the last one will be in the class dictionary.

Functions not defined in the class can be registered using the ``add_overload`` attribute.

>>> def nothing(obj, arg, verbose=False):
...    print('Nothing.')
>>> MyClass.fun.add_overload(type(None), nothing)

When called, the generic function dispatches on the type of the first argument

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

To check which implementation will the generic function choose for a given type, use the ``dispatch()`` attribute

>>> a.fun.dispatch(float)
<function MyClass.fun_num at 0x1035a2840>
>>> a.fun.dispatch(dict)    # note: default implementation
<function MyClass.fun at 0x103fe0000>

To access all registered implementations, use the read-only ``registry`` attribute

>>> a.fun.registry.keys()
dict_keys([<class 'NoneType'>, <class 'int'>, <class 'object'>,
          <class 'decimal.Decimal'>, <class 'list'>,
          <class 'float'>])
>>> a.fun.registry[float]
<function MyClass.fun_num at 0x1035a2840>
>>> a.fun.registry[object]
<function MyClass.fun at 0x103fe0000>

Subclasses can extend the type registry of the function on the base class with their own overrides.
Each subclass has it's own independant copy of the dispatch registry

>>> class SubClass(MyClass):
...     @MyClass.fun.register(str)
...     def fun_str(self, arg, verbose=False):
...         print('str')
...
>>> s = SubClass()
>>> s.fun('hello')
str
>>> b = MyClass()
>>> b.fun('hello')
hello

Method overrides do not need to provide the ``register`` decorator again to be used in the dispatch of ``fun``

>>> class SubClass2(MyClass):
...     def fun_int(self, arg, verbose=False):
...         print('subclass int')
...
>>> s = SubClass2()
>>> s.fun(1)
subclass int

However, providing the register decorator with the same type will also work.
Decorating a method override with a different type (not a good idea) will register the different type and leave the base-class handler in place for the orginal type.

Method overrides can be specified on individual instances if necessary

>>> def fun_str(obj, arg, verbose=False):
...    print('str')
>>> b = MyClass()
>>> b.fun.register(str, fun_str)
<function fun_str at 0x000002376A3D32F0>
>>> b.fun('hello')
str
>>> b2 = MyClass()
>>> b2.fun('hello')
hello

For functions annotated with types, the decorator will infer the type of the first argument automatically as shown below

>>> class MyClassAnno:
...     @singledispatch
...     def fun(self, arg):
...         print('default')
...
...     @fun.register
...     def fun_int(self, arg: int):
...         print('int')
...
>>> class SubClassAnno(MyClassAnno):
...     @MyClassAnno.fun.register
...     def fun_float(self, arg: float):
...         print('float')

Finally, accessing the method ``fun`` via a class will use the dispatch registry for that class

>>> SubClass2.fun(s, 1)
subclass int
>>> MyClass.fun(s, 1)
1

"""

from ._methoddispatch import *

__version__ = '4.0.0'
__author__ = 'Seequent'
__license__ = 'BSD'
__copyright__ = 'Copyright 2022 Seequent'
