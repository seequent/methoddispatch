#!/usr/bin/env python
from _weakrefset import WeakSet
from abc import get_cache_token
from functools import update_wrapper, _find_impl
from types import MappingProxyType
from weakref import WeakKeyDictionary

__all__ = ['singledispatch']


################################################################################
### singledispatch() - single-dispatch generic function decorator
################################################################################


class singledispatch:
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

    def add_overload(self, cls, func=None):
        """add_overload(cls, func) -> func (private)

        Registers a new implementation for the given *cls* on a *generic_func*.

        """
        if func is None:
            if isinstance(cls, type):
                return lambda f: self.add_overload(cls, f)
            func = cls
            cls = _get_class_from_annotation(cls)
        self._registry[cls] = func
        if self.cache_token is None and hasattr(cls, '__abstractmethods__'):
            self.cache_token = get_cache_token()
        self.dispatch_cache.clear()
        return func

    def __get__(self, instance, owner=None):
        me = self
        if owner is not None and owner not in self._classes:
            # unfortunately we can't rely on base classes having been processed already.
            for base in owner.mro()[::-1]:
                if base is object:
                    continue
                if base not in self._classes:
                    _fixup_class_attributes(base)
                    self._classes.add(base)
            # owners singledispatch attributes have been changed
            # which means caller may want the new attribute
            me = owner.__dict__.get(self.__name__, self)
            if not isinstance(me, singledispatch):
                me = self
        if instance is not None:
            wrapper = BoundSDMethod(me, instance)
        elif owner is not None:
            wrapper = UnboundSDMethod(me, owner)
        else:
            return me
        update_wrapper(wrapper, me.func)
        return wrapper

    def __call__(self, *args, **kw):
        return self.dispatch(args[0].__class__)(*args, **kw)

    def _clear_cache(self):
        self.dispatch_cache.clear()

    def copy(self):
        new = singledispatch(self.func)
        new.__name__ = self.__name__
        new._registry.update(self._registry)
        new._classes = self._classes  # borg
        return new

    def get_registered_types(self):
        return [type_ for type_ in self._registry.keys() if type_ is not object]

    def register(self, cls, func=None):
        """ Decorator for methods to register an overload on generic method.
        :param cls: is the type to register or may be omitted or None to use the annotated parameter type.
        """
        if func is None:
            if isinstance(cls, type):
                return lambda f: self.register(cls, f)
            func = cls
            cls = _get_class_from_annotation(cls)

        overloads = getattr(func, '_overloads', [])
        overloads.append((self.__name__, cls))
        func._overloads = overloads
        return func


def _get_class_from_annotation(func):
    # only import inspect if annotation parsing is necessary
    import inspect
    argspec = inspect.getfullargspec(func)
    assert len(argspec.args) > 1, f'{func!r} must have at least 2 parameters.'
    argname = argspec.args[1]
    if argname not in argspec.annotations:
        raise TypeError(
            f"Invalid first argument to `register()`: {func!r}. "
            f"Use either `@register(some_class)` or plain `@register` "
            f"on an annotated function."
        )
    cls = argspec.annotations.get(argname)
    assert isinstance(cls, type), (
        f"Invalid annotation for {argname!r}. {cls!r} is not a class."
    )
    return cls


class BoundSDMethod:
    """ A bound singledispatch method """

    def __init__(self, s_d, instance):
        self._instance = instance
        self._s_d = s_d
        self._instance_sd = instance.__dict__.get('__' + s_d.__name__, None)

    def copy(self):
        if self._instance_sd is not None:
            return self._instance_sd.copy()
        else:
            return self._s_d.copy()

    def dispatch(self, cls):
        if self._instance_sd is not None:
            return self._instance_sd.dispatch(cls)
        else:
            return self._s_d.dispatch(cls)

    @property
    def registry(self):
        if self._instance_sd is not None:
            return self._instance_sd.registry
        else:
            return self._s_d.registry

    def __call__(self, *args, **kwargs):
        return self.dispatch(args[0].__class__)(self._instance, *args, **kwargs)

    def register(self, cls, func=None):
        if self._instance_sd is None:
            self._instance.__dict__['__' + self.__name__] = self._instance_sd = self._s_d.copy()
        return self._instance_sd.add_overload(cls, func)

    def get_registered_types(self):
        if self._instance_sd is not None:
            return self._instance_sd.get_registered_types()
        else:
            return self._s_d.get_registered_types()


class UnboundSDMethod:
    """ An unbound singledispatch method """

    def __init__(self, s_d, cls):
        self._s_d = s_d

    def copy(self):
        return self._s_d.copy()

    def dispatch(self, cls):
        return self._s_d.dispatch(cls)

    @property
    def registry(self):
        return self._s_d.registry

    def __call__(self, *args, **kwargs):
        return self.dispatch(args[1].__class__)(*args, **kwargs)

    def register(self, cls, func=None):
        return self._s_d.register(cls, func)

    def get_registered_types(self):
        return self._s_d.get_registered_types()

    def add_overload(self, cls, func=None):
        self._s_d.add_overload(cls, func)


def _fixup_class_attributes(cls):
    """ replaces/adds any singledispatch attributes from base classes into this class so that the dispatch tables
    are kept independant.
    """
    generics = []
    attributes = cls.__dict__
    patched = set()
    for base in cls.mro()[1:]:
        if base is object:
            continue
        for name, value in base.__dict__.items():
            if isinstance(value, singledispatch) and name not in patched:
                if name in attributes:
                    continue
                generic = value.copy()
                setattr(cls, name, generic)
                patched.add(name)
                generics.append(generic)
    for name, value in attributes.items():
        if not callable(value) or isinstance(value, singledispatch):
            continue
        if hasattr(value, '_overloads'):
            for generic_name, cls in value._overloads:
                generic = attributes[generic_name]
                if cls is None:
                    generic.add_overload(value)
                else:
                    generic.add_overload(cls, value)
        else:  # register over-ridden methods
            for generic in generics:
                for cls, f in generic.registry.items():
                    if name == f.__name__:
                        generic.add_overload(cls, value)
                        break
