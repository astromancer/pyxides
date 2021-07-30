"""
Vectorization helpers
"""

# std libs

from collections import abc
import itertools as itt

# local libs
from recipes.op import MethodCaller, AttrGetter, AttrSetter, NULL
from recipes.functionals import echo0

from recipes.logging import logging, get_module_logger

# module level logger
logger = get_module_logger()
logging.basicConfig()
logger.setLevel(logging.DEBUG)


class repeat(dict):
    """Helper class for repeating scalar objects"""

    def __init__(self, mapping=(), **kws):
        kws = dict(mapping, **kws)
        super().__init__(zip(kws, map(itt.repeat, kws.values())))


class AttrVectorizer(AttrGetter):
    # TODO: optional caching for properties
    """
    Vectorize specific attribute lookup over items in a container with this
    descriptor.

    Examples
    --------

    The next example demonstrates using `AttrVectorizer` as a property for
    vectorized lookup of a specific attribute. Consider if we want to use the
    'stems' attribute of a `Sentence` class to represent the list of 'stem'
    attributes of `Word` objects in the container. The normal property
    definition for vectorized attribute lookup is as follows:

    >>> class Word:
    ...     def __init__(self, word, stem):
    ...         self.word = str(word)
    ...         self.stem = str(stem)

    >>> class Sentence(ListOf(Word), AttrVectorizer):
    ...     @property
    ...     def stems(self):
    ...         return self.attrs('stem')

    The `AttrVectorizer` class allows you to write thess kind of definitions
    more succinctly without the explicit function definition as:

    >>> class Sentence(ListOf(Word), AttrVectorizer):
    ...     stems = AttrVectorizer('stem')


    A more complete (although still somewhat contrived) example
    >>> class Letter:
    ...     def __init__(self, s):
    ...         self.letter = s
    ...         self.upper = s.upper()
    ...
    ... class Word(ListOf(Letter)):
    ...     def __init__(self, letters=()):
    ...         # initialize container
    ...         super().__init__(letters)
    ...
    ...         # properties: vectorized attribute getters on `Letter` objects
    ...         letters = AttrVectorizer('letter')
    ...         uppers = AttrVectorizer('upper')
    ...
    ... word = Word('hello!')
    ... word.letters # effectively does [_.letter for _ in word]
    ['h', 'e', 'l', 'l', 'o', '!']
    >>> word.uppers     # [_.upper for _ in word]
    ['H', 'E', 'L', 'L', 'O', '!']


    Note: Explicitly adding `AttrVectorizer` instances as class attributes (as
    above) is only necessary if you want direct access to container item
    attributes through a container attribute. Alternatively, use the `attrs`
    attribute gained from `AttrVectorizerMixin` for indirect non-specific
    attribute access:

    >>> class Word(ListOf(Letter), AttrVectorizerMixin):
    ...     '''This class supports vectorized attribute lookup through the
    ...     `attrs` property.'''
    ...
    ... word = Word('hello!')
    ... word.attr.letter
    ['h', 'e', 'l', 'l', 'o', '!']
    """

    def __init__(self, *keys, default=NULL, defaults=None, convert=echo0):
        super().__init__(*keys, default=default, defaults=defaults)
        assert callable(convert)
        self.convert = convert

    def __call__(self, target):
        return self.convert(list(map(super().__call__, target)))

    def __get__(self, instance, objtype=None):
        if instance is None:  # called from class
            return self

        # called from instance - fetch item attribute values
        return self(instance)

    def __set__(self, instance, value):
        n = len(self.keys)
        if n == 0:
            raise ValueError('Cannot set attribute.')

        if n != 1:
            raise NotImplementedError

        key, = self.keys  # pylint: disable=unbalanced-tuple-unpacking
        self.set(instance, {key: value})

    @staticmethod
    def set(target, mapping=(), /, **kws):
        """
        Set attributes on the items in the container.

        Parameters
        ----------
        target : abc.Collection
            Target container of objects for which attributes will be set
        mapping: dict or repeat
            (key, value) pairs to be assigned on each item in the container.
            Attribute names can be chained 'like.this' to set values on deeply
            nested objects in the container.


        Examples
        --------
        >>> def naive_plural(word):
        ...     return word + 's'
        ...
        ... class Word:
        ...     def __init__(word):
        ...         self.word = str(word).strip('!?,...')
        ...         self.plural = naive_plural(self.word)
        ...
        ... class Sentence(ListOf(Word)):
        ...     plurals = AttrVectorizer('plural')
        ...
        ... sentence = Sentence('one world!'.split())
        ... sentence.plurals
        ('ones', 'worlds')
        ... sentence plurals = 'many worlds'.split()
        ... sentence[0].plural, sentence[1].plural
        ('many', 'worlds')


        Raises
        ------
        ValueError
            If mapping values are of incorrect size (and are not `itt.repeat`
            objects).
        TypeError
            If any value is not `abc.Collection` or `itt.repeat`.
        """

        kws = dict(mapping or {}, **kws)

        # check values are same length as container before we attempt to set
        # any attributes
        size = len(target)
        assert size
        for key, values in kws.items():
            if isinstance(values, abc.Sized) and (len(values) != size):
                raise ValueError(
                    f'Cannot set attributes: {key} has {len(values)} values, '
                    f'while {size} are expected for target container of type '
                    f'{type(target)}.'
                )
            if isinstance(values, itt.repeat):
                # Catch infinite repeats and only use as many as are needed
                kws[key] = itt.islice(values, size)
            elif not isinstance(values, abc.Collection):
                raise TypeError(f'Cannot map attribute values for {key!r}. '
                                f'Unsupported type: {type(values)}.')

        # set
        setter = AttrSetter(*kws.keys())
        for item, values in zip(target, zip(*kws.values())):
            setter(item, values)
            # assert tuple([getattr(item, k) for k in kws.keys()]) == values


