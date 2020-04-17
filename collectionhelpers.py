"""Decorator helpers for defining custom Sequence and Mapping types
with fancy indexing behavior like the builtins"""

from collections.abc import Sequence, MutableSequence, Mapping
from functools import wraps

def mapping_helper(cls):
    """Class decorator that adds missing-key handling.

    Define a __getitem__ that raises KeyError on missing keys, add the
    decorator, and it's replaced with a wrapper that calls __missing__
    on missing keys, exactly as dict does."""

    if not issubclass(cls, Mapping):
        raise TypeError("can only help mappings")

    _getitem = cls.__getitem__
    @wraps(_getitem)
    def __getitem__(self, key):
        try:
            return _getitem(self, key)
        except KeyError:
            try:
                missing = type(self).__missing__
            except AttributeError:
                pass
            else:
                return missing(self, key)
            raise
    cls.__getitem__ = __getitem__

    # The default Mapping.__contains__ just tests for self[key], which
    # will of course check with __missing__. But it shouldn't.
    _contains = cls.__contains__
    if _contains == Mapping.__contains__:
        @wraps(_contains)
        def __contains__(self, key):
            try:
                _getitem(self, key)
            except KeyError:
                return False
            else:
                return True
        cls.__contains__ = __contains__

    # Same issue as __contains__.
    _get = cls.get
    if _get == Mapping.get:
        @wraps(_get)
        def get(self, key, default=None):
            try:
                return _getitem(self, key)
            except KeyError:
                return default
        cls.get = get
            
    return cls

def sequence_helper(cls):
    """Class decorator that adds slice and negative index handling and
    type and range checking.
    
    Define __getitem__ (and, for mutable sequences, __setitem__, __delitem__,
    and insert methods) that can only handle positive integer indices within 
    range, add the decorator, and your methods will be replaced by wrappers 
    that can handle all the same varieties of indexing as tuple and list,
    exactly they way they do."""

    if not issubclass(cls, Sequence):
        raise TypeError("can only help sequences")
    
    def deslice(self, index):
        # The slice.indices method already does the exact same checking and
        # conversion we do for individual indices in posintify, so we don't
        # need to do it manually.
        return range(*index.indices(len(self)))

    def _posintify(self, index):
        if not isinstance(index, int):
            try:
                index = index.__index__()
            except AttributeError:
                raise TypeError("indices must be integers")
        if index < 0:
            index += len(self)
        return index
    
    def posintify(self, index):
        index = _posintify(self, index)
        if index < 0 or index >= len(self):
            raise IndexError("index out of range")
        return index

    def posinttruncify(self, index):
        index = _posintify(self, index)
        if index < 0:
            index = 0
        if index > len(self):
            index = len(self)
        return index
    
    _getitem = cls.__getitem__
    @wraps(_getitem)
    def __getitem__(self, index):
        if isinstance(index, slice):
            # TODO: Maybe this should be a choice between returning a list,
            #       a seq, or a type(self)? Not all sequence types can be
            #       constructed from an iterable...
            return type(self)(_getitem(self, i) for i in deslice(self, index))
        else:
            return _getitem(self, posintify(self, index))
    cls.__getitem__ = __getitem__

    if not issubclass(cls, MutableSequence):
        return cls
    
    _delitem = cls.__delitem__
    @wraps(_delitem)
    def __delitem__(self, index):
        if isinstance(index, slice):
            for i in reversed(deslice(self, index)):
                _delitem(self, i)
        else:
            _delitem(self, posintify(self, index))
    cls.__delitem__ = __delitem__

    _insert = cls.insert
    @wraps(_insert)
    def insert(self, index, value):
        _insert(self, posinttruncify(self, index), value)
    cls.insert = insert

    _setitem = cls.__setitem__
    @wraps(_setitem)
    def __setitem__(self, index, value):
        if isinstance(index, slice):
            indices = deslice(self, index)
            if index.step is not None and index.step != 1:
                try:
                    values = tuple(value)
                except TypeError:
                    raise TypeError("must assign iterable to extended slice")
                if len(values) != len(indices):
                    raise ValueError(f"attempt to assign {len(values)} values "
                                     f"to an extended slice of size "
                                     f"{len(indices)}")
                for i, v in zip(indices, values):
                    self[i] = v
            else:
                try:
                    # a[:-1] = a is legal, and assigns a copy of all of a
                    # to the slice a[:-1] (with the same net effect as
                    # if a: a.append(a[-1])), rather than going into an
                    # infinite loop appending from an iterator that keeps
                    # growing as we go. Of course you can still get into
                    # trouble by, e.g., creating a sequence that delegates
                    # to a list and then doing a[:-1] = a._list, but then
                    # you're actually asking for an infinite loop...
                    if value is self:
                        values = tuple(value)
                    else:
                        values = iter(value)
                except TypeError:
                    raise TypeError("must assign iterable to slice")
                for i in reversed(indices):
                    _delitem(self, i)
                for i, value in enumerate(values, start=indices.start):
                    _insert(self, i, value)
        else:
            _setitem(self, posintify(self, index), value)
    cls.__setitem__ = __setitem__

    return cls
