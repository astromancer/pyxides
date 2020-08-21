"""
Container magic
"""

from collections import OrderedDict
from recipes.decor import raises as bork
import warnings
import abc
import collections as col
import numbers
from .dicts import DefaultOrderedDict
import itertools as itt
import operator as op
import inspect
import functools as ftl

import numpy as np

from recipes.logging import LoggingMixin
from .sets import OrderedSet
from .dicts import pformat


SELECT_LOGIC = {'AND': np.logical_and,
                 'OR': np.logical_or,
                 'XOR': np.logical_xor}


def is_property(v):
    return isinstance(v, property)


def _echo(_):
    return _


def str2tup(keys):
    if isinstance(keys, str):
        keys = keys,  # a tuple
    return keys


# def attrgetter_default(*attrs, **kw):
#     """
#     Like attrgetter, but defaults to None (or specified default) if attr
#     doesn't exist.
#     Always returns tuple, even if only one in attrs (unlike attrgetter)
#     """
#     default = kw.pop('default', None)
#     if kw:
#         raise TypeError("attrgetter_default() got unexpected "
#             "keyword argument(s): %r" % sorted(kw))
#     def fn(obj):
#         getter = lambda attr: getattr(obj, attr, default)
#         return tuple(map(getter, attrs))
#     return fn

class SelfAwareContainer:   # recipes.oo.SelfAware ???
    """
    A mixin class for containers that bypasses object initialization if the
    first argument to the initializer is an object of the same class,
    in which case that object is returned. Use at your own discretion.
    """
    _skip_init = False

    def __new__(cls, *args, **kws):
        # this is here to handle initializing the object from an already
        # existing instance of the class
        if len(args) and isinstance(args[0], cls):
            instance = args[0]
            instance._skip_init = True
            return instance
        else:
            return super().__new__(cls)

        # TODO: test + examples


class OfTypes(abc.ABCMeta):
    """
    Factory that creates TypeEnforcer classes. Allows for the following usage
    pattern:
    >>> class Container(UserList, OfTypes(int)): pass
    which creates a container class `Container` that will only allow integer
    items inside. This constructor assigns a tuple of allowed types as class
     attribute `_allowed_types`
    """

    # NOTE: inherit from ABCMeta to avoid metaclass conflict with UserList which
    # has metaclass abc.ABCMeta

    def __new__(cls, *args):

        if isinstance(args[0], str):
            # This results from an internal call during class construction
            name, bases, attrs = args
            # create class
            return super().__new__(cls, name, cls.make_bases(name, bases), attrs)

        # we are here if invoked by direct call:
        # cls = OfTypes(int)

        # create TypeEnforcer class that inherits from _TypeEnforcer.
        # args gives allowed types for this container.
        # `_allowed_types` class attribute set to tuple of allowed types

        # check arguments are given and class objects
        if len(args) == 0:
            raise ValueError(f'{cls.__name__!r}s constructor requires at least '
                             'one argument: the allowed type(s)')
        for kls in args:
            if not isinstance(kls, type):
                raise TypeError(f'Arguments to {cls.__name__!r} constructor '
                                'should be classes')

        return super().__new__(cls, 'TypeEnforcer', (_TypeEnforcer,),
                               {'_allowed_types': tuple(args)})

    @classmethod
    def make_bases(cls, name, bases):
        # sneakily place `_TypeEnforcer` ahead of `Container` types in the
        # inheritance order so that type checking happens on __init__ of classes
        # with this metaclass

        # TODO: might want to do the same for ObjectArray1d.  If you register
        #   your classes as ABCs you can do this in one foul swoop!

        # also check if there is another TypeEnforcer in the list of bases and
        # make sure the `_allowed_types` are consistent - if any is a subclass
        # of a type in the already defined `_allowed_types` higher up
        # TypeEnforcer this is allowed, else raise TypeError since it will lead
        # to type enforcement being done for different types at different levels
        # in the class heirarchy
        ite = None
        ic = None
        currently_allowed_types = []
        # enforcers = []
        # base_enforcers = []
        # indices = []
        # new_bases = list(bases)
        for i, base in enumerate(bases):
            if issubclass(base, col.Container):
                ic = i

            if isinstance(base, cls):
                # _TypeEnforcer !
                requested_allowed_types = base._allowed_types
                ite = i

            # look for other `_TypeEnforcer`s in the inheritance diagram so we
            # consolidate the type checking
            for bb in base.__bases__:
                if isinstance(bb, cls):
                    # this is a `_TypeEnforcer` base
                    currently_allowed_types.extend(bb._allowed_types)
                    # base_enforcers.append(bb)
                    # original_base = base

        # print('=' * 80)
        # print(name, bases)
        # print('requested', requested_allowed_types)
        # print('current', currently_allowed_types)

        # deal with multiple enforcers
        # en0, *enforcers = enforcers
        # ite, *indices = indices
        # if len(enforcers) > 0:
        #     # multiple enforcers defined like this:
        #     # >>> class Foo(list, OfType(int), OfType(float))
        #     # instead of like this:
        #     # >>> class Foo(list, OfType(int, float))
        #     # merge type checking
        #     warnings.warn(f'Multiple `TypeEnforcer`s in bases of {name}. '
        #                   'Please use `OfType(clsA, clsB)` to allow multiple '
        #                   'types in your containers')

        #     for i, ix in enumerate(indices):
        #         new_bases.pop(ix - i)

        # consolidate allowed types
        if currently_allowed_types:
            # new_allowed_types = []
            # loop through currently allowed types
            for allowed in currently_allowed_types:
                for new in requested_allowed_types:
                    if issubclass(new, allowed):
                        # type restriction requested is a subclass of already
                        # existing restriction type.  This means we narrow the
                        # restriction to the new (subclass) type
                        # new_allowed_types.append(new)
                        break
                    else:
                        # requested restriction is a new type unrelated to
                        # existing restriction
                        raise TypeError(
                            f'Multiple type restrictions ({new}, {allowed}) '
                            'requested in different bases of container class '
                            f'{name}.')  # To allow multiple
            #     else:
            #         new_allowed_types.append(allowed)
            # #
            # print('new', new_allowed_types)
            # print('new_bases', new_bases)

        #     bases = tuple(new_bases)
        # else:
        #     # set new allowed types
        #     bases[ite]._allowed_types = requested_allowed_types

        if (ite is None) or (ic is None):
            return bases

        if ic < ite:
            # _TypeEnforcer is before UserList in inheritance order so that
            # types get checked before initialization of the `Container`
            _bases = list(bases)
            _bases.insert(ic, _bases.pop(ite))
            # print('new_bases', _bases)
            return tuple(_bases)

        return bases


