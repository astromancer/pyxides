"""
Container magic
"""

import abc
from collections import UserList
import numbers
from .dicts import DefaultOrderedDict
import itertools as itt
import operator as op
import inspect
from collections import Callable
import functools as ftl

import numpy as np

from recipes.logging import LoggingMixin
from .sets import OrderedSet
from .dicts import pformat


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

class SelfAwareContainer(object):
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


# class OfTypes(object):
#     def __new__(cls, item_types):
#         cls._item_types = tuple(item_types)
#         return TypeEnforcer

# def OfTypes(item_types):

def base_order(kls):
    if issubclass(kls, _TypeEnforcer):
        return 0

    if issubclass(kls, UserList):
        return 1

    return 1    

class OfTypes(abc.ABCMeta):
    # NOTE: inherit from ABCMeta to avoid metaclass conflict with UserList which
    # has metaclass abc.ABCMeta
    """
    Factory that creates TypeEnforcer classes. Allows for the following usage
    pattern: 
    >>> class Container(UserList, OfTypes(int)): pass
    which creates a container class `Container` that will only allow integer 
    items inside. This constructor assigns a tuple of allowed types as class
     attribute `_item_types`
    """

    def __new__(mcs, *args):

        if isinstance(args[0], str):
            # This results from an internal call during class construction
            name, bases, attrs = args
            # sneakily place `_TypeEnforcer` ahead of `UserList` in the
            # inheritance order so that type checking happens on init
            bases = tuple(sorted(bases, key=base_order))
            # create class
            return super().__new__(mcs, name, bases, attrs)

        # we are here if invoked by direct call:
        # cls = OfTypes(int)

        # create TypeEnforcer class. args gives allowed types
        # `_item_types` class attribute set to tuple of allowed types
        return super().__new__(mcs, 'TypeEnforcer', (_TypeEnforcer,),
                               {'_item_types': tuple(args)})


# alias
OfType = OfTypes


class _TypeEnforcer(object):
    # TODO: inherit from abc.ABC / abc.Container
    """
    Item type checking mixin for list-like containers
    """

    _item_types = (object, )    # placeholder

    def __init__(self, items):
        super().__init__(self.checked_types(items))

    def checked_types(self, itr):
        for i, obj in enumerate(itr):
            self.check_type(obj, i)
            yield obj

    def check_type(self, obj, i):
        if not isinstance(obj, self._item_types):
            many = len(self._item_types) > 1
            raise TypeError(
                f'Items contained in {self.__class__.__name__!r} must derive '
                f'from {"one of" if many else ""}'
                f'{self._item_types[[0, slice(None)][many]]}. '
                f'Item {i} is of type {type(obj)!r}.')

    def append(self, item):
        self.check_type(item, len(self))
        super().append(item)

    def extend(self, itr):
        super().extend(self.checked_types(itr))


class ReprContainer(object):
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


class ReprContainerMixin(object):
    """
    If you inherit from this class, add
    >>> self._repr = ReprContainer(self)
    to your `__init__` method., nd add  whatever option you want for the
    representation.  If your container is an attribute of another class, use
    >>> self._repr = ReprContainer(self.data)
    where 'self.data' is the container you want to represent
    """
    _repr = None

    def __repr__(self):
        if self._repr is None:
            self._repr = ReprContainer(self)  # this is just the default.

        return self._repr()

    # def pprint(self):


class ItemGetter(object):
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
        if isinstance(key, numbers.Integral):
            # single item retrieval
            return getitem(key)
        elif isinstance(key, list):
            # if multiple item retrieval
            items = [getitem(k) for k in key]
        elif isinstance(key, np.ndarray):
            if key.ndim != 1:
                raise ValueError('Only 1D indexing arrays are allowed')
            items = [getitem(k) for k in key]
        else:
            raise TypeError('Invalid index type %r' % type(key))
        return self.get_returned_type()(items)


class ContainerWrapper(ItemGetter):

    _wraps = list
    # if you use this class without changing this class attribute, you may as
    # well just use UserList

    def __init__(self, items):
        self.data = self._wraps(items)

    def __len__(self):
        return len(self.data)


