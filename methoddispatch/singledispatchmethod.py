#!/usr/bin/env python
from abc import get_cache_token
from functools import update_wrapper, _find_impl
from types import MappingProxyType
from weakref import WeakKeyDictionary, WeakSet

__all__ = ['singledispatchmethod']

################################################################################
### singledispatchmethod() - single-dispatch generic method decorator
################################################################################


class singledispatchmethod(object):
    """Single-dispatch generic function decorator.

    Transforms a function into a generic function, which can have different
    behaviours depending upon the type of its first argument. The decorated
    function acts as the default implementation, and additional
    implementations can be registered using the register() attribute of the
    generic function.
    """
    def __init__(self, func):
        self._registry = {}
        self._classes = WeakSet()
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

    def _register(self, cls, func=None):
        """_register(cls, func) -> func

        Registers a new implementation for the given *cls* on a *generic_func*.

        """
        if func is None:
            if isinstance(cls, type):
                return lambda f: self._register(cls, f)
            func = cls
            cls = _get_class_from_annotation(cls)
        self._registry[cls] = func
        if self.cache_token is None and hasattr(cls, '__abstractmethods__'):
            self.cache_token = get_cache_token()
        self.dispatch_cache.clear()
        return func

    def __get__(self, instance, cls=None):
        me = self
        if cls is not None and cls not in self._classes:
            # unfortunately we can't rely on base classes having been processed already.
            for base in cls.mro()[::-1]:
                if base is object:
                    continue
                if base not in self._classes:
                    _fixup_class_attributes(base)
                    self._classes.add(base)
            # owners singledispatch attributes have been changed
            # which means caller may want the new attribute
            me = cls.__dict__.get(self.__name__, self)
            if not isinstance(me, singledispatchmethod):
                me = self
        wrapper = _sd_method(me, instance)
        update_wrapper(wrapper, me.func)
        return wrapper

    def __call__(self, *args, **kw):
        return self.dispatch(args[0].__class__)(*args, **kw)

    def _clear_cache(self):
        self.dispatch_cache.clear()

    def copy(self):
        new = singledispatchmethod(self.func)
        new._registry.update(self._registry)
        return new

    def get_registered_types(self):
        return [type_ for type_ in self._registry.keys() if type_ is not object]

    def register(self, cls, func=None):
        """register(cls, func=None) -> func

        Registers a new implementation for the given *cls* on a *generic_func*.

        """
        if func is None:
            if isinstance(cls, type):
                return lambda f: self.register(cls, f)
            func = cls
            cls = _get_class_from_annotation(cls)

        __overloads__ = getattr(func, '__overloads__', [])
        __overloads__.append((self.__name__, cls))
        func.__overloads__ = __overloads__
        return func


def _get_class_from_annotation(func):
    # only import inspect if annotation parsing is necessary
    import inspect
    argspec = inspect.getfullargspec(func)
    if not len(argspec.args) > 1:
        raise TypeError(f'{func!r} must have at least 2 parameters.')
    argname = argspec.args[1]
    if argname not in argspec.annotations:
        raise TypeError(
            f"Invalid first argument to `register()`: {func!r}. "
            f"Use either `@register(some_class)` or plain `@register` "
            f"on an annotated function."
        )
    cls = argspec.annotations.get(argname)
    if not isinstance(cls, type):
        raise TypeError(f"Invalid annotation for {argname!r}. {cls!r} is not a class.")
    return cls


class _sd_method(object):
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

    def register(self, cls, func=None):
        return self._s_d.register(cls, func)


def _fixup_class_attributes(cls):
    generics = []
    attributes = cls.__dict__
    patched = set()
    for base in cls.mro()[1:]:
        if base is object:
            continue
        for name, value in base.__dict__.items():
            if isinstance(value, singledispatchmethod) and name not in patched:
                if name in attributes:
                    continue
                generic = value.copy()
                setattr(cls, name, generic)
                patched.add(name)
                generics.append(generic)
    for name, value in attributes.items():
        if not callable(value) or isinstance(value, singledispatchmethod):
            continue
        if hasattr(value, '__overloads__'):
            for generic_name, cls in value.__overloads__:
                generic = attributes[generic_name]
                if cls is None:
                    generic._register(value)
                else:
                    generic._register(cls, value)
        else:  # register over-ridden methods
            for generic in generics:
                for cls, f in generic.registry.items():
                    if name == f.__name__:
                        generic._register(cls, value)
                        break
