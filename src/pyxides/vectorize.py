

# std libs
import operator as op
import itertools as itt

# local libs
from recipes.op import MethodCaller
from recipes.functionals import echo0


# def _unpack()
# unpack = (_echo, list)[isinstance(val, abc.Iterable)]


class AttrVectorizeDescriptor:
    """
    Vectorized attribute lookup on items in a container.

    This is a descriptor class for containers that enables getting attributes
    more easily from the items in the container. i.e vectorized attribute lookup
    across contained objects.
    
    Examples
    --------
    This example demonstrates basic usage
    >>> import time
    ...
    ... class MyList(list):
    ...    attrs  = AttrVectorizeDescriptor()
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

    def __init__(self, parent=None):
        self.parent = parent

    def __get__(self, instance, objtype=None):
        if instance is None:  # called from class
            return self

        # called from instance. initialize!
        return self.__class__(instance)

    def __getattr__(self, name):
        return self.__call__(name)

    def __call__(self, *keys):
        """
        Get a list of (tuples of) attribute values from the objects in the
        container for the attribute(s) in `attrs`.

        Parameters
        ----------
        keys: str, or tuple of str
            Each of the items in `keys` must be a string pointing to
            and attribute name on the contained object.
            Chaining the attribute lookup via '.'-separated strings is also
            permitted.  eg:. 'hello.world' will look up the 'world' attribute
            on the 'hello' attribute for each of the items in the container.

        Returns
        -------
        list or list of tuples
            The attribute values for each object in the container and each key
        """

        return list(self._attrs_gen(*keys))

    def _attrs_gen(self, *keys):
        yield from map(op.attrgetter(*keys), self.parent)

    def set(self, mapping=(), each=False, **kws):
        """
        Set attributes on the items in the container.

        Parameters
        ----------
        kws: dict
            (attribute, value) pairs to be assigned on each item in the
            container.  Attribute names can be chained 'like.this' to set values
            on deeply nested objects in the container.

        each: bool
            Use this switch when passing iterable values to set each item in the
            value sequence to the corresponding item in the container.  In this
            case, each value iterable must have the same length as the container
            itself.
        """

        # kws.update(zip(keys, values)) # check if sequences else error prone
        kws = dict(mapping or {}, **kws)
        get_value = itt.repeat
        if each:
            get_value = echo0

            # check values are same length as container before we attempt to set
            # any attributes
            # unpack the keyword values in case they are iterables:
            kws = dict(zip(kws.keys(), map(list, kws.values())))
            lengths = set(map(len, kws.values()))
            if (lengths - {len(self.parent)}):
                raise ValueError(
                    f'Not all values are the same length ({lengths}) as the '
                    f'container {len(self.parent)} while `each` has been set.'
                )

        for key, value in kws.items():
            *chained, attr = key.rsplit('.', 1)
            get_parent = op.attrgetter(chained[0]) if chained else echo0
            for obj, val in zip(self.parent, get_value(value)):
                setattr(get_parent(obj), attr, val)


class AttrVectorize:
    """
    This is a mixin class for containers that allows getting attributes from
    the objects in the container. i.e vectorized attribute lookup across
    contained objects, as well as vectorized method calls.

    This example demonstrates how to automate attribute retrieval
    >>> import time
    >>> class MyList(list, AttrVectorize):
    >>>    pass

    >>> class Simple:
    >>>     def __init__(self, i):
    >>>         i = i
    >>>         t = time.time()

    >>> l = MyList(map(Simple, [1, 2, 3]))
    >>> l.attrs('i')
    >>> l.attrs('t')

    """

    attrs = AttrVectorizeDescriptor()

    def varies_by(self, *keys):
        return len(set(self.attrs(*keys))) > 1


class AttrVector:
    """
    Descriptor for vectorized attribute getting on `AttrVectorize` subclasses.

    Examples
    --------
    Consider if we want to use the 'stems' attribute of a `Sentence` class to
    represent the list of 'stem' attributes of `Word` objects in the container.
    The normal property definition for vectorized attribute lookup is as
    follows:

    >>> class Word:
    ...     def __init__(self, word, stem):
    ...         self.word = str(word)
    ...         self.stem = str(stem)

    >>> class Sentence(ListOf(Word), AttrVectorize):
    ...     @property
    ...     def stems(self):
    ...         return self.attrs('stem')

    The `AttrVector` class allows you to write thess kind of definitions more
    succinctly without explicit function definition as:
    >>> class Sentence(ListOf(Word), AttrVectorize):
    ...     stems = AttrVector('stem')


    A more complete (although still somewhat contrived) example
    >>> class Letter:
    ...     def __init__(self, s):
    ...         self.letter = s
    ...         self.upper = s.upper()
    ...
    ... class Word(ListOf(Letter), AttrVectorize):
    ...     def __init__(self, letters=()):
    ...         # initialize container
    ...         super().__init__(letters)
    ...
    ...         # properties: vectorized attribute getters on `letters`
    ...         letters = AttrVector('letter')
    ...         uppers = AttrVector('upper')
    ...
    ... word = Word(map(Letter, 'hello!'))
    ... word.letters
    ['h', 'e', 'l', 'l', 'o', '!']
    >>> cs.uppers
    ['H', 'E', 'L', 'L', 'O', '!']

    Note: The addition of `AttrVector`s are only necessary if you want direct
    access to container item attributes. Alternatively, use the `attrs` method 
    gained from `AttrVectorize`:
    >>> class Word(ListOf(Letter), AttrVectorize):
    ...     pass

    >>> word = Word(map(Letter, 'hello!'))
    ... word.attr.letter

    """

    def __init__(self, name, convert=echo0):
        self.name = name
        self.convert = convert

    def __get__(self, obj, kls=None):
        if obj is None:
            # class attribute lookup
            return self

        # instance attribute lookup
        return self.convert(obj.attrs(self.name))


class CallVectorizeDescriptor:
    """
    Vectorized method calls on items in a container.

    >>> class Hi(list):
    ...    calls = CallVectorizeDescriptor()
    ...
    ... hi = Hi('hello')
    >>> hi.calls.upper()
    ['H', 'E', 'L', 'L', 'O']
    >>> hi.calls.join('||')
    ['|h|', '|e|', '|l|', '|l|', '|o|']
    >>> hi.calls.encode(encoding='latin')
    [b'h', b'e', b'l', b'l', b'o']
    """

    def __init__(self, parent=None):
        self.parent = parent

    def __call__(self, name, *args, **kws):
        # old behaviour. discouraged
        # >>> container.calls('upper')
        # >>> container.calls('join', '||')
        return _CallVectorizer(self.parent, name)

    def __get__(self, instance, objtype=None):
        if instance is None:  # called from class
            return self

        # called from instance. initialize!
        return self.__class__(instance)

    def __getattr__(self, name):
        return _CallVectorizer(self.parent, name)


class _CallVectorizer:
    def __init__(self, container, name):
        self._container = container
        self.name = str(name)

    def __call__(self, *args, **kws):
        return list(self._calls_gen(*args, **kws))

    def _calls_gen(self, *args, **kws):
        yield from map(MethodCaller(self.name, *args, **kws), self._container)


class CallVectorize:
    # todo docsplice
    """
    Call vectorizer mixin. Gives inheritors the 'calls' method that can be used
    for vectorized function calls on objects inside the container.

    >>> class Hi(list, CallVectorize):
    ...    pass
    ...
    ... hi = Hi('hello')
    >>> hi.calls.upper()
    ['H', 'E', 'L', 'L', 'O']
    >>> hi.calls.join('||')
    ['|h|', '|e|', '|l|', '|l|', '|o|']
    >>> hi.calls.encode(encoding='latin')
    [b'h', b'e', b'l', b'l', b'o']

    """
    calls = CallVectorizeDescriptor()


class Vectorized(CallVectorize, AttrVectorize):
    """
    Mixin class that embues method and attribute lookup vectorization
    """