class AttrVector:  # This is already actually an AttrTable!!
    """
    Vectorize attribute lookup on items in a container.

    This descriptor class for containers enables getting attributes
    more easily from the items in the container. i.e vectorized attribute lookup
    across contained objects.

    Examples
    --------
    This example demonstrates general usage: Vectorized lookup of any attribute
    on items in the container.

    >>> import time
    ...
    ... class MyList(list):
    ...    attrs  = AttrVector()
    ...
    ... class Simple:
    ...     def __init__(self, i):
    ...         self.i = i
    ...         self.t = time.time()
    ...         self.hello = Hello()
    ...
    ... class Hello:
    ...     world = 'hi'
    ...
    ... l = MyList(map(Simple, [1, 2, 3]))
    >>> l.attrs.i
    [1, 2, 3]
    >>> l.attrs.t
    [1625738233.40768, 1625738233.407681, 1625738233.4076815]
    >>> l.attrs('hello.world')
    ['hi', 'hi', 'hi']
    """

    def __init__(self, target=None):
        # self.name = ''
        self.target = target

    def __getattr__(self, name):
        if self.target:
            return self(name)
        return super().__getattribute__(name)

    def __call__(self, *attrs, default=NULL, defaults=None):
        """
        Get a list of (tuples of) attribute values from the objects in the
        container for the attribute(s) in `attrs`.

        Parameters
        ----------
        attrs: str, or tuple of str
            Each of the items in `attrs` must be a string pointing to
            and attribute name on the contained object.
            Chaining the attribute lookup via '.'-separated strings is also
            permitted.  eg:. 'hello.world' will look up the 'world' attribute
            on the 'hello' attribute for each of the items in the container.

        Returns
        -------
        list or list of tuples
            The attribute values for each object in the container and each key
        """
        return AttrVectorizer(*attrs, default=NULL, defaults=None)(self.target)

    def __get__(self, instance, objtype=None):
        # self.target = instance  # None if called from class
        return self.__class__(instance)

    def set(self, mapping=(), **kws):
        return AttrVectorizer.set(self.target, mapping, **kws)


class _MethodVectorizer(MethodCaller):
    def __init__(self, *args, convert=list, **kws):
        super().__init__(*args, **kws)
        assert callable(convert)
        self.convert = convert

    def __call__(self, target):
        return self.convert(map(super().__call__, target))


class _GroupMethodVectorizer(_MethodVectorizer):
    def __call__(self, target):
        result = type(target).fromkeys(target.keys())
        result.default_factory = target.default_factory
        result.group_id = target.group_id

        # Call method with `self.name` on each value in dict
        result.update({
            key: MethodCaller.__call__(self, val)
                for key, val in target.items() if val
                })
        return result

# Vectorization dispatchers
# @ftl.singledispatch
# def vectorize(target)


