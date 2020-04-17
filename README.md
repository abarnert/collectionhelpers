# collectionhelpers
Decorators to make it easy to write custom sequences and mappings with full tuple/list/dict indexing.

# Intro

Defining custom collections is very simple with the classes in [`collections.abc`](https://docs.python.org/3/library/collections.abc.html), which work as mixins as well as ABCs. For example, if you want a `tuple`-like class, you only have to define `__getitem__` and `__len__`, and you get `__contains__`, `__iter__`, `__reversed__`, `index`, and `count` for free.

But there's one big problem: You don't get slices for free. Or negative indexes. Or conversion via the `__index__` protocol. And as soon as you start implementing that, you realize that it takes a lot of boilerplate, some of which is hard to get right (especially when you get to `__setitem__` for `MutableSequence`), but is exactly the same in every sequence you ever write.

Wouldn't it be nice if there were a helper that would supply all that complicated indexing behavior too?

Well now you can!

# `Mapping` and `MutableMapping`

The only `dict` feature missing from `Mapping` and `MutableMapping` is the `__missing__` protocol--which actually only matters to `dict` subclasses, not `dict` itself, but it's still sometimes important:

    class KeyDefaultingDict(dict):
        def __missing__(self, key):
	        return key

    d = KeyDefaultingDict(a=1)
    print(d['a'])
	print(d['b'])

This prints `1`, then prints `b` instead of raising a `KeyError`. But if you change `KeyDefaultingDict` to inherit from a different mapping type, it raises `KeyError`.

As simple as this seems, there are some tricks to getting it right. For example, if you inherited the default `__contains__` from `Mapping`, it just checks `self[key]`, so if your `__getitem__` calls `__missing__`, every mapping now contains every possible key, which is not what you want (and not what `dict` does). And similarly for `get`.

So, instead of doing it yourself, just decorate the mapping type (in subclassing situations like this one, you can decorate either the base mapping superclass or the missing-implementing subclass) and it works:

    @mapping_helper
    class KeyDefaultingDict(MyCustomMapping):
        def __missing__(self, key):
            return key

Just provide (or inherit) a `__getitem__` that raises a `KeyError` as expected, and the wrapper will replace your `__getitem__` with one that adds the call to `__missing__` when it should.

The wrapper will also wrap `__contains__` and `get` if they're inherited from `collections.abc.Mapping`, but it will leave them alone otherwise. This seems to usually be the right thing, but it is admittedly pretty hacky, and might need to change in future versions.

## `Sequence`

There's a broad class of related indexing stuff that`tuple` does: negative indices, slicing, converting non-`int` indices with `__index__`, raising on out-of-range indices (but not raising on out-of-range slice start/stop or `index` method parameters). Here it's even more obvious that nobody wants to write all of that.

So instead, just implement a `Sequence` with a `__len__`, and a `__getitem__` that works for integers `0 <= index < len(self)`, and decorate it with `@sequence_helper`. The decorator will replace your `__getitem__` with a new wrapper that adds in all the `tuple` stuff.

The wrapper does not modify `index`. The `Sequence` implementation already handles negative indices properly, so the only real problem is `__index__`, which I don't think comes up often enough to worry about for this method. But if I'm wrong, it would be easy to add later.

Slicing a sequence returns a subsequence of type `type(self)`. This means that your type (and any subclasses) needs to be constructable from an iterable, in the same way that `tuple` is. Which is not true for all sequences—sometimes constructing from an iterable requires passing additional args (think of a sequence equivalent to `defaultdict`), or calling some custom factory, or sometimes it's just not even possible (e.g., range, or a proxy or bridge to some immutable sequence outside your control) so you'd want to just return a `list` or `tuple` or something. Either way, you can't use this decorator. If that turns out to be a problem in practice… see TODO below.

Nothing else is wrapped. The `index` method provided by `Sequence` already handles negative values for `start` and `stop` properly, but it doesn't handle `__index__` conversion. And a custom implementation might not handle negative values, or might even not accept `start` and `stop` parameters. The decorator does not currently help with those problems, but if it turns out to be needed in practice, that shouldn't be hard to add something that wraps the `Sequence` implementation.

## `MutableSequence`

Mutation makes `list` even more complicated. Besides just having a lot more methods, you can delete slices, replace extended slices with iterables of the same length, replace simple slices with iterables of any length (and without building a useless temporary list first). All of which can be fun, but especially slice replacement.

To get this behavior, all you need to do is implement a `MutableSequence` with a `__len__`, and `__getitem__`, `__delitem__`, `__setitem__` that work for integers `0 <= index < len(self)`, and `insert` that works for integers `0 <= index <= len(self)` (notice that last `<=`, because you can insert at the end of a sequence), and decorate it with `@sequence_helper`. The decorator will replace `__getitem__`, `__delitem__`, `__setitem__`, and `insert` with wrappers that do all the slice assignment and so on the same way as `list`.

Nothing else is wrapped. The `index` has the same (probably-non-)issue as with `Sequence`. The `pop` method will automatically get the same features if it's implemented in terms of `__getitem__` and `__delitem__` (including indirectly, e.g., with subscription syntax), and the one provided by `MutableSequence` does, and so will most reasonable custom implementations—but if yours doesn't, the decorator won't help. Again, that would be easy to add if needed, but I don't think it is.

# Testing

Other than a small number of tests for the decorators themselves, most of the tests are copied from the relevant bits of the stdlib test suite, run on simple classes that just own and delegate to a `dict`/`tuple`/`list`, implementing the minimum required by the `collections.abc` class and the decorator. They also assert that the decorator's wrappers never pass any out-of-bounds indices to them.

# TODO (maybe)

 * Should `sequence_helper` take an optional `factory` to construct slices? This would default to `type(self)`, but `cls`, `list` or `tuple`, an alternate-constructor classmethod, a `partial` that binds in other parameters, etc. are all reasonable things to use.
 * Should `sequence_helper` default to `cls` for slices instead of `type(self)` to construct slices? That's what `tuple` and `list` do if you slice a subclass.
 * Should `mapping_helper` replace `__contains__` and `get` unconditionally, rather than only if they come from `Mapping`? Or maybe optionally, based on a parameter to the decorator?
 * Can extended slice assignment avoid making a temporary copy of the input when it's `Sized`? I think `list` always copies unless it's a fast-sequence (`list` or `tuple`), but I don't think that's actually necessary.
 * Does `Sequence.index` need to be replaced (maybe dependent on where it comes from, or optionally)?
 * Does `MutableSequence.pop` need to be replaced (maybe dependent or optionally)?
 * Is it work making all of the exception comments match the builtin types, modulo the type names? The stdlib test suite does actually check some of these with regex…
 * Is there any reasonable way to combine this library with a views library, or can we just not worry about that?