class ObjectArray1D(ItemGetter):
    """
    A container class where the main container is a 1D numpy object array
    providing all the array slicing niceties.

    Provides the following list-like functionality:
    >>> c = ObjectArray1D([1, 2, 3])
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

    # TODO: what if i want a different name for my container?
    # TODO: __slots__

    def __init__(self, items):
        self.data = np.array(items, dtype='O')

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        items = self.data[key]
        if isinstance(key, numbers.Integral):
            return items

        # if multiple items from the container was retrieved
        return self.get_returned_type()(items)

    def pop(self, i):
        return np.delete(self.data, i)

    def append(self, item):
        # todo: type enforcement
        self.data = np.append(self.data, [item])

    def extend(self, itr):
        # todo: type enforcement
        self.data = np.hstack([self.data, list(itr)])


class MethodCaller(object):
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


class CallVectorizer(object):
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


class AttrMapper(object):
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
            Chaining attribute  lookup via '.'-separated strings is also
            permitted.  eg:. 'hello.world' will look up the 'world' attribute
            on the object in the 'hello' slot for each of the items in the
            container.


        Returns
        -------

        """

        return list(self.attrs_gen(*keys))

    def attrs_gen(self, *keys):
        yield from map(op.attrgetter(*keys), self)

    def set_attrs(self, **kws):
        """
        Set attributes

        Parameters
        ----------
        keys: container or iterable
            attribute names to be set.  can be chained '_.like.this'
        values: container or iterable
            values to be assigned
        kws:
            (key, values) as defined above
        """

        # kws.update(zip(keys, values)) # check if sequences else error prone
        for key, val in kws.items():
            *chained, attr = key.rsplit('.', 1)
            if len(chained):
                get_parent = op.attrgetter(chained[0])
            else:
                get_parent = _echo

            for o in self:
                setattr(get_parent(o), attr, val)

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


class AttrTable(object):
    """
    Abstraction layer that can group, split and merge multiple data sets
    """

    def _get_input(self, obj):
        if obj is None:
            return dict()

        if isinstance(obj, dict):
            return obj

        return dict(zip(self.attrs, obj))  # TODO : ordered dict better

    def __init__(self, attrs, column_headers=None, formatters=None, **kws):

        self.attrs = list(attrs)
        self.kws = kws  # set default keywords here

        self.formatters = self._get_input(formatters)
        self.headers = self._get_input(column_headers)

        self.headers = dict(zip(attrs, self.get_headers(attrs)))

        # set default options for table
        for key, val in dict(row_nrs=0,
                             precision=5,
                             minimalist=True,
                             compact=True,
                             ).items():
            self.kws.setdefault(key, val)

    def __call__(self, container, attrs=None, **kws):
        """
        Print the table of attributes for this container as a table.

        Parameters
        ----------
        attrs: array_like, optional
            Attributes of the instance that will be printed in the table.
            defaults to the list given upon initialization of the class.
        **kws:
            Keyword arguments passed directly to the `motley.table.Table`
            constructor.

        Returns
        -------


        """
        if not hasattr(container, 'attrs'):
            raise TypeError('Container does not support vectorized attribute '
                            'lookup on items.')

        table = self.get_table(container, attrs, **kws)
        print(table)
        return table

    def get_table(self, container, attrs=None, **kws):
        """
        Keyword arguments passed directly to the `motley.table.Table`
            constructor.

        Returns
        -------
        `motley.table.Table` instance
        """

        from motley.table import Table

        if len(container) == 0:
            return Table(['Empty'])

        if attrs is None:
            attrs = self.attrs

        # print('BEFORE', kws['formatters'])
        kws.setdefault('title', container.__class__.__name__)
        kws.setdefault('col_headers', self.get_headers(attrs))
        kws.setdefault('formatters', self.get_formatters(attrs))
        kws.setdefault('col_groups', self.get_col_groups(attrs))
        # print('AFTER', kws['formatters'])

        kws_ = self.kws.copy()
        kws_.update(**kws)
        # print(kws_['total'])

        return Table(container.attrs(*attrs), **kws_)

    def get_headers(self, attrs):
        heads = []
        for a in attrs:
            head = self.headers.get(a, a.split('.')[-1])
            heads.append(head)
        return heads

    def get_col_groups(self, attrs):
        groups = []
        for a in attrs:
            parts = a.split('.')
            groups.append(parts[0] if len(parts) > 1 else '')
        return groups

    def get_formatters(self, attrs):
        return [self.formatters.get(a, str) for a in attrs]
        # fmt = []
        # for a in attrs:
        #     # will auto format if no formatter
        #     if a in self.formatters:
        #         fmt[self.headers.get(a, a)] = self.formatters[a]
        #
        # return fmt

    def add_attr(self, attr, column_header=None, formatter=None):

        if not isinstance(attr, str):
            raise ValueError('Attribute must be a str')

        # block below will bork with empty containers
        # obj = self.parent[0]
        # if not hasattr(obj, attr):
        #     raise ValueError('%r is not a valid attribute of object of '
        #                      'type %r' % (attr, obj.__class__.__name__))

        # avoid duplication
        if attr not in self.attrs:
            self.attrs.append(attr)

        if column_header is None:
            column_header = attr  # FIXME split here

        self.headers[attr] = column_header
        if formatter is not None:
            self.formatters[column_header] = formatter


