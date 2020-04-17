# Many of these tests come from the CPython 3.8 stdlib test suite,
# especially the `test_getitem` and similar methods of
# `seq_tests.CommonTest` and `list_tests.CommonTest`. It does require
# a few changes, but the goal is for the changes to be as small as
# possible, so new stdlib test diffs can be pulled in easily.

from collections.abc import Sequence, MutableSequence, Mapping, MutableMapping
import sys
import unittest

from collectionhelpers import mapping_helper, sequence_helper

@mapping_helper
class FrozenKeyDict(Mapping):
    def __new__(cls, *args, **kwargs):
        self = super(FrozenKeyDict, cls).__new__(cls)
        self._dict = dict(*args, **kwargs)
        return self
    def __getitem__(self, key):
        return self._dict[key]
    def __iter__(self):
        return iter(self._dict)
    def __len__(self):
        return len(self._dict)
    def __missing__(self, key):
        if isinstance(key, Exception):
            raise key
        elif isinstance(key, type) and issubclass(key, Exception):
            raise key()
        return key
    def __repr__(self):
        return f"{type(self).__name__}({self._dict})"

class FrozenDictTest(unittest.TestCase):
    type2test = FrozenKeyDict
    abc = Mapping

    def test_decorate(self):
        class M:
            __getitem__ = 42
            __setitem__ = 42
            __delitem__ = 42
            __iter__ = 42
            __len__ = 42
            __contains__ = 42
            get = 42
        self.assertRaises(TypeError, mapping_helper, M)
        self.abc.register(M)
        M = mapping_helper(M)
        self.assertIsInstance(M(), self.abc)

        class N:
            pass
        self.abc.register(N)
        self.assertRaises(AttributeError, mapping_helper, N)

        @mapping_helper
        class O(self.abc):
            __getitem__ = 42
            __setitem__ = 42
            __delitem__ = 42
            __iter__ = 42
            __len__ = 42
            __contains__ = 42
            get = 42
        self.assertIsInstance(O(), self.abc)
        
    def test_keys(self):
        d = self.type2test({'a': 'b'})
        k = d.keys()
        self.assertIn('a', k)
        self.assertNotIn('b', k)
        
    def test_contains(self):
        d = self.type2test({'a': 'b'})
        self.assertIn('a', d)
        self.assertNotIn('b', d)

    def test_getitem_immutable(self):
        d = self.type2test({'a': 'b'})
        self.assertEqual(d['a'], 'b')
        self.assertEqual(d['b'], 'b')
        self.assertRaises(RuntimeError, d.__getitem__, RuntimeError)

        class Exc(Exception): pass
        
        class BadEq(object):
            def __eq__(self, other):
                raise Exc()
            def __hash__(self):
                return 24

        x = BadEq()
        d = self.type2test({x: 42})
        self.assertEqual(d[23], 23)
        self.assertRaises(Exc, d.__getitem__, BadEq())

        class BadHash(object):
            fail = False
            def __hash__(self):
                if self.fail:
                    raise Exc()
                else:
                    return 42

        x = BadHash()
        d = self.type2test({'x': 42})
        x.fail = True
        self.assertEqual(d[23], 23)
        self.assertRaises(Exc, d.__getitem__, x)

@mapping_helper
class KeyDict(MutableMapping):
    def __new__(cls, *args, **kwargs):
        self = super(KeyDict, cls).__new__(cls)
        self._dict = dict(*args, **kwargs)
        return self
    def __getitem__(self, key):
        return self._dict[key]
    def __delitem__(self, key):
        del self._dict[key]
    def __setitem__(self, key, value):
        self._dict[key] = value
    def __iter__(self):
        return iter(self._dict)
    def __len__(self):
        return len(self._dict)
    def __missing__(self, key):
        if isinstance(key, Exception):
            raise key
        elif isinstance(key, type) and issubclass(key, Exception):
            raise key()
        return key
    def __repr__(self):
        return f"{type(self).__name__}({self._dict})"

class DictTest(FrozenDictTest):
    type2test = KeyDict
    abc = MutableMapping

    def test_getitem_mutable(self):
        d = self.type2test({'a': 'b'})
        self.assertEqual(d['a'], 'b')
        self.assertEqual(d['b'], 'b')
        d['b'] = 'c'
        self.assertEqual(d['b'], 'c')
        del d['a']
        self.assertEqual(d['a'], 'a')
    
