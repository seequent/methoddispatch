#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import get_cache_token
from functools import update_wrapper, _find_impl
from types import MappingProxyType
from weakref import WeakKeyDictionary

__all__ = ['singledispatch', 'register', 'SingleDispatch', 'SingleDispatchABC']

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
        """generic_func.register(cls, func) -> func

        Registers a new implementation for the given *cls* on a *generic_func*.

        """
        if func is None:
            if isinstance(cls, type):
                return lambda f: self.register(cls, f)
            ann = getattr(cls, '__annotations__', {})
            if not ann:
                raise TypeError(
                    f"Invalid first argument to `register()`: {cls!r}. "
                    f"Use either `@register(some_class)` or plain `@register` "
                    f"on an annotated function."
                )
            func = cls

            # only import typing if annotation parsing is necessary
            from typing import get_type_hints
            argname, cls = next(iter(get_type_hints(func).items()))
            assert isinstance(cls, type), (
                f"Invalid annotation for {argname!r}. {cls!r} is not a class."
            )
        self._registry[cls] = func
        if self.cache_token is None and hasattr(cls, '__abstractmethods__'):
            self.cache_token = get_cache_token()
        self.dispatch_cache.clear()
        return func

    def __get__(self, instance, cls=None):
        if cls is not None and not issubclass(cls, SingleDispatch):
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


class SingleDispatch(object):
    """
    Base or mixin class to enable single dispatch on methods.
    """
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        generics = []
        attributes = cls.__dict__
        for base in cls.mro()[1:]:
            if issubclass(base, SingleDispatch):
                for name, value in base.__dict__.items():
                    if isinstance(value, singledispatch):
                        if name in attributes:
                            raise RuntimeError('Cannot override generic function.  '
                                               'Try @register("{}", object) instead.'.format(name))
                        generic = value.copy()
                        setattr(cls, name, generic)
                        generics.append(generic)
        for name, value in attributes.items():
            if not callable(value) or isinstance(value, singledispatch):
                continue
            if hasattr(value, 'overloads'):
                for generic_name, cls in value.overloads:
                    generic = attributes[generic_name]
                    if cls is None:
                        generic.register(value)
                    else:
                        generic.register(cls, value)
            else:  # register over-ridden methods
                for generic in generics:
                    for cls, f in generic.registry.items():
                        if name == f.__name__:
                            generic.register(cls, value)
                            break


SingleDispatchABC = SingleDispatch  # for backwards compatibility


def register(name, cls=None):
    """ Decorator for methods on a sub-class to register an overload on a base-class generic method.
    :param name: is the name of the generic method on the base class
    :param cls: is the type to register or may be omitted or None to use the annotated parameter type.
    """
    def wrapper(func):
        overloads = getattr(func, 'overloads', [])
        overloads.append((name, cls))
        func.overloads = overloads
        return func
    return wrapper
