
# std libs
import operator as op
import functools as ftl
import itertools as itt

# local libs
from recipes.op import MethodCaller
from recipes.functionals import echo0


class CallVectorizer:
    """Vectorized method calls on items in a container"""

    def __init__(self, container):
        self._container = container

    def __call__(self, name, *args, **kws):
        return list(self.calls_gen(name, *args, **kws))

    def _calls_gen(self, name, *args, **kws):
        yield from map(MethodCaller(name, *args, **kws), self._container)

    def __getattr__(self, key):
        if key in self.__dict__:
            return super().__getattr__(key)
        else:
            return ftl.partial(self, key)

# def _unpack()
# unpack = (_echo, list)[isinstance(val, abc.Iterable)]


class AttrMapper:
    """
    This is a mixin class for containers that allows getting attributes from
    the objects in the container. i.e vectorized attribute lookup across
    contained objects, as well as vectorized method calls.

    This example demonstrates basic usage
    >>> import time
    >>> class MyList(list, AttrMapper):
    >>>    pass

    >>> class Simple:
    >>>     def __init__(self, i):
    >>>         i = i
    >>>         t = time.time()

    >>> l = MyList(map(Simple, [1, 2, 3]))
    >>> l.attrs('i')
    >>> l.attrs('t')

    >>> l = MyList('hello world')
    >>> l.calls('upper')
    >>> l.calls('zfill', 8)
    >>> l.calls('encode', encoding='latin')


    """

    def attrs(self, *keys):
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

        return list(self.attrs_gen(*keys))

    def attrs_gen(self, *keys):
        yield from map(op.attrgetter(*keys), self)

    def set_attrs(self, each=False, **kws):
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


        Examples
        --------
        >>> mylist.set_attrs(**{'hello.world': 1})
        >>> mylist[0].hello.world == mylist[1].hello.world == 1
        True
        >>> mylist.set_attrs(each=True, foo='12')
        >>> (mylist[0].foo == '1') and (mylist[1].foo == '2')
        True
        """

        # kws.update(zip(keys, values)) # check if sequences else error prone
        get_value = itt.repeat
        if each:
            get_value = echo0

            # check values are same length as container before we attempt to set
            # any attributes
            # unpack the keyword values in case they are iterables:
            kws = dict(zip(kws.keys(), map(list, kws.values())))
            lengths = set(map(len, kws.values()))
            if (lengths - {len(self)}):
                raise ValueError(
                    f'Not all values are the same length ({lengths}) as the '
                    f'container {len(self)} while `each` has been set.'
                )

        for key, value in kws.items():
            *chained, attr = key.rsplit('.', 1)
            get_parent = op.attrgetter(chained[0]) if chained else echo0
            for obj, val in zip(self, get_value(value)):
                setattr(get_parent(obj), attr, val)

    def calls(self, name, *args, **kws):
        # TODO: replace with CallVectorizer.  might have to make that a
        #   descriptor
        """

        Parameters
        ----------
        name
        args
        kws

        Returns
        -------

        """
        return list(self.calls_gen(name, *args, **kws))

    def calls_gen(self, name, *args, **kws):
        yield from map(MethodCaller(name, *args, **kws), self)

    def varies_by(self, *keys):
        return len(set(self.attrs(*keys))) > 1


class AttrProp:
    """
    Descriptor for vectorized attribute getting on `AttrMapper` subclasses.

    Examples
    --------
    The normal property definition for getting attributes on contained items
    >>> class Example:
    ...     @property
    ...     def stems(self):
    ...         return self.attrs('stem')

    Can now be written as
    >>> class Example:
    ...     stems = AttrProp('stems')


    A more complete (although somewhat contrived) example
    >>> class Simple:
    ...     def __init__(self, b):
    ...         self.b = b.upper()
    ...
    ... class ContainerOfSimples(UserList, OfTypes(Simple), AttrMapper):
    ...     def __init__(self, images=()):
    ...         # initialize container
    ...         super().__init__(images)
    ...
    ...         # properties: vectorized attribute getters on `images`
    ...         bees = AttrProp('b')
    ...
    ... cs = ContainerOfSimples(map(Simple, 'hello!'))
    ... cs.bees
    ['H', 'E', 'L', 'L', 'O', '!']
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
