# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from abc import ABCMeta
from functools import update_wrapper
from UserDict import UserDict
from weakref import WeakKeyDictionary
import warnings


class MappingProxyType(UserDict):
    def __init__(self, data):
        UserDict.__init__(self)
        self.data = data


def get_cache_token():
    return ABCMeta._abc_invalidation_counter


__all__ = ['singledispatch', 'register', 'SingleDispatchMeta', 'SingleDispatchABCMeta',
           'SingleDispatch', 'SingleDispatchABC']


def _c3_merge(sequences):
    """Merges MROs in *sequences* to a single MRO using the C3 algorithm.

    Adapted from http://www.python.org/download/releases/2.3/mro/.

    """
    result = []
    while True:
        sequences = [s for s in sequences if s]   # purge empty sequences
        if not sequences:
            return result
        for s1 in sequences:   # find merge candidates among seq heads
            candidate = s1[0]
            for s2 in sequences:
                if candidate in s2[1:]:
                    candidate = None
                    break      # reject the current head, it appears later
            else:
                break
        if not candidate:
            raise RuntimeError("Inconsistent hierarchy")
        result.append(candidate)
        # remove the chosen candidate
        for seq in sequences:
            if seq[0] == candidate:
                del seq[0]


def _c3_mro(cls, abcs=None):
    """Computes the method resolution order using extended C3 linearization.

    If no *abcs* are given, the algorithm works exactly like the built-in C3
    linearization used for method resolution.

    If given, *abcs* is a list of abstract base classes that should be inserted
    into the resulting MRO. Unrelated ABCs are ignored and don't end up in the
    result. The algorithm inserts ABCs where their functionality is introduced,
    i.e. issubclass(cls, abc) returns True for the class itself but returns
    False for all its direct base classes. Implicit ABCs for a given class
    (either registered or inferred from the presence of a special method like
    __len__) are inserted directly after the last ABC explicitly listed in the
    MRO of said class. If two implicit ABCs end up next to each other in the
    resulting MRO, their ordering depends on the order of types in *abcs*.

    """
    for i, base in enumerate(reversed(cls.__bases__)):
        if hasattr(base, '__abstractmethods__'):
            boundary = len(cls.__bases__) - i
            break   # Bases up to the last explicit ABC are considered first.
    else:
        boundary = 0
    abcs = list(abcs) if abcs else []
    explicit_bases = list(cls.__bases__[:boundary])
    abstract_bases = []
    other_bases = list(cls.__bases__[boundary:])
    for base in abcs:
        if issubclass(cls, base) and not any(
                issubclass(b, base) for b in cls.__bases__
        ):
            # If *cls* is the class that introduces behaviour described by
            # an ABC *base*, insert said ABC to its MRO.
            abstract_bases.append(base)
    for base in abstract_bases:
        abcs.remove(base)
    explicit_c3_mros = [_c3_mro(base, abcs=abcs) for base in explicit_bases]
    abstract_c3_mros = [_c3_mro(base, abcs=abcs) for base in abstract_bases]
    other_c3_mros = [_c3_mro(base, abcs=abcs) for base in other_bases]
    return _c3_merge(
        [[cls]] +
        explicit_c3_mros + abstract_c3_mros + other_c3_mros +
        [explicit_bases] + [abstract_bases] + [other_bases]
    )


def _compose_mro(cls, types):
    """Calculates the method resolution order for a given class *cls*.

    Includes relevant abstract base classes (with their respective bases) from
    the *types* iterable. Uses a modified C3 linearization algorithm.

    """
    bases = set(cls.__mro__)
    # Remove entries which are already present in the __mro__ or unrelated.

    def is_related(typ):
        return (typ not in bases and hasattr(typ, '__mro__')
                and issubclass(cls, typ))
    types = [n for n in types if is_related(n)]
    # Remove entries which are strict bases of other entries (they will end up
    # in the MRO anyway.

    def is_strict_base(typ):
        for other in types:
            if typ != other and typ in other.__mro__:
                return True
        return False
    types = [n for n in types if not is_strict_base(n)]
    # Subclasses of the ABCs in *types* which are also implemented by
    # *cls* can be used to stabilize ABC ordering.
    type_set = set(types)
    mro = []
    for typ in types:
        found = []
        for sub in typ.__subclasses__():
            if sub not in bases and issubclass(cls, sub):
                found.append([s for s in sub.__mro__ if s in type_set])
        if not found:
            mro.append(typ)
            continue
        # Favor subclasses with the biggest number of useful bases
        found.sort(key=len, reverse=True)
        for sub in found:
            for subcls in sub:
                if subcls not in mro:
                    mro.append(subcls)
    return _c3_mro(cls, abcs=mro)


