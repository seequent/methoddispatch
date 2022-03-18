# -*- coding: utf-8 -*-
import unittest

import methoddispatch
from methoddispatch import singledispatch, SingleDispatch
try:
    from methoddispatch import SingleDispatchABC
except ImportError:
    SingleDispatchABC = SingleDispatch

import abc
import doctest
import sys


def instance_foo(self, bar):
    return 'instance'


class BaseClass(SingleDispatch):
    @singledispatch
    def foo(self, bar):
        return 'default'

    @foo.add_overload(int)
    def foo_int(self, bar):
        return 'int'

    @foo.register(set)
    def foo_set(self, bar):
        return 'set'

    @singledispatch
    def bar(self, bar):
        return 'default'

    @bar.register(int)
    def bar_int(self, bar):
        return 'int'


class SubClass(BaseClass):
    @BaseClass.foo.register(float)
    def foo_float(self, bar):
        return 'float'

    def foo_int(self, bar):
        return 'sub int'

    @BaseClass.foo.register(str)
    def foo_str(self, bar):
        return 'str'


class SubSubClass(SubClass):
    @SubClass.foo.register(list)
    def foo_list(self, bar):
        return 'list'

    @SubClass.foo.register(tuple)
    def foo_tuple(self, bar):
        return 'tuple'


class IFoo(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def foo(self, bar):
        pass


class MyClass(SingleDispatchABC, IFoo):
    @singledispatch
    def foo(self, bar):
        return 'my default'

    @foo.register(int)
    def foo_int(self, bar):
        return 'my int'

    @foo.register(list)
    def foo_list(self, bar):
        return 'my list'


class TestMethodDispatch(unittest.TestCase):
    def test_base_class(self):
        b = BaseClass()
        self.assertEqual(b.foo('text'), 'default')
        self.assertEqual(b.foo(1), 'int')
        self.assertEqual(b.foo(set()), 'set')
        self.assertEqual(b.foo(1.0), 'default')
        self.assertEqual(b.bar(1.0), 'default')
        self.assertEqual(b.bar(1), 'int')

    def test_sub_class(self):
        s = SubClass()
        self.assertEqual(s.foo([]), 'default')
        self.assertEqual(s.foo(1), 'sub int')
        self.assertEqual(s.foo(1.0), 'float')
        self.assertEqual(s.foo(''), 'str')

    def test_sub_sub_class(self):
        # this checks that we are using MRO and not just bases.
        s = SubSubClass()
        self.assertEqual(s.foo([]), 'list')
        self.assertEqual(s.foo(1), 'sub int')
        self.assertEqual(s.foo(1.0), 'float')
        self.assertEqual(s.foo(''), 'str')

    def test_independence(self):
        b = BaseClass()
        s = SubClass()
        self.assertEqual(b.foo(1.0), 'default')
        self.assertEqual(s.foo(1.0), 'float')

    def test_instance_register(self):
        b = BaseClass()
        b2 = BaseClass()
        b.foo.register(float, instance_foo)
        self.assertEqual(BaseClass.foo(b, 1.0), 'default')
        self.assertEqual(b.foo(1.0), 'instance')
        self.assertEqual(b2.foo(1.0), 'default')

    def test_attempted_override(self):
        with self.assertRaises(RuntimeError):
            class SubClass2(BaseClass):
                def foo(self, bar):
                    pass

    def test_abc_interface_support(self):
        m = MyClass()
        self.assertEqual('my default', m.foo('text'))
        self.assertEqual('my int', m.foo(1))
        self.assertEqual('my list', m.foo([]))

    def test_class_access(self):
        s = SubClass()
        self.assertEqual(BaseClass.foo(s, 1), 'int')
        self.assertEqual(SubClass.foo(s, 1), 'sub int')

    def test_class_extra_attributes(self):
        """ Check that dispatch and registry attributes are accessible """
        self.assertTrue(hasattr(SubClass.foo, 'dispatch'))
        self.assertTrue(hasattr(SubClass.foo, 'registry'))
        self.assertIs(SubClass.foo.dispatch(float), SubClass.__dict__['foo_float'])
        self.assertEqual(set(SubClass.foo.registry.keys()), set([float, object, set, int, str]))

    def test_instance_extra_attributes(self):
        """ Check that dispatch and registry attributes are accessible """
        s = SubClass()
        self.assertTrue(hasattr(s.foo, 'dispatch'))
        self.assertTrue(hasattr(s.foo, 'registry'))
        self.assertIs(s.foo.dispatch(float), SubClass.__dict__['foo_float'])
        self.assertEqual(set(s.foo.registry.keys()), set([float, object, set, int, str]))

    def test_docs(self):
        num_failures, num_tests = doctest.testmod(methoddispatch, name='methoddispatch')
        # we expect 6 failures as a result like <function fun_num at 0x1035a2840> is not deterministic
        self.assertLessEqual(num_failures, 6)
        self.assertGreaterEqual(num_tests, 30)

    def test_annotations(self):
        class AnnClass(BaseClass):
            @BaseClass.foo.register
            def foo_int(self, bar: int):
                return 'an int'

        c = AnnClass()
        self.assertEqual(c.foo(1), 'an int')

        def foo_float(obj: AnnClass, bar: float):
            return 'float'

        c.foo.register(foo_float)
        self.assertEqual(c.foo(1.23), 'float')


if __name__ == '__main__':
    unittest.main()