# alias
OfType = OfTypes


class _TypeEnforcer:
    """
    Item type checking mixin for list-like containers
    """

    _allowed_types = (object, )    # placeholder

    def __init__(self, items):
        super().__init__(self.checks_type(items))

    def checks_type(self, itr, raises=None, warns=None, silent=None):
        """Generator that checks types"""
        if raises is warns is silent is None:
            raises = True   # default behaviour : raise TypeError

        if raises:
            emit = bork(TypeError)
        elif warns:
            emit = warnings.warn
        elif silent:
            emit = _echo  # silently ignore

        for i, obj in enumerate(itr):
            self.check_type(obj, i, emit)
            yield obj

    def check_type(self, obj, i='', emit=bork(TypeError)):
        """Type checker"""
        if not isinstance(obj, self._allowed_types):
            many = len(self._allowed_types) > 1
            ok = tuple(map(str, self._allowed_types))[[0, slice(None)][many]]
            emit(f'Items in container class {self.__class__.__name__!r} must '
                 f'derive from {"one of" if many else ""} {ok}. '
                 f'Item {i}{" " * bool(i)}is of type {type(obj)!r}.')

    def append(self, item):
        self.check_type(item, len(self))
        super().append(item)

    def extend(self, itr):
        super().extend(self.checks_type(itr))