def _find_impl(cls, registry):
    """Returns the best matching implementation from *registry* for type *cls*.

    Where there is no registered implementation for a specific type, its method
    resolution order is used to find a more generic implementation.

    Note: if *registry* does not contain an implementation for the base
    *object* type, this function may return None.

    """
    mro = _compose_mro(cls, registry.keys())
    match = None
    for t in mro:
        if match is not None:
            # If *match* is an implicit ABC but there is another unrelated,
            # equally matching implicit ABC, refuse the temptation to guess.
            if (t in registry and t not in cls.__mro__
                    and match not in cls.__mro__ and not issubclass(match, t)):
                raise RuntimeError("Ambiguous dispatch: {0} or {1}".format(
                    match, t))
            break
        if t in registry:
            match = t
    return registry.get(match)


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

    def add_overload(self, cls, func=None):
        """add_overload(cls, func) -> func (private)

        Registers a new implementation for the given *cls* on a *generic_func*.

        """
        if func is None:
            return lambda f: self.add_overload(cls, f)
        self._registry[cls] = func
        if self.cache_token is None and hasattr(cls, '__abstractmethods__'):
            self.cache_token = get_cache_token()
        self.dispatch_cache.clear()
        return func

    def __get__(self, instance, owner=None):
        if owner is not None and not isinstance(owner, SingleDispatchMeta):
            raise ValueError('singledispatch can only be used on methods of SingleDispatch subclasses')
        if instance is not None:
            wrapper = BoundSDMethod(self, instance)
        elif owner is not None:
            wrapper = UnboundSDMethod(self)
        else:
            return self
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

    def register(self, cls, func=None):
        """ Decorator for methods to register an overload on generic method.
        :param cls: is the type to register or may be omitted or None to use the annotated parameter type.
        """
        if func is None:
            return lambda f: self.register(cls, f)

        overloads = getattr(func, '_overloads', [])
        overloads.append((self.__name__, cls))
        func._overloads = overloads
        return func


class BoundSDMethod(object):
    """ A bounf singledispatch method """

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

    def __init__(self, s_d):
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
    generics = []
    attributes = cls.__dict__
    patched = set()
    for base in cls.mro()[1:]:
        if isinstance(base, SingleDispatchMeta):
            for name, value in base.__dict__.items():
                if isinstance(value, singledispatch) and name not in patched:
                    if name in attributes:
                        raise RuntimeError('Cannot override generic function.  '
                                           'Try @{name}.register(object) instead.'.format(name=name))
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
                generic.add_overload(cls, value)
        else:  # register over-ridden methods
            for generic in generics:
                for cls, f in generic.registry.items():
                    if name == f.__name__:
                        generic.add_overload(cls, value)
                        break


class SingleDispatchMeta(type):
    """Metaclass for objects with single dispatch methods.
    The primary purpose is to copy the registry and dispatch lists
    so that registered types on sub-classes do not modify the base class.
    """
    def __new__(mcs, clsname, bases, attributes):
        cls = super(SingleDispatchMeta, mcs).__new__(mcs, clsname, bases, attributes)
        _fixup_class_attributes(cls)
        return cls


class SingleDispatchABCMeta(SingleDispatchMeta, ABCMeta):
    pass


class SingleDispatch(object):
    __metaclass__ = SingleDispatchMeta


class SingleDispatchABC(object):
    __metaclass__ = SingleDispatchABCMeta


def register(name, cls):
    """ Decorator for methods on a sub-class to register an overload on a base-class generic method.
    :param name: is the name of the generic method on the base class, or the unbound method itself
    :param cls: is the type to register
    """
    warnings.warn('Use @BaseClass.method.register() instead of register', DeprecationWarning, stacklevel=2)
    name = getattr(name, '__name__', name)  # __name__ exists on sd_method courtesy of update_wrapper
    def wrapper(func):
        overloads = getattr(func, '_overloads', [])
        overloads.append((name, cls))
        func._overloads = overloads
        return func
    return wrapper
