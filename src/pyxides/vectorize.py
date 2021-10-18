"""
Vectorization helpers
"""

# std

from collections import abc
import itertools as itt

# local
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


class vdict(dict):
    """
    Dictionary with vectorized item lookup.
    """

    def __getitem__(self, key):
        # dispatch on np.ndarray for vectorized item getting with arbitrary
        # nesting
        if isinstance(key, abc.Collection):
            # Container and not str
            return [self[_] for _ in key]

        if key in (Ellipsis, None):
            return list(self.values())

        return super().__getitem__(key)


class AttrVector(AttrGetter):  #
    # TODO: optional caching for properties
    """
    Vectorize specific attribute lookup over items in a container with this
    data descriptor.

    Examples
    --------

    The next example demonstrates using `AttrVector` as a property for
    vectorized lookup of a specific attribute. Consider if we want to use the
    'stems' attribute of a `Sentence` class to represent the list of 'stem'
    attributes of `Word` objects in the container. The normal property
    definition for vectorized attribute lookup is as follows:

    >>> class Word:
    ...     def __init__(self, word, stem):
    ...         self.word = str(word)
    ...         self.stem = str(stem)

    >>> class Sentence(ListOf(Word), AttrVector):
    ...     @property
    ...     def stems(self):
    ...         return self.attrs('stem')

    The `AttrVector` class allows you to write thess kind of definitions
    more succinctly without the explicit function definition as:

    >>> class Sentence(ListOf(Word), AttrVector):
    ...     stems = AttrVector('stem')


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
    ...         letters = AttrVector('letter')
    ...         uppers = AttrVector('upper')
    ...
    ... word = Word('hello!')
    ... word.letters # effectively does [_.letter for _ in word]
    ['h', 'e', 'l', 'l', 'o', '!']
    >>> word.uppers     # [_.upper for _ in word]
    ['H', 'E', 'L', 'L', 'O', '!']


    Note: Explicitly adding `AttrVector` instances as class attributes (as
    above) is only necessary if you want direct access to container item
    attributes through a container attribute. Alternatively, use the `attrs`
    attribute gained from `AttrTabulate` for dynamic attribute access:

    >>> class Word(ListOf(Letter), AttrTabulate):
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
        return self.convert(list(self.map(target)))

    def map(self, target):
        assert isinstance(target, abc.Collection)
        return map(super().__call__, target)

    def filter(self, *args):
        *test, target = args
        return filter(test or None, self.map(target))

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
        This method is used to manipulate the attributes of many objects at
        once. It sets values of one or more specified attributes on all the
        objects in a `target` container.  Attribute value pairs can be provided
        as a mapping, as the first positional argument, or as keyword value
        pairs. Values provided should either be lists or tuples of the same size
        as the target container, or, if all target objects are to have the same
        attribute value, a `repeat` object.


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
        ...     plurals = AttrVector('plural')
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


class AttrTableDescriptor: 
    """
    Vectorized attribute lookup on items in a container.

    This is a descriptor class for container classes that vectorizes attribute
    lookup across objects in the container.

    Examples
    --------
    This example demonstrates general usage: Vectorized lookup of any attribute
    on items in the container.

    >>> import time
    ...
    ... class MyList(list):
    ...    getattrs  = AttrTableDescriptor()
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

    >>> l.getattrs('hello.world')
    ['hi', 'hi', 'hi']

    Attributes of the children can also be accessed as attributes of this object
    eg:
    >>> l.getattrs.i
    [1, 2, 3]
    >>> l.getattrs.t
    [1625738233.40768, 1625738233.407681, 1625738233.4076815]

    """

    # TODO ADD optional static attributes here ?! 
    # Can optionally, be initialized with a set of static attributes names, in
    # which case, the call method can be used without parameters to lookup those
    # attribute values. 
    
    def __init__(self, target=None):
        # self.name = ''
        self.target = target

    def __getattr__(self, name):
        # hack attribute lookup to vectorize across container if possible as a
        # shortcut. ie. self.attr.name does self.getattrs('name')
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
        return AttrVector(*attrs, default=NULL, defaults=None)(self.target)

    def __get__(self, instance, objtype=None):
        # self.target = instance  # None if called from class
        return self.__class__(instance)

    def set(self, mapping=(), **kws):
        return AttrVector.set(self.target, mapping, **kws)


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
        result.update(
            {key: MethodCaller.__call__(self, val)
                for key, val in target.items() if val}
        )
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

        result = kls(self.name, *args, **kws)(self.target)
        # ensure target gets reset
        self.target = None
        return result

    def __get__(self, instance, objtype=None):
        self.target = instance  # None if accessed from class
        return self


class CallVectorizerDescriptor(MethodVectorizer):
    """
    Descriptor for generalized method vectorization over objects in a container.

    >>> class Hi(list):
    ...    calls = CallVectorizerDescriptor()
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
        result = super().__call__(*args, **kws)
        self.name = None
        return result

    def __getattr__(self, name):
        # >>> container.calls.upper()
        # >>> container.calls.join('||')
        return MethodVectorizer(name, self.target)


# class _GroupCallVectorizer(MethodVectorizer):
#     def __call__(self, *args, **kws):
#         return {key: _.calls(self.name, *args, **kws)
#                 for key, _ in self._container.items()}


class AttrTabulate:
    """
    This is a mixin class for containers that allows getting attributes from
    the objects in the container. i.e vectorized attribute lookup across
    contained objects, as well as vectorized method calls.

    This example demonstrates how to automate attribute retrieval
    >>> import time
    >>> class MyList(list, AttrTabulate):
    >>>    pass

    >>> class Simple:
    >>>     def __init__(self, i):
    >>>         i = i
    >>>         t = time.time()

    >>> l = MyList(map(Simple, [1, 2, 3]))
    >>> l.attrs('i')
    >>> l.attrs('t')

    """

    attrs = getattrs = AttrTableDescriptor()

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


class MethodVectorizerMixin:
    # todo docsplice
    """
    Call vectorizer mixin. Gives inheritors the 'calls' method that can be used
    for vectorized function calls on objects inside the container.

    >>> class Hi(list, MethodVectorizerMixin):
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
    calls = CallVectorizerDescriptor()


class Vectorized(MethodVectorizerMixin, AttrTabulate):
    """
    Mixin class for the vectorization API that embues inheritors with vectorized
    method calls through the `calls` class attribute and vectorized attribute
    lookup through the `attrs` class attribute.

    Example
    -------
    >>>
    """