class ReprContainer:
    """
    Flexible string representation for list-like containers.  This object can
    act as a replacement for the builtin `__repr__` or `__str__` methods.
    Inherit from `ReprContainerMixin` to get pretty representations of
    your container built in.
    """

    format = '{pre}: {joined}'
    max_width = 120
    edge_items = 2
    wrap = True
    max_items = 50
    max_lines = 3

    def __init__(self, parent, alias=None, sep=', ', brackets='[]',
                 show_size=True):
        self.parent = parent
        self.name = alias or parent.__class__.__name__
        self.sep = str(sep)
        if brackets is None:
            brackets = ('', '')
        self.brackets = tuple(brackets)
        assert len(self.brackets) == 2
        self.show_size = bool(show_size)

    def __call__(self):
        return self.format.format(
            **self.__dict__,
            **{name: p.fget(self) for name, p in
               inspect.getmembers(self.__class__, is_property)})

    def __str__(self):
        return self()

    def __repr__(self):
        return self()

    def item_str(self, item):
        return str(item)

    @property
    def sized(self):
        if self.show_size:
            return '(size %i)' % len(self.parent)
        return ''

    @property
    def pre(self):
        return self.name + self.sized

    @property
    def joined(self):
        n_per_line = 0
        if len(self.parent):
            first = self.item_str(self.parent[0])
            n_per_line = self.max_width // (len(first) + len(self.sep))

        if len(self.parent) > n_per_line:
            line_count = 1  # start counting here so we break 1 line early
            if self.wrap:
                s = ''
                w_pre = len(self.pre) + 3
                newline = '\n' + ' ' * w_pre
                loc = w_pre
                end = self.max_items - self.edge_items
                for i, item in enumerate(self.parent):
                    si = self.item_str(item)
                    if i > end:
                        s += ' ... ' + self.sep
                        s += self._joined(self.parent[-self.edge_items:])
                        break

                    if loc + len(si) > self.max_width:
                        s += newline
                        loc = w_pre
                        line_count += 1
                        if line_count >= self.max_lines:
                            s += ' ... ' + self.sep
                            s += self._joined(self.parent[-self.edge_items:])
                            # todo: can probably print more edge items here
                            break

                    s += si + self.sep
                    loc += len(si + self.sep)

                s = s.strip(self.sep)

                # if i > end:
                #     s += self.parent[-self.edge_items:]

                # for j0 in range(0, len(self.parent), n_per_line):
                #     j1 = j0 + n_per_line
                #     if j1 > imx:
                #         s += ' ... ' + newline
                #         break
                #     s += self._joined(self.parent[j0: j1]) + newline
                #
                # if j1 > imx:
                #     s += self._joined(self.parent[j0:])
                # else:
                #     s = s.rstrip(newline)

                # s += self._joined(self.parent[j0:])
                # else:
                #     s += self._joined(self.parent[-n_per_line:])

                # if i1 > imx:

                # else:
                #     s += self._joined(self.parent[i0:])

                return s.join(self.brackets)

            return ' ... '.join((self._joined(self.parent[:self.edge_items]),
                                 self._joined(self.parent[-self.edge_items:]))
                                ).join(self.brackets)

        return self._joined(self.parent).join(self.brackets)

    def _joined(self, items):
        return self.sep.join(map(str, (map(self.item_str, items))))


class ReprContainerMixin:
    """
    If you inherit from this class, add
    >>> self._repr = ReprContainer(self)
    to your `__init__` method, and add  whatever option you want for the
    representation. If your container is an attribute of another class, use
    >>> self._repr = ReprContainer(self.data)
    where 'self.data' is the container you want to represent
    """
    _repr = None

    def __repr__(self):
        if self._repr is None:
            self._repr = ReprContainer(self)  # this is just the default.

        return self._repr()

    # def pprint(self):


class ItemGetter:  # ItemGetterMixin ?
    """
    Container that supports vectorized item getting like numpy arrays
    """
    _returned_type = None

    @classmethod
    def set_returned_type(cls, obj):
        """Will change the type returned by __getitem__"""
        cls._returned_type = obj

    @classmethod
    def get_returned_type(cls):
        """
        Return the class that wraps objects returned by __getitem__.
        Default is to return this class itself, so that
        `type(obj[[1]]) == type(obj)`

        This is useful for subclasses that overwrite `__init__` and don't
        want re-run initialization code
        """
        return cls._returned_type or cls

    def __getitem__(self, key):
        getitem = super().__getitem__
        #
        if (isinstance(key, numbers.Integral)
                and not isinstance(key, (bool, np.bool))):
            return getitem(key)

        if isinstance(key, (slice, type(...))):
            items = getitem(key)

        elif isinstance(key, (list, tuple)):
            # if multiple item retrieval vectorizer!
            items = [getitem(k) for k in key]

        elif isinstance(key, np.ndarray):
            if key.ndim != 1:
                raise ValueError('Only 1D indexing arrays are allowed')
            if key.dtype.kind == 'b':
                key, = np.where(key)
            if key.dtype.kind == 'i':
                items = [getitem(k) for k in key]
            else:
                raise ValueError(
                    'Index arrays should be of type float or bool')
        else:
            raise TypeError('Invalid index type %r' % type(key))

        # wrap in required type
        return self.get_returned_type()(items)


