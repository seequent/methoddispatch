# -*- coding: utf-8 -*-
"""
# methoddispatch

Python 3.4 added the ``singledispatch`` decorator to the ``functools`` standard library module.
Python 3.8 added the ``singledispatchmethod`` decorator to the ``functools`` standard library module,
however it does not allow sub-classes to modify the dispatch table independantly of the base class.

This library adds this functionality.

To define a generic method, decorate it with the ``@singledispatch`` decorator. Note that the dispatch happens on the
type of the first argument, create your function accordingly.
To add overloaded implementations to the function, use the ``register()`` method of the generic function.
It is a decorator, taking a type parameter and decorates a function implementing the operation for that type.
The ``register()`` method returns the undecorated function which enables decorator stacking,
pickling, as well as creating unit tests for each variant independently

>>> from methoddispatch import singledispatch, SingleDispatch
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

The ``register()`` method relys on ``SingleDispatch.__init_subclass__``
to create the actual dispatch table rather than adding the function directly.
This also means that (unlike functools.singledispatchmethod) two methods
with the same name cannot be registered as only the last one will be in the class dictionary.

Functions not defined in the class can be registered with a generic method using the ``add_overload`` method

>>> def nothing(obj, arg, verbose=False):
...    print('Nothing.')
>>> MyClass.fun.add_overload(type(None), nothing)

Using ``add_overload`` will affect all instances of ``MyClass`` as if it were part of the class declaration.

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

To check which implementation will the generic function choose for a given type, use the ``dispatch()`` method

>>> a.fun.dispatch(float).__qualname__
'MyClass.fun_num'
>>> a.fun.dispatch(dict).__qualname__    # note: default implementation
'MyClass.fun'

To access all registered implementations, use the read-only ``registry`` attribute

>>> a.fun.registry.keys()
dict_keys([<class 'object'>, <class 'int'>, <class 'list'>, <class 'decimal.Decimal'>, <class 'float'>, <class 'NoneType'>])
>>> a.fun.registry[float].__qualname__
'MyClass.fun_num'
>>> a.fun.registry[object].__qualname__
'MyClass.fun'

Extending the dispatch table.

Subclasses can extend the type registry of the function on the base class with their own overrides.
The ``SingleDispatch`` mixin class ensures that each subclass has it's own independant copy of the dispatch registry

>>> class SubClass(MyClass):
...     @MyClass.fun.register(str)
...     def fun_str(self, arg, verbose=False):
...         print('subclass')
...
>>> s = SubClass()
>>> s.fun('hello')
subclass
>>> b = MyClass()
>>> b.fun('hello')
hello

Overriding the dispatch table

There are two ways to override the dispatch function for a given type.
One way is to override a base-class method that is in the base class dispatch table.
Method overrides do not need to provide the ``register`` decorator again to be used in the dispatch of ``fun``

>>> class SubClass2(MyClass):
...     def fun_int(self, arg, verbose=False):
...         print('subclass2 int')
...
>>> s = SubClass2()
>>> s.fun(1)
subclass2 int

The other way is to register a method with the same type using the `register` method.

>>> class Mixin2(MyClass):
...    @MyClass.fun.register(int)
...    def fun_int_override(self, arg, verbose=False):
...        print('subclass3 int')
...
>>> s = Mixin2()
>>> s.fun(1)
subclass3 int

Note that the decorator takes precedence over the method name, so if you do something like this:

>>> class SubClass4(MyClass):
...    @MyClass.fun.register(str)
...    def fun_int(self, arg, verbose=False):
...        print('silly mistake')

then SubClass4.fun_int is used for string arguments.

>>> s = SubClass4()
>>> s.fun(1)
1
>>> s.fun('a string')
silly mistake

Method overrides can be specified on individual instances if necessary using the ``register()`` method.

>>> def fun_str(obj, arg, verbose=False):
...    print('instance str')
>>> b = MyClass()
>>> b.fun.register(str, fun_str).__qualname__
'fun_str'
>>> b.fun('hello')
instance str
>>> b2 = MyClass()
>>> b2.fun('hello')
hello

For functions annotated with types, the decorator will infer the type of the first argument automatically as shown below

>>> class MyClassAnno(SingleDispatch):
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

Note that these types are used at runtine and so concrete classes need to be used, not typing generics.

Finally, accessing the method ``fun`` via a class will use the dispatch registry for that class

>>> SubClass2.fun(s, 1)
subclass2 int
>>> MyClass.fun(s, 1)
1

You can use Mixin or multiple inheritance to add a generic method to a class, like this:

>>> class BaseClassForMixin(SingleDispatch):
...    @singledispatch
...    def foo(self, bar):
...        print('BaseClass')
...        return 'default'
...
...    @foo.register(float)
...    def foo_float(self, bar):
...        print('BaseClass')
...        return 'float'
...
>>> class Mixin1(BaseClassForMixin):
...
...    @BaseClassForMixin.foo.register(int)
...    def foo_int(self, bar):
...        print('Mixin1')
...        return 'int'
...
...    @BaseClassForMixin.foo.register(str)
...    def foo_str(self, bar):
...        print('Mixin1')
...        return 'str2'
...
>>> class Mixin2(BaseClassForMixin):
...    @BaseClassForMixin.foo.register(str)
...    def foo_str2(self, bar):
...        print('Mixin2')
...        return 'str3'
...
>>> class SubClassWithMixins(Mixin2, Mixin1):
...    def foo_float(self, bar):
...        print('SubClassWithMixins')
...        return 'float'

Note that even though ``Mixin2`` has method ``foo_str2`` it will still override ``Mixin1.foo_str`` in
the dispatch of ``foo()`` because they are both handlers for the ``str`` type and ``Mixin2`` comes before 
``Mixin1`` in the bases list.

>>> s = SubClassWithMixins()
>>> s.foo('text')
Mixin2
'str3'
>>> s.foo(1)
Mixin1
'int'
>>> s.foo(3.2)
SubClassWithMixins
'float'
"""

from ._methoddispatch import *

__version__ = '5.0.1'
__author__ = 'Seequent Ltd'
__license__ = 'BSD'
__copyright__ = 'Copyright 2023 Seequent Ltd'