@sequence_helper
class Tuple(Sequence):
    def __new__(cls, *args, **kwargs):
        self = super(Tuple, cls).__new__(cls)
        self._tuple = tuple(*args, **kwargs)
        return self
    def __getitem__(self, index):
        assert isinstance(index, int)
        assert 0 <= index < len(self)
        return self._tuple[index]
    def __len__(self):
        return len(self._tuple)
    def __repr__(self):
        return f"{type(self).__name__}({self._tuple})"

class TupleTest(unittest.TestCase):
    type2test = Tuple
    abc = Sequence

    # This is pretty hacky, but it allows us to copy and paste large
    # swaths of tests from the stdlib without having to modify them
    def assertEqual(self, x, y):
        if isinstance(x, (self.type2test, list)): x = tuple(x)
        if isinstance(y, (self.type2test, list)): y = tuple(y)
        return super().assertEqual(x, y)
    
    def test_decorate(self):
        class S:
            __getitem__ = 42
            __setitem__ = 42
            __delitem__ = 42
            __len__ = 42
            insert = 42
        self.assertRaises(TypeError, sequence_helper, S)                
        self.abc.register(S)
        S = sequence_helper(S)
        self.assertIsInstance(S(), self.abc)

        class T:
            pass
        self.abc.register(T)
        self.assertRaises(AttributeError, sequence_helper, T)

        @sequence_helper
        class U(self.abc):
            __getitem__ = 42
            __setitem__ = 42
            __delitem__ = 42
            __len__ = 42
            insert = 42
        self.assertIsInstance(U(), self.abc)
        
    def test_getitem(self):
        u = self.type2test([0, 1, 2, 3, 4])
        for i in range(len(u)):
            self.assertEqual(u[i], i)
            self.assertEqual(u[int(i)], i)
        for i in range(-len(u), -1):
            self.assertEqual(u[i], len(u)+i)
            self.assertEqual(u[int(i)], len(u)+i)
        self.assertRaises(IndexError, u.__getitem__, -len(u)-1)
        self.assertRaises(IndexError, u.__getitem__, len(u))
        self.assertRaises(ValueError, u.__getitem__, slice(0,10,0))

        u = self.type2test()
        self.assertRaises(IndexError, u.__getitem__, 0)
        self.assertRaises(IndexError, u.__getitem__, -1)

        self.assertRaises(TypeError, u.__getitem__)

        a = self.type2test([10, 11])
        self.assertEqual(a[0], 10)
        self.assertEqual(a[1], 11)
        self.assertEqual(a[-2], 10)
        self.assertEqual(a[-1], 11)
        self.assertRaises(IndexError, a.__getitem__, -3)
        self.assertRaises(IndexError, a.__getitem__, 3)
        
    def test_getslice(self):
        l = [0, 1, 2, 3, 4]
        u = self.type2test(l)

        self.assertEqual(u[0:0], self.type2test())
        self.assertEqual(u[1:2], self.type2test([1]))
        self.assertEqual(u[-2:-1], self.type2test([3]))
        self.assertEqual(u[-1000:1000], u)
        self.assertEqual(u[1000:-1000], self.type2test([]))
        self.assertEqual(u[:], u)
        self.assertEqual(u[1:None], self.type2test([1, 2, 3, 4]))
        self.assertEqual(u[None:3], self.type2test([0, 1, 2]))

        # Extended slices
        self.assertEqual(u[::], u)
        self.assertEqual(u[::2], self.type2test([0, 2, 4]))
        self.assertEqual(u[1::2], self.type2test([1, 3]))
        self.assertEqual(u[::-1], self.type2test([4, 3, 2, 1, 0]))
        self.assertEqual(u[::-2], self.type2test([4, 2, 0]))
        self.assertEqual(u[3::-2], self.type2test([3, 1]))
        self.assertEqual(u[3:3:-2], self.type2test([]))
        self.assertEqual(u[3:2:-2], self.type2test([3]))
        self.assertEqual(u[3:1:-2], self.type2test([3]))
        self.assertEqual(u[3:0:-2], self.type2test([3, 1]))
        self.assertEqual(u[::-100], self.type2test([4]))
        self.assertEqual(u[100:-100:], self.type2test([]))
        self.assertEqual(u[-100:100:], u)
        self.assertEqual(u[100:-100:-1], u[::-1])
        self.assertEqual(u[-100:100:-1], self.type2test([]))
        self.assertEqual(u[-100:100:2], self.type2test([0, 2, 4]))

        # Test extreme cases with long ints
        a = self.type2test([0,1,2,3,4])
        self.assertEqual(a[ -pow(2,128): 3 ], self.type2test([0,1,2]))
        self.assertEqual(a[ 3: pow(2,145) ], self.type2test([3,4]))
        self.assertEqual(a[3::sys.maxsize], self.type2test([3]))

    def test_subscript(self):
        a = self.type2test([10, 11])
        self.assertEqual(a.__getitem__(0), 10)
        self.assertEqual(a.__getitem__(1), 11)
        self.assertEqual(a.__getitem__(-2), 10)
        self.assertEqual(a.__getitem__(-1), 11)
        self.assertRaises(IndexError, a.__getitem__, -3)
        self.assertRaises(IndexError, a.__getitem__, 3)
        self.assertEqual(a.__getitem__(slice(0,1)), self.type2test([10]))
        self.assertEqual(a.__getitem__(slice(1,2)), self.type2test([11]))
        self.assertEqual(a.__getitem__(slice(0,2)), self.type2test([10, 11]))
        self.assertEqual(a.__getitem__(slice(0,3)), self.type2test([10, 11]))
        self.assertEqual(a.__getitem__(slice(3,5)), self.type2test([]))
        self.assertRaises(ValueError, a.__getitem__, slice(0, 10, 0))
        self.assertRaises(TypeError, a.__getitem__, 'x')

    def test_index(self):
        u = self.type2test([0, 1])
        self.assertEqual(u.index(0), 0)
        self.assertEqual(u.index(1), 1)
        self.assertRaises(ValueError, u.index, 2)

        u = self.type2test([-2, -1, 0, 0, 1, 2])
        self.assertEqual(u.count(0), 2)
        self.assertEqual(u.index(0), 2)
        self.assertEqual(u.index(0, 2), 2)
        self.assertEqual(u.index(-2, -10), 0)
        self.assertEqual(u.index(0, 3), 3)
        self.assertEqual(u.index(0, 3, 4), 3)
        self.assertRaises(ValueError, u.index, 2, 0, -10)

        self.assertRaises(TypeError, u.index)

        class BadExc(Exception):
            pass

        class BadCmp:
            def __eq__(self, other):
                if other == 2:
                    raise BadExc()
                return False

        a = self.type2test([0, 1, 2, 3])
        self.assertRaises(BadExc, a.index, BadCmp())

        a = self.type2test([-2, -1, 0, 0, 1, 2])
        self.assertEqual(a.index(0), 2)
        self.assertEqual(a.index(0, 2), 2)
        self.assertEqual(a.index(0, -4), 2)
        self.assertEqual(a.index(-2, -10), 0)
        self.assertEqual(a.index(0, 3), 3)
        self.assertEqual(a.index(0, -3), 3)
        self.assertEqual(a.index(0, 3, 4), 3)
        self.assertEqual(a.index(0, -3, -2), 3)
        self.assertEqual(a.index(0, -4*sys.maxsize, 4*sys.maxsize), 2)
        self.assertRaises(ValueError, a.index, 0, 4*sys.maxsize,-4*sys.maxsize)
        self.assertRaises(ValueError, a.index, 2, 0, -10)


