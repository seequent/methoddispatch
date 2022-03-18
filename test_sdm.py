# -*- coding: utf-8 -*-
import unittest

from singledispatchmethod import singledispatchmethod


def instance_foo(self, bar):
    return 'instance'


class BaseClass:
    @singledispatchmethod
    def foo(self, bar):
        return 'default'

    @foo.register(int)
    def foo_int(self, bar):
        return 'int'

    @foo.register(set)
    def foo_set(self, bar):
        return 'set'

    @singledispatchmethod
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


class MidClass(BaseClass):
    @BaseClass.foo.register(float)
    def foo_float(self, bar):
        return 'mid float'

    @BaseClass.foo.register(str)
    def foo_str(self, bar):
        return 'mid str'


class SubMidClass(MidClass):
    @SubClass.foo.register(list)
    def foo_list(self, bar):
        return 'list'


class AnnClass(BaseClass):
    @BaseClass.foo.register
    def foo_int(self, bar: int):
        return 'an int'


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

    def test_sub_mid_class(self):
        # this checks that we are using MRO and not just bases.
        s = SubMidClass()
        self.assertEqual(s.foo([]), 'list')
        self.assertEqual(s.foo(1), 'int')
        self.assertEqual(s.foo(1.0), 'mid float')
        self.assertEqual(s.foo(''), 'mid str')

    def test_independence(self):
        b = BaseClass()
        s = SubClass()
        self.assertEqual(b.foo(1.0), 'default')
        self.assertEqual(s.foo(1.0), 'float')

    def test_override(self):
        class SubClass2(BaseClass):
            def foo(self, bar):
                return None
        s = SubClass2()
        self.assertEqual(None, s.foo('bar'))
        self.assertEqual(None, s.foo(set()))

    def test_override_super(self):
        class SubClass2(BaseClass):
            def foo(self, bar):
                return super().foo(bar)
        s = SubClass2()
        self.assertEqual('default', s.foo('bar'))
        self.assertEqual('set', s.foo(set()))

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

    def test_annotations(self):
        c = AnnClass()
        self.assertEqual(c.foo(1), 'an int')

    def test_wrong_annotation(self):
        with self.assertRaises(TypeError):
            class AnnClass2(BaseClass):
                @BaseClass.foo.register
                def foo_int(self, bar, baz: str):
                    return 'an int'


if __name__ == '__main__':
    unittest.main()