class ContainerWrapper(ItemGetter):

    _wraps = list
    # if you use this class without changing this class attribute, you may as
    # well just use UserList

    def __init__(self, items):
        self.data = self._wraps(items)

    def __len__(self):
        return len(self.data)


class ArrayLike1D(ItemGetter, col.UserList):
    """
    A container class where the that emulates a one dimensional numpy array,
    providing all the array slicing niceties.

    Provides the following list-like functionality:
    >>> c = ArrayLike1D([1, 2, 3])
    >>> three = c.pop(-1)
    >>> c.append(id)
    >>> c.extend(['some', 'other', object])
    multi-index slicing ala numpy
    >>> c[[0, 3, 5]]    # [1, <function id(obj, /)>, 'other']

    Attributes
    ----------
    data: np.ndarray
        The object container

    Note
    ----
    The append and extend methods will not work when appending array-like 
    objects since numpy will (try to) flatten them before appending.  If you 
    need vectorized item getting as well as support for having array-like
    objects in you container, inherit from `UserList` and `ItemGetter`
    """
    pass


# class ObjectArray1D(ItemGetter):
#     # NOTE: DEPRECATED
#     """
#     A container class where the main container is a 1D numpy object array
#     providing all the array slicing niceties.

#     Provides the following list-like functionality:
#     >>> c = ObjectArray1D([1, 2, 3])
#     >>> three = c.pop(-1)
#     >>> c.append(id)
#     >>> c.extend(['some', 'other', object])
#     multi-index slicing ala numpy
#     >>> c[[0, 3, 5]]    # [1, <function id(obj, /)>, 'other']

#     Attributes
#     ----------
#     data: np.ndarray
#         The object container

#     Note
#     ----
#     The append and extend methods will not work when appending array-like
#     objects since numpy will (try to) flatten them before appending.  If you
#     need vectorized item getting as well as support for having array-like
#     objects in you container, inherit from `UserList` and `ItemGetter`
#     """

#     # TODO: what if i want a different name for my container?
#     # TODO: __slots__

#     def __init__(self, items):
#         self.data = np.array(items, dtype='O')

#     def __len__(self):
#         return len(self.data)

#     def __getitem__(self, key):
#         items = self.data[key]
#         if isinstance(key, numbers.Integral):
#             return items

#         # if multiple items from the container was retrieved
#         return self.get_returned_type()(items)

#     def pop(self, i):
#         return np.delete(self.data, i)

#     def append(self, item):
#         # todo: type enforcement
#         self.data = np.append(self.data, [item])

#     def extend(self, itr):
#         # todo: type enforcement
#         self.data = np.hstack([self.data, list(itr)])


class MethodCaller:
    """
    This is adapted from `operator.methodcaller`. The code below is copied
    verbatim from 'operator.py' (since you can't inherit from
    `operator.methodcaller!`) with only the `__call__` method altered to support
    chained attribute lookup like:
    >>> MethodCaller('foo.bar.func', *args, **kws)(object)

    Return a callable object that calls the given method on its operand.
    After f = methodcaller('name'), the call f(r) returns r.name().
    After g = methodcaller('name', 'date', foo=1), the call g(r) returns
    r.name('date', foo=1).
    """
    __slots__ = ('_name', '_args', '_kwargs')

    def __init__(*args, **kwargs):
        if len(args) < 2:
            msg = ("%s needs at least one argument, the method name"
                   % args[0].__class__.__name__)
            raise TypeError(msg)
        self = args[0]
        self._name = args[1]
        if not isinstance(self._name, str):
            raise TypeError('method name must be a string')
        self._args = args[2:]
        self._kwargs = kwargs

    def __call__(self, obj):
        return op.attrgetter(self._name)(obj)(*self._args, **self._kwargs)

    def __repr__(self):
        args = [repr(self._name)]
        args.extend(map(repr, self._args))
        args.extend('%s=%r' % (k, v) for k, v in self._kwargs.items())
        return '%s.%s(%s)' % (self.__class__.__module__,
                              self.__class__.__name__,
                              ', '.join(args))

    def __reduce__(self):
        if not self._kwargs:
            return self.__class__, (self._name,) + self._args
        else:
            return ftl.partial(self.__class__, self._name,
                               **self._kwargs), self._args

