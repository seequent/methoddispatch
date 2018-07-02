# -*- coding: utf-8 -*-
import unittest

import methoddispatch
from methoddispatch import singledispatch, register, SingleDispatch, SingleDispatchABC
import abc
import doctest
import six
import sys


class BaseClass(SingleDispatch):
    @singledispatch
    def foo(self, bar):
        return 'default'

    @foo.register(int)
    def foo_int(self, bar):
        return 'int'


class SubClass(BaseClass):
    @register('foo', float)
    def foo_float(self, bar):
        return 'float'

    def foo_int(self, bar):
        return 'sub int'


@six.add_metaclass(abc.ABCMeta)
class IFoo(object):
    @abc.abstractmethod
    def foo(self, bar):
        pass


class MyClass(IFoo, SingleDispatchABC):
    @singledispatch
    def foo(self, bar):
        return 'my default'

    @foo.register(int)
    def foo_int(self, bar):
        return 'my int'


@singledispatch
def func(a):
    return 'default'


@func.register(bool)
def func_bool(a):
    return not a


class TestMethodDispatch(unittest.TestCase):
    def test_base_class(self):
        b = BaseClass()
        self.assertEqual(b.foo('text'), 'default')
        self.assertEqual(b.foo(1), 'int')
        self.assertEqual(b.foo(1.0), 'default')

    def test_sub_class(self):
        s = SubClass()
        self.assertEqual(s.foo('text'), 'default')
        self.assertEqual(s.foo(1), 'sub int')
        self.assertEqual(s.foo(1.0), 'float')

    def test_independence(self):
        b = BaseClass()
        s = SubClass()
        self.assertEqual(b.foo(1.0), 'default')
        self.assertEqual(s.foo(1.0), 'float')

    def test_attempted_override(self):
        with self.assertRaises(RuntimeError):
            class SubClass2(BaseClass):
                def foo(self, bar):
                    pass

    def test_abc_interface_support(self):
        m = MyClass()
        self.assertEqual(m.foo('text'), 'my default')
        self.assertEqual(m.foo(1), 'my int')

    def test_pure_funcs(self):
        self.assertEqual('default', func(self))
        self.assertEqual(False, func(True))
        self.assertEqual(True, func(False))

    def test_class_access(self):
        s = SubClass()
        self.assertEqual(BaseClass.foo(s, 1), 'int')
        self.assertEqual(SubClass.foo(s, 1), 'sub int')

    @unittest.skipIf(six.PY2, 'docs are in python3 syntax')
    def test_docs(self):
        num_failures, num_tests = doctest.testmod(methoddispatch, name='methoddispatch')
        # we expect 6 failures as a result like <function fun_num at 0x1035a2840> is not deterministic
        self.assertEqual(num_failures, 6)
        self.assertGreater(num_tests, 30)

    @unittest.skipIf(sys.version_info < (3, 7), 'docs are in python3 syntax')
    def test_annotations(self):
        exec(py_37_tests)


py_37_tests = """
def test_annotations(self):
    class AnnClass(BaseClass):
        @register('foo')
        def foo_int(self, bar: int):
            return 'ann int'

    c = AnnClass()
    self.assertEqual(c.foo(1), 'ann int')

test_annotations(self)
"""