#


def get_sort_values(self, *keys, **kws):
    vals = []
    # get value tuples for grouping
    for key_or_func in keys:
        # functions given as keywords take precedent over attribute names
        # when grouping
        if isinstance(key_or_func, str):
            vals.append(map(op.attrgetter(key_or_func), self))

        elif isinstance(key_or_func, Callable):
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


class AttrGrouper(AttrMapper):
    # group_id = None

    # @property
    # def group_id(self):
    #     return self._group_id
    #
    # @group_id.setter
    # def group_id(self, group_id):
    #     self._group_id = OrderedSet(group_id)

    def new_groups(self):  # , *keys, **kws
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
        groups = self.new_groups()  # keys, **kws
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

        if return_index:
            return groups, indices
        return groups

    def sort_by(self, *keys, **kws):
        """
        Sort the cubes by the value of attributes given in keys,
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
        idx, svals = zip(*sorted(enumerate(vals), key=op.itemgetter(1)))
        return self[list(idx)]


class Grouped(DefaultOrderedDict):
    """
    Emulates dict to hold multiple container instances keyed by their
    common attribute values. The attribute names given in group_id are the
    ones by which the run is separated into segments (which are also container
    instances).
    """

    group_id = None

    # This class should never be instantiated directly, only by the new_group
    # method of AttrGrouper, which sets `group_id`

    # def __init__(self, default_factory=None, *keys, **kws):
    #     """
    #     note: the init arguments here do not do what you they normally do for
    #     the construction of a dict-like object. Objects of this type are
    #     always instantiated empty. This class should never be
    #     instantiated directly with keywords from the user, only by the
    #     new_group  method of AttrGrouper.
    #     `keys` and `kws` are the "context" by which the grouping is done.
    #     Keep track of this so we have this info available later for pprint
    #     and optimization
    #     """
    #     super().__init__(default_factory)
    #     self._keys = keys
    #     self._kws = kws

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
        list_like = self.default_factory()
        # filter None since we use that to represent empty group
        for obj in filter(None, self.values()):
            list_like.extend(obj)
        return list_like

    def group_by(self, *keys, return_index=False, **kws):
        # logic='AND', **kws)
        """
        (Re-)group by attributes

        Parameters
        ----------
        keys

        Returns
        -------

        """
        return self.to_list().group_by(*keys, return_index=return_index, **kws)

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

    def select_by(self, **kws):
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
        # if bool(keys) == bool(kws):
        #     raise ValueError('Grouping cannot be done using both attribute '
        #                      'values *and* function evaluation on attribute '
        #                      'values. Please pass only `keys` or only `kws` '
        #                      'to this function (either, not both, not neither)
        #                      ')

        out = self.__class__()

        # TODO!!!

        for key, obs in self.items():
            print(obs.attrs(*keys))
            if obs.attrs(*keys) == value_set:
                out[key] = obs
        return out

    def filter_by(self, **kws):
        # can probably merge with select_by
        attrs = self.attrs(*kws.keys())
        funcs = kws.values()
        def predicate(att): return all(f(at) for f, at in zip(funcs, att))
        selection = list(map(predicate, attrs))
        return self[selection]

    def filter_duplicates(self):
        if len(set(map(id, self))) == len(self):
            return self  # all items are unique
        #
        return self.__class__([next(it) for _, it in itt.groupby(self, id)])


class Container(ObjectArray1D, SelfAwareContainer, AttrGrouper,
                ReprContainerMixin, LoggingMixin):
    """Good container"""

    def __init__(self, list_=None):

        if list_ is None:
            list_ = []

        # make sure objects derive from _BaseHDU
        # TypeEnforcer(_BaseHDU)(list_)

        # init container
        ObjectArray1D.__init__(self, list_)