@sequence_helper
class List(MutableSequence):
    def __new__(cls, *args, **kwargs):
        self = super(List, cls).__new__(cls)
        self._list = list(*args, **kwargs)
        return self
    def __getitem__(self, index):
        assert isinstance(index, int)
        assert 0 <= index < len(self)
        return self._list[index]
    def __delitem__(self, index):
        assert isinstance(index, int)
        assert 0 <= index < len(self)
        del self._list[index]
    def __setitem__(self, index, value):
        assert isinstance(index, int)
        assert 0 <= index < len(self)
        self._list[index] = value
    def insert(self, index, value):
        assert isinstance(index, int)
        assert 0 <= index <= len(self)
        self._list.insert(index, value)
    def __len__(self):
        return len(self._list)
    def __repr__(self):
        return f"{type(self).__name__}({self._list})"

class ListTest(TupleTest):
    type2test = List
    abc = MutableSequence

    def test_set_subscript(self):
        a = self.type2test(range(20))
        self.assertRaises(ValueError, a.__setitem__, slice(0, 10, 0), [1,2,3])
        self.assertRaises(TypeError, a.__setitem__, slice(0, 10), 1)
        self.assertRaises(ValueError, a.__setitem__, slice(0, 10, 2), [1,2])
        self.assertRaises(TypeError, a.__getitem__, 'x', 1)
        a[slice(2,10,3)] = [1,2,3]
        self.assertEqual(a, self.type2test([0, 1, 1, 3, 4, 2, 6, 7, 3,
                                            9, 10, 11, 12, 13, 14, 15,
                                            16, 17, 18, 19]))

    def test_setitem(self):
        a = self.type2test([0, 1])
        a[0] = 0
        a[1] = 100
        self.assertEqual(a, self.type2test([0, 100]))
        a[-1] = 200
        self.assertEqual(a, self.type2test([0, 200]))
        a[-2] = 100
        self.assertEqual(a, self.type2test([100, 200]))
        self.assertRaises(IndexError, a.__setitem__, -3, 200)
        self.assertRaises(IndexError, a.__setitem__, 2, 200)

        a = self.type2test([])
        self.assertRaises(IndexError, a.__setitem__, 0, 200)
        self.assertRaises(IndexError, a.__setitem__, -1, 200)
        self.assertRaises(TypeError, a.__setitem__)

        a = self.type2test([0,1,2,3,4])
        a[0] = 1
        a[1] = 2
        a[2] = 3
        self.assertEqual(a, self.type2test([1,2,3,3,4]))
        a[0] = 5
        a[1] = 6
        a[2] = 7
        self.assertEqual(a, self.type2test([5,6,7,3,4]))
        a[-2] = 88
        a[-1] = 99
        self.assertEqual(a, self.type2test([5,6,7,88,99]))
        a[-2] = 8
        a[-1] = 9
        self.assertEqual(a, self.type2test([5,6,7,8,9]))

        self.assertRaises(TypeError, a.__getitem__, 'a')

    def test_delitem(self):
        a = self.type2test([0, 1])
        del a[1]
        self.assertEqual(a, [0])
        del a[0]
        self.assertEqual(a, [])

        a = self.type2test([0, 1])
        del a[-2]
        self.assertEqual(a, [1])
        del a[-1]
        self.assertEqual(a, [])

        a = self.type2test([0, 1])
        self.assertRaises(IndexError, a.__delitem__, -3)
        self.assertRaises(IndexError, a.__delitem__, 2)

        a = self.type2test([])
        self.assertRaises(IndexError, a.__delitem__, 0)

        self.assertRaises(TypeError, a.__delitem__)

    def test_setslice(self):
        l = [0, 1]
        a = self.type2test(l)

        for i in range(-3, 4):
            a[:i] = l[:i]
            self.assertEqual(a, l)
            a2 = a[:]
            a2[:i] = a[:i]
            self.assertEqual(a2, a)
            a[i:] = l[i:]
            self.assertEqual(a, l)
            a2 = a[:]
            a2[i:] = a[i:]
            self.assertEqual(a2, a)
            for j in range(-3, 4):
                a[i:j] = l[i:j]
                self.assertEqual(a, l)
                a2 = a[:]
                a2[i:j] = a[i:j]
                self.assertEqual(a2, a)

        aa2 = a2[:]
        aa2[:0] = [-2, -1]
        self.assertEqual(aa2, [-2, -1, 0, 1])
        aa2[0:] = []
        self.assertEqual(aa2, [])

        a = self.type2test([1, 2, 3, 4, 5])
        a[:-1] = a
        self.assertEqual(a, self.type2test([1, 2, 3, 4, 5, 5]))
        a = self.type2test([1, 2, 3, 4, 5])
        a[1:] = a
        self.assertEqual(a, self.type2test([1, 1, 2, 3, 4, 5]))
        a = self.type2test([1, 2, 3, 4, 5])
        a[1:-1] = a
        self.assertEqual(a, self.type2test([1, 1, 2, 3, 4, 5, 5]))

        a = self.type2test([])
        a[:] = tuple(range(10))
        self.assertEqual(a, self.type2test(range(10)))

        self.assertRaises(TypeError, a.__setitem__, slice(0, 1, 5))

        self.assertRaises(TypeError, a.__setitem__)

    def test_delslice(self):
        a = self.type2test([0, 1])
        del a[1:2]
        del a[0:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test([0, 1])
        del a[1:2]
        del a[0:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test([0, 1])
        del a[-2:-1]
        self.assertEqual(a, self.type2test([1]))

        a = self.type2test([0, 1])
        del a[-2:-1]
        self.assertEqual(a, self.type2test([1]))

        a = self.type2test([0, 1])
        del a[1:]
        del a[:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test([0, 1])
        del a[1:]
        del a[:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test([0, 1])
        del a[-1:]
        self.assertEqual(a, self.type2test([0]))

        a = self.type2test([0, 1])
        del a[-1:]
        self.assertEqual(a, self.type2test([0]))

        a = self.type2test([0, 1])
        del a[:]
        self.assertEqual(a, self.type2test([]))

    def test_insert(self):
        a = self.type2test([0, 1, 2])
        a.insert(0, -2)
        a.insert(1, -1)
        a.insert(2, 0)
        self.assertEqual(a, [-2, -1, 0, 0, 1, 2])

        b = a[:]
        b.insert(-2, "foo")
        b.insert(-200, "left")
        b.insert(200, "right")
        self.assertEqual(b, self.type2test(["left",-2,-1,0,0,"foo",1,2,"right"]))

        self.assertRaises(TypeError, a.insert)

    def test_pop(self):
        a = self.type2test([-1, 0, 1])
        a.pop()
        self.assertEqual(a, [-1, 0])
        a.pop(0)
        self.assertEqual(a, [0])
        self.assertRaises(IndexError, a.pop, 5)
        a.pop(0)
        self.assertEqual(a, [])
        self.assertRaises(IndexError, a.pop)
        self.assertRaises(TypeError, a.pop, 42, 42)
        a = self.type2test([0, 10, 20, 30, 40])

    def test_slice2(self):
        u = self.type2test("spam")
        u[:2] = "h"
        self.assertEqual(u, self.type2test("ham"))

    def test_extendedslicing(self):
        #  subscript
        a = self.type2test([0,1,2,3,4])

        #  deletion
        del a[::2]
        self.assertEqual(a, self.type2test([1,3]))
        a = self.type2test(range(5))
        del a[1::2]
        self.assertEqual(a, self.type2test([0,2,4]))
        a = self.type2test(range(5))
        del a[1::-2]
        self.assertEqual(a, self.type2test([0,2,3,4]))
        a = self.type2test(range(10))
        del a[::1000]
        self.assertEqual(a, self.type2test([1, 2, 3, 4, 5, 6, 7, 8, 9]))
        #  assignment
        a = self.type2test(range(10))
        a[::2] = [-1]*5
        self.assertEqual(a, self.type2test([-1, 1, -1, 3, -1, 5, -1, 7, -1, 9]))
        a = self.type2test(range(10))
        a[::-4] = [10]*3
        self.assertEqual(a, self.type2test([0, 10, 2, 3, 4, 10, 6, 7, 8 ,10]))
        a = self.type2test(range(4))
        a[::-1] = a
        self.assertEqual(a, self.type2test([3, 2, 1, 0]))
        a = self.type2test(range(10))
        b = a[:]
        c = a[:]
        a[2:3] = self.type2test(["two", "elements"])
        b[slice(2,3)] = self.type2test(["two", "elements"])
        c[2:3:] = self.type2test(["two", "elements"])
        self.assertEqual(a, b)
        self.assertEqual(a, c)
        a = self.type2test(range(10))
        a[::2] = tuple(range(5))
        self.assertEqual(a, self.type2test([0, 1, 1, 3, 2, 5, 3, 7, 4, 9]))
        # test issue7788
        a = self.type2test(range(10))
        del a[9::1<<333]
        
if __name__ == '__main__':
    unittest.main()
