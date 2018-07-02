#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import get_cache_token, ABCMeta
from functools import update_wrapper, _find_impl
from types import MappingProxyType
from weakref import WeakKeyDictionary

__all__ = ['singledispatch', 'register', 'SingleDispatchMeta', 'SingleDispatchABCMeta',
           'SingleDispatch', 'SingleDispatchABC']

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
        wrapper = sd_method(self, instance)
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


class sd_method(object):
    """ A singledispatch method """
    def __init__(self, s_d, instance):
        self._instance = instance
        self._s_d = s_d

    def dispatch(self, cls):
        return self._s_d.dispatch(cls)

    @property
    def registry(self):
        return self._s_d.registry

    def __call__(self, *args, **kwargs):
        if self._instance is None:
            return self.dispatch(args[1].__class__)(*args, **kwargs)
        else:
            return self.dispatch(args[0].__class__)(self._instance, *args, **kwargs)


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
        cls = super(SingleDispatchMeta, mcs).__new__(mcs, clsname, bases, attributes)
        return cls


class SingleDispatchABCMeta(SingleDispatchMeta, ABCMeta):
    pass


class SingleDispatch(metaclass=SingleDispatchMeta):
    pass


class SingleDispatchABC(metaclass=SingleDispatchABCMeta):
    pass


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