class MethodVectorizer:
    """
    A descriptor class for specific method vectorization over items in a
    container.

    Examples
    --------
    >>> class Word(ListOf(str)):
    ...     # method vectorization on `str` methods.
    ...     uppers = MethodVectorizer('upper')
    ...
    ... word = Word('hello!')
    >>> word.uppers()     # [_.upper() for _ in word]
    ['H', 'E', 'L', 'L', 'O', '!']

    Another example:
    >>> import math
    ...
    ... class Formatters(ListOf(str)):
    ...     mod = MethodVectorizer('__mod__')
    ...
    ... fmt = Formatters(['%s', '%8.4f'])
    ... fmt.mod(repeat(math.pi))

    >>> fmt.mod(['My favourite number is π:', math.pi])
    """

    def __init__(self, name, target=None, convert=echo0):
        self.name = name
        self.target = target
        self.convert = convert

    def __call__(self, *args, **kws):
        assert self.target

        if isinstance(self.target, abc.MutableMapping):
            kls = _GroupMethodVectorizer
        elif isinstance(self.target, abc.Collection):
            kls = _MethodVectorizer
        else:
            raise TypeError(f'Cannot vectorize object of type '
                            f'{type(self.target)}.')

        try:
            return kls(self.name, *args, **kws)(self.target)
        finally:
            # ensure target gets reset
            self.target = None

    def __get__(self, instance, objtype=None):
        self.target = instance  # None if accessed from class
        return self


class CallVector(MethodVectorizer):
    """
    Descriptor for generalized method vectorization over objects in a container.

    >>> class Hi(list):
    ...    calls = CallVector()
    ...
    ... hi = Hi('hello')
    >>> hi.calls.upper()
    ['H', 'E', 'L', 'L', 'O']
    >>> hi.calls.join('||')
    ['|h|', '|e|', '|l|', '|l|', '|o|']
    >>> hi.calls.encode(encoding='latin')
    [b'h', b'e', b'l', b'l', b'o']
    """

    def __init__(self):
        super().__init__(self, None)

    def __call__(self, name, *args, **kws):
        # >>> container.calls('upper')
        # >>> container.calls('join', '||')
        self.name = name
        try:
            super().__call__(*args, **kws)
        finally:
            self.name = None

    def __getattr__(self, name):
        # >>> container.calls.upper()
        # >>> container.calls.join('||')
        return MethodVectorizer(name, self.target)


# class _GroupCallVectorizer(MethodVectorizer):
#     def __call__(self, *args, **kws):
#         return {key: _.calls(self.name, *args, **kws)
#                 for key, _ in self._container.items()}


class AttrVectorizerMixin:
    """
    This is a mixin class for containers that allows getting attributes from
    the objects in the container. i.e vectorized attribute lookup across
    contained objects, as well as vectorized method calls.

    This example demonstrates how to automate attribute retrieval
    >>> import time
    >>> class MyList(list, AttrVectorizerMixin):
    >>>    pass

    >>> class Simple:
    >>>     def __init__(self, i):
    >>>         i = i
    >>>         t = time.time()

    >>> l = MyList(map(Simple, [1, 2, 3]))
    >>> l.attrs('i')
    >>> l.attrs('t')

    """

    attrs = AttrVector()

    def varies_by(self, *keys):
        """
        Check if the attribute values mapped to by `keys` vary accross  of items
        in the container.

        Parameters
        ----------
        keys : tuple of str
            Attributes of items in the container that will be checked against
            each other for variation.

        Returns
        -------
        bool
            True if there is 1 unique value associated with each attribute
            accross all items, otherwise False.
        """
        return len(set(self.attrs(*keys))) > 1


class CallVectorizerMixin:
    # todo docsplice
    """
    Call vectorizer mixin. Gives inheritors the 'calls' method that can be used
    for vectorized function calls on objects inside the container.

    >>> class Hi(list, CallVectorizerMixin):
    ...    '''Class has `calls` method for vectorized method calling on items'''
    ...
    ... hi = Hi('hello')
    >>> hi.calls.upper()
    ['H', 'E', 'L', 'L', 'O']
    >>> hi.calls.join('||')
    ['|h|', '|e|', '|l|', '|l|', '|o|']
    >>> hi.calls.encode(encoding='latin')
    [b'h', b'e', b'l', b'l', b'o']
    """
    calls = CallVector()


class Vectorized(CallVectorizerMixin, AttrVectorizerMixin):
    """
    Mixin class for the vectorization API that embues inheritors with vectorized
    method calls through the `calls` class attribute and vectorized attribute
    lookup through the `attrs` class attribute.

    Example
    -------
    >>>
    """