# update c
# MethodCaller.__doc__ += op.methodcaller.__doc__.replace('methodcaller', 'MethodCaller')


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


class AttrMapper:
    """
    This is a mixin class for containers that allows getting attributes from
    the objects in the container. i.e vectorized attribute lookup across
    contained objects, as well as vectorized method calls.

    This example demonstrates basic usage
    >>> import time
    >>> class MyList(list, AttrMapper):
    >>>        pass

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
            get_value = _echo

            # check values are same length as container before we attempt to set
            # any attributes
            if set(map(len, kws.values())) != len(self):
                raise ValueError('Not all values are the same length as the '
                                 'container while `each` has been set.')

        for key, value in kws.items():
            *chained, attr = key.rsplit('.', 1)
            if chained:
                get_parent = op.attrgetter(chained[0])
            else:
                get_parent = _echo

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

    Example
    -------
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

    def __init__(self, name, convert=_echo):
        self.name = name
        self.convert = convert

    def __get__(self, obj, kls=None):
        if obj is None:
            # class attribute lookup
            return self

        # instance attribute lookup
        return self.convert(obj.attrs(self.name))


class Grouped(OrderedDict):
    """
    Emulates dict to hold multiple container instances keyed by their
    common attribute values. The attribute names given in group_id are the
    ones by which the run is separated into segments (which are also container
    instances).
    """

    group_id = ()

    # This class should never be instantiated directly, only by the new_group
    # method of AttrGrouper, which sets `group_id`

    def __init__(self, factory, *args, **kws):
        """
        note: the init arguments here do not do what you they normally do for
        the construction of a dict-like object. Objects of this type are
        always instantiated empty. This class should never be
        instantiated directly with keywords from the user, only by the
        new_group  method of AttrGrouper.
        `keys` and `kws` are the "context" by which the grouping is done.
        Keep track of this so we have this info available later for pprint
        and optimization
        """

        if not callable(factory):
            raise TypeError('Factory (first argument) must be a callable')
        self.factory = factory

        super().__init__(*args, **kws)

    # def make_container(self):
    #    monkey patch containers with grouping context?

    def __repr__(self):
        return pformat(self, self.__class__.__name__)

    def to_list(self):
        """
        Concatenate values to container.  Container type is determined by
        `default_factory`
        """
        # construct container
        list_like = self.factory()
        # filter None since we use that to represent empty group
        for obj in filter(None, self.values()):
            list_like.extend(obj)
        return list_like

    def group_by(self, *keys, return_index=False, **kws):
        # logic='AND'
        """
        (Re-)group by attributes

        Parameters
        ----------
        keys

        Returns
        -------

        """
        return self.to_list().group_by(*keys, return_index=return_index, **kws)

    def select_by(self,logic='AND',  **kws):
        """
        Select the files with attribute value pairs equal to those passed as
        keywords.  Eg: g.select_by(binning='8x8').  Keep the original
        grouping for the selected files.

        Parameters
        ----------
        kws

        Returns
        -------

        """
        return self.to_list().select_by(logic, **kws).group_by(*self.group_id)

    def varies_by(self, *keys):
        """
        Check whether the attribute value mapped to by `key` varies across
        the set of observing runs

        Parameters
        ----------
        key

        Returns
        -------
        bool
        """
        values = set()
        for o in filter(None, self.values()):
            vals = set(o.attrs(*keys))
            if len(vals) > 1:
                return True
            else:
                values |= vals
            if len(values) > 1:
                return True
        return False

    # def filter_duplicates(self):
    #     if len(set(map(id, self))) == len(self):
    #         return self  # all items are unique
    #     #
    #     return self.__class__(self.factory,
    #                           *(next(it) for _, it in itt.groupby(self, id)))


class AttrGrouper(AttrMapper):
    """
    Abstraction layer that can group, split and sort multiple data sets
    """


    def new_groups(self, *args, **kws):
        """
        Construct a new group mapping for items in the container.
        Subclasses can overwrite, but whatever is returned by this method
        should be a subclass of `Grouped` in order to merge back to
        containers of the same type and have direct accees to regrouping
        method `group_by`.
        """
        return Grouped(self.__class__)  # , *keys, **kws

    def group_by(self, *keys, return_index=False, **kws):
        """
        Separate a run according to the attribute given in keys.
        keys can be a tuple of attributes (str), in which case it will
        separate into runs with a unique combination of these attributes.

        Parameters
        ----------
        keys: str, callable or tuple
            each item should be either str or callable
        kws:
            each key should be an attribute of the contained objects
            each item should be callable
        return_index: bool
            whether to return the indices of the original position of objects as
             a grouped dict


        Returns
        -------
        att_dic: dict
            (val, run) pairs where val is a tuple of attribute values mapped
            to by `keys` and run is the shocRun containing observations which
            all share the same attribute values
        flag:
            1 if attrs different for any cube in the run, 0 all have the same
            attrs

        """
        vals = get_sort_values(self, *keys, **kws)

        # use DefaultOrderedDict to preserve order among groups
        groups = DefaultOrderedDict(self.__class__)  # keys, **kws
        groups.group_id = keys, kws
        indices = DefaultOrderedDict(list)

        # if self.group_id == keys:  # is already separated by this key
        att_set = set(vals)  # unique set of key attribute values
        if len(att_set) == 1:
            # NOTE: can eliminate this block if you don't mind re-initializing
            # all contained objects have the same attribute (key) value(s)
            # self.group_id = keys
            groups[vals[0]] = self
            indices[vals[0]] = list(range(len(self)))
        else:
            # key attributes are not equal across all containers
            # get indices of elements in this group.
            # list comp for-loop needed for tuple attrs
            for i, (item, a) in enumerate(zip(self, vals)):
                groups[a].append(item)
                indices[a].append(i)

        g = self.new_groups()
        g.update(groups)

        if return_index:
            return g, indices
        return g

    def sort_by(self, *keys, **kws):
        """
        Sort the items by the value of attributes given in keys,
        kws can be (attribute, callable) pairs in which case sorting will be
         done according to value returned by callable on a given attribute.
        """

        vals = get_sort_values(self, *keys, **kws)
        # if not len(vals):
        #     raise ValueError('No attribute name(s) or function(s) to group by.')

        # NOTE: support for python 3.6+ only
        # For python <3.6 order of kwargs is lost when passing to a function,
        # so this function may not work as expected for sorting on multiple
        # attributes.
        # see: https://docs.python.org/3/whatsnew/3.6.html
        idx, _ = zip(*sorted(enumerate(vals), key=op.itemgetter(1)))
        return self[list(idx)]

    def select_by(self, logic='AND', **kws):

        logic = SELECT_LOGIC[logic.upper()]

        selection = np.ones(len(self))
        for att, seek in kws.items():
            vals = self.attrs(att)
            if not callable(seek):
                seek = seek.__eq__

            selection = logic(selection, list(map(seek, vals)))
        #
        return self[selection]


def get_sort_values(self, *keys, **kws):
    vals = []
    # get value tuples for grouping
    for key_or_func in keys:
        # functions given as keywords take precedent over attribute names
        # when grouping
        if isinstance(key_or_func, str):
            vals.append(map(op.attrgetter(key_or_func), self))

        elif isinstance(key_or_func, col.Callable):
            vals.append(map(key_or_func, self))
        else:
            raise ValueError('Key values must be str (attribute name on '
                             'item) or callable (evaluated on item).')

    if kws:
        for fun, val in zip(kws.values(), zip(*self.attrs(*kws.keys()))):
            vals.append(map(fun, val))

    if not len(vals):
        raise ValueError('No attribute name(s) or function(s) to sort by.')

    # keys = OrderedSet(keys)
    # make sure we don't end up with 1-tuples as our group ids when grouping
    # with single function / attribute
    unpack = tuple if len(vals) == 1 else zip
    return list(unpack(*vals))


class Container(ArrayLike1D, SelfAwareContainer, AttrGrouper,
                ReprContainerMixin, LoggingMixin):
    """Good container"""

    def __init__(self, list_=()):
        # init container
        ArrayLike1D.__init__(self, list_)
