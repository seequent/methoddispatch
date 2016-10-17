#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    ==============
    methoddispatch 1.0.0
    ==============

    `PEP 443 <http://www.python.org/dev/peps/pep-0443/>`_ proposed to expose
    a mechanism in the ``functools`` standard library module in Python 3.4
    that provides a simple form of generic programming known as
    single-dispatch generic functions.

    This library extends this functionality to instance methods (and works for functions too)

    To define a generic method , decorate it with the ``@singledispatch``
    decorator. Note that the dispatch happens on the type of the first
    argument, create your function accordingly::

      >>> from methoddispatch import singledispatch
      >>> @singledispatch
      ... def fun(arg, verbose=False):
      ...     if verbose:
      ...         print("Let me just say,", end=" ")
      ...     print(arg)

    To add overloaded implementations to the function, use the
    ``register()`` attribute of the generic function. It is a decorator,
    taking a type parameter and decorating a function implementing the
    operation for that type::

      >>> @fun.register(int)
      ... def _(arg, verbose=False):
      ...     if verbose:
      ...         print("Strength in numbers, eh?", end=" ")
      ...     print(arg)
      ...
      >>> @fun.register(list)
      ... def _(arg, verbose=False):
      ...     if verbose:
      ...         print("Enumerate this:")
      ...     for i, elem in enumerate(arg):
      ...         print(i, elem)

    To enable registering lambdas and pre-existing functions, the
    ``register()`` attribute can be used in a functional form::

      >>> def nothing(arg, verbose=False):
      ...     print("Nothing.")
      ...
      >>> fun.register(type(None), nothing)
      <function nothing at 0x03D3FDB0>

    The ``register()`` attribute returns the undecorated function which
    enables decorator stacking, pickling, as well as creating unit tests for
    each variant independently::

      >>> from decimal import Decimal
      >>> @fun.register(float)
      ... @fun.register(Decimal)
      ... def fun_num(arg, verbose=False):
      ...     if verbose:
      ...         print("Half of your number:", end=" ")
      ...     print(arg / 2)
      ...
      >>> fun_num is fun
      False

    When called, the generic function dispatches on the type of the first
    argument::

      >>> fun("Hello, world.")
      Hello, world.
      >>> fun("test.", verbose=True)
      Let me just say, test.
      >>> fun(42, verbose=True)
      Strength in numbers, eh? 42
      >>> fun(['spam', 'spam', 'eggs', 'spam'], verbose=True)
      Enumerate this:
      0 spam
      1 spam
      2 eggs
      3 spam
      >>> fun(None)
      Nothing.
      >>> fun(1.23)
      0.615

    Where there is no registered implementation for a specific type, its
    method resolution order is used to find a more generic implementation.
    The original function decorated with ``@singledispatch`` is registered
    for the base ``object`` type, which means it is used if no better
    implementation is found.

    To check which implementation will the generic function choose for
    a given type, use the ``dispatch()`` attribute::

      >>> fun.dispatch(float)
      <function fun_num at 0x1035a2840>
      >>> fun.dispatch(dict)    # note: default implementation
      <function fun at 0x103fe0000>

    To access all registered implementations, use the read-only ``registry``
    attribute::

      >>> fun.registry.keys()
      dict_keys([<class 'NoneType'>, <class 'int'>, <class 'object'>,
                <class 'decimal.Decimal'>, <class 'list'>,
                <class 'float'>])
      >>> fun.registry[float]
      <function fun_num at 0x1035a2840>
      >>> fun.registry[object]
      <function fun at 0x103fe0000>

    Decorating class methods requires the class have ``SingleDispatchMeta`` as
    a metaclass.  The metaclass ensures that the dipatch registry of
    sub-classes do not affect instances of the base class::

      >>> class BaseClass(metaclass=SingleDispatchMeta):
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
      Because the ``foo`` function is not in scope, the ``register`` decorator must be used instead::

      >>> class SubClass(BaseClass):
      ...     @register('foo', float)
      ...     def foo_float(self, bar):
      ...         return 'float'
      ...
      >>> s = SubClass()
      >>> s.foo(1)
      'int'
      >>> s.foo(1.0)
      'float'
      >>> b.foo(1.0)
      'default'

      Method overrides do not need to provide the ``register`` decorator again::

      >>> class SubClass2(BaseClass):
      ...     def foo_int(self, bar):
      ...         return 'my int'
      ...
      >>> s = SubClass2()
      >>> s.foo(1)
      'my int'

      Providing the register decorator with the same type will also work.
      Decorating with a different type (not a good idea) will register the different
      type and leave the base-class handler in place for the orginal type.

      If your class also inhertits from an ABC interface you can use the SingleDispatchABCMeta metaclass instead.

      Accessing the method ``foo`` via a class will use the dispatch registry of that class::

      >>> SubClass2.foo(s, 1)
      'my int'
      >>> BaseClass.foo(s, 1)
      'int'

