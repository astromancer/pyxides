"""
Classes for grouping containers
"""

# std libs
import operator as op
import functools as ftl
import itertools as itt
from collections import abc

# third-party libs
import numpy as np

# local libs
from recipes.dicts import DefaultOrderedDict, pformat

# relative libs
from .vectorize import AttrMapper


SELECT_LOGIC = {'AND': np.logical_and,
                'OR': np.logical_or,
                'XOR': np.logical_xor}


class Groups(DefaultOrderedDict):
    """
    Emulates dict to hold multiple container instances keyed by their
    common attribute values. The attribute names given in group_id are the
    ones by which the run is separated into segments (which are also container
    instances).
    """

    group_id = (), {}

    # This class should never be instantiated directly, only by the new_group
    # method of AttrGrouper, which sets `group_id`

    def __init__(self, factory=None, mapping=(), **kws):
        """
        note: the init arguments here do not do what you they normally do for
        the construction of a dict-like object. Objects of this type are
        always instantiated empty. This class should never be
        instantiated directly with keywords from the user, only by the
        `new_groups`  method of AttrGrouper.

        `keys` and `kws` are the "context" by which the grouping is done.
        Keep track of this so we have this info available later for pprint
        and optimization.
        """

        super().__init__(factory, mapping, **kws)

    def __repr__(self):
        return pformat(self, self.__class__.__name__)

    def at(self, index):
        """
        Get the value at index position. This enables list-like item getting for
        integer keys which is useful if the keys for the grouping are too
        complex to easily type.

        Parameters
        ----------
        index : int
        """
        return next(itt.islice(iter(self.values()), index, index + 1))

    def to_list(self):
        """
        Concatenate values to single list-like container. Returned container
        type is determined by `default_factory` function.
        """
        # construct container
        list_like = self.default_factory()
        # filter None since we use that to represent empty group
        for obj in filter(None, self.values()):
            if isinstance(obj, type(list_like)):
                list_like.extend(obj)
            else:
                list_like.append(obj)
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

    def select_by(self, logic='AND',  **kws):
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

    def map(self, func, *args, **kws):
        # runs an arbitrary function on each shocCampaign in the group
        assert callable(func)
        out = self.__class__(self.default_factory)
        out.group_id = self.group_id

        for key, obj in self.items():
            out[key] = None if obj is None else func(obj, *args, **kws)
        return out

    def calls(self, name, *args, **kws):
        """
        For each group of observations (shocCampaign), call the
        method with name `name`  passing  `args` and `kws`.

        Parameters
        ----------
        name
        args
        kws

        Returns
        -------

        """

        def run_method(obj, *args, **kws):
            return getattr(obj, name)(*args, **kws)

        return self.map(run_method, *args, **kws)

    def attrs(self, *keys):
        out = {}
        for key, obj in self.items():
            if obj is None:
                out[key] = None
            elif isinstance(obj, AttrMapper):
                out[key] = obj.attrs(*keys)
            else:
                out[key] = op.attrgetter(*keys)(obj)
        return out


class AttrGrouper(AttrMapper):
    """
    Abstraction layer that can group, split and sort multiple data sets
    """
    @classmethod
    def new_groups(cls, *args, **kws):
        """
        Construct a new group mapping for items in the container.
        Subclasses can overwrite, but whatever is returned by this method
        should be a subclass of `Groups` in order to merge back to
        containers of the same type and have direct accees to regrouping
        method `group_by`.
        """
        return Groups(cls, *args, **kws)

    def group_by(self, *keys, return_index=False, **kws):
        """
        Separate a container according to the attribute given in keys.
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
        g = self.new_groups()
        if len(keys) == 1 and isinstance(keys[0], g.__class__):
            keys, kws = keys[0].group_id
            # group_like() better?

        vals = get_sort_values(self, *keys, **kws)

        # use DefaultOrderedDict to preserve order amongst groups
        # default factory makes another object of this class ie. container with
        # grouping ability
        groups = DefaultOrderedDict(self.__class__)
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

        #
        g.update(groups)
        g.group_id = keys, kws
        # turn off the default factory, since we are done adding items now
        # g.default_factory = None # NOTE: need default_factory for to_list!
        # indices.default_factory = None

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
        if not kws:
            raise ValueError('No criteria for selection provided.')

        logic = SELECT_LOGIC[logic.upper()]
        selection = np.ones(len(self), bool)
        for att, seek in kws.items():
            vals = self.attrs(att)
            if not callable(seek):
                seek = ftl.partial(op.eq, seek)

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

        elif isinstance(key_or_func, abc.Callable):
            vals.append(map(key_or_func, self))
        else:
            raise ValueError(
                'Key values must either be str (attribute(s) of item) '
                'or callable (evaluated per item).'
            )

    if kws:
        for fun, val in zip(kws.values(), zip(*self.attrs(*kws.keys()))):
            vals.append(map(fun, val))

    if not vals:
        raise ValueError('No attribute name(s) or function(s) to sort by.')

    # keys = OrderedSet(keys)
    # make sure we don't end up with 1-tuples as our group ids when grouping
    # with single function / attribute
    unpack = tuple if len(vals) == 1 else zip
    return list(unpack(*vals))