"""
from abc import get_cache_token, ABCMeta
from functools import update_wrapper, _find_impl
from types import MappingProxyType
from weakref import WeakKeyDictionary

__all__ = ['singledispatch', 'SingleDispatchMeta', 'SingleDispatchABCMeta', 'register']

################################################################################
### singledispatch() - single-dispatch generic function decorator
################################################################################


class singledispatch(object):
    """Single-dispatch generic function decorator.

    Transforms a function into a generic function, which can have different
    behaviours depending upon the type of its first argument. The decorated
    function acts as the default implementation, and additional
    implementations can be registered using the register() attribute of the
    generic function.
    """
    def __init__(self, func):
        self._registry = {}
        self.dispatch_cache = WeakKeyDictionary()
        self.func = func
        self.cache_token = None
        self._registry[object] = func
        self.registry = MappingProxyType(self._registry)
        update_wrapper(self, func)

    def dispatch(self, cls):
        """dispatch(cls) -> <function implementation>

        Runs the dispatch algorithm to return the best available implementation
        for the given *cls* registered on *generic_func*.

        """
        if self.cache_token is not None:
            current_token = get_cache_token()
            if self.cache_token != current_token:
                self.dispatch_cache.clear()
                self.cache_token = current_token
        try:
            impl = self.dispatch_cache[cls]
        except KeyError:
            try:
                impl = self._registry[cls]
            except KeyError:
                impl = _find_impl(cls, self._registry)
            self.dispatch_cache[cls] = impl
        return impl

    def register(self, cls, func=None):
        """register(cls, func) -> func

        Registers a new implementation for the given *cls* on a *generic_func*.
        """
        if func is None:
            return lambda f: self.register(cls, f)
        self._registry[cls] = func
        if self.cache_token is None and hasattr(cls, '__abstractmethods__'):
            self.cache_token = get_cache_token()
        self.dispatch_cache.clear()
        return func

    def __get__(self, instance, cls=None):
        if cls is not None and not isinstance(cls, SingleDispatchMeta):
            raise ValueError('singledispatch can only be used on methods of SingleDispatchMeta types')
        if instance is None:
            def wrapper(*args, **kwargs):
                return self.dispatch(args[1].__class__)(*args, **kwargs)
        else:
            def wrapper(*args, **kwargs):
                return self.dispatch(args[0].__class__)(instance, *args, **kwargs)
        update_wrapper(wrapper, self.func)
        return wrapper

    def __call__(self, *args, **kw):
        return self.dispatch(args[0].__class__)(*args, **kw)

    def _clear_cache(self):
        self.dispatch_cache.clear()

    def copy(self):
        new = singledispatch(self.func)
        new._registry.update(self._registry)
        return new

    def get_registered_types(self):
        return [type_ for type_ in self._registry.keys() if type_ is not object]


def _fixup_class_attributes(attributes, bases):
    generics = []
    for base in bases:
        if isinstance(base, SingleDispatchMeta):
            for name, value in base.__dict__.items():
                if isinstance(value, singledispatch):
                    if name in attributes:
                        raise RuntimeError('Cannot override generic function.  '
                                           'Try @register({}, object) instead.'.format(name))
                    generic = value.copy()
                    attributes[name] = generic
                    generics.append(generic)
    for name, value in attributes.items():
        if not callable(value) or isinstance(value, singledispatch):
            continue
        if hasattr(value, 'overloads'):
            for generic_name, cls in value.overloads:
                generic = attributes[generic_name]
                generic.register(cls, value)
        else:  # register over-ridden methods
            for generic in generics:
                for cls, f in generic.registry.items():
                    if name == f.__name__:
                        generic.register(cls, value)
                        break


class SingleDispatchMeta(type):
    """Metaclass for objects with single dispatch methods.
    The primary purpose is to copy the registry and dispatch lists
    so that registered types on sub-classes do not modify the base class.
    """
    def __new__(mcs, clsname, bases, attributes):
        _fixup_class_attributes(attributes, bases)
        cls = type.__new__(mcs, clsname, bases, attributes)
        return cls


class SingleDispatchABCMeta(SingleDispatchMeta, ABCMeta):
    def __new__(mcs, name, bases, namespace):
        _fixup_class_attributes(namespace, bases)
        return ABCMeta.__new__(mcs, name, bases, namespace)


def register(name, cls):
    """ Decorator for methods on a sub-class to register an overload on a base-class generic method
    name is the name of the generic method on the base class
    cls is the type to register
    """
    def wrapper(func):
        overloads = getattr(func, 'overloads', [])
        overloads.append((name, cls))
        func.overloads = overloads
        return func
    return wrapper
