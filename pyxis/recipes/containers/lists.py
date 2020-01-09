"""
Recipes involving lists
"""

# std libs
import re
import operator
import functools
import itertools as itt
import collections as coll

# third-party libs
import more_itertools as mit

# relative libs
from .dicts import DefaultOrderedDict
from ..iter import nth_zip


def xmap(func, it, return_type=list):
    return return_type(map(func, it))


def lmap(func, it):
    return xmap(func, it)


# def amap(func, it):
#     return np.array(lmap(func, it))


def rmap(func, iterable):
    """recursive mapping with type preservation"""
    if isinstance(iterable, coll.Iterable):
        return type(iterable)(
                map(functools.partial(rmap, func), iterable)
        )
    else:
        return func(iterable)


# def lzip(*its):
#     return list(zip(*its))


# def azip(*its):
# return np.array(


def multi_index(seq, val, default=None):
    """Return the index location of all the occurances of val in seq"""
    i, idx = 0, []
    while i < len(seq):
        try:
            i = seq.index(val, i)
            idx.append(i)
            i += 1
        except ValueError:
            return default
    else:
        return idx


where = multi_index


def flatten(l):
    return list(mit.flatiter(l))


def lists(mapping):
    """create a sequence of lists from a mapping/iterator/generator"""
    return list(map(list, mapping))


def listsplit(L, idx):
    """Split a list into sublists at the given indices"""
    return list(map(L.__getitem__, itt.starmap(slice, mit.pairwise(idx))))


def listfind(L, item, start=0, indexer=None):
    """List indexing with a bit of spice"""
    if indexer is None:
        return L.index(item)
    for i, l in enumerate(L):
        if indexer(l, item):
            return i


def listfindall(L, item, indexer=None):
    """
    Return the index positions of the items in the list.
    Parameters
    ----------
    indexer:    function, optional
        method by which the indexing is done.  Calling sequence is indexer(x, items), where x is an item
        from the input list.  The function should return boolean value to indicate whether the position
        of that item is to be returned in the index list.

    Examples
    --------
    >>> L = ['ab', 'Ba', 'cb', 'dD']
    >>> listfindall(L, 'a', str.__contains__)
    [0, 1]
    >>> listfindall(L, 'a', indexer=str.startswith)
    [0]

    """
    if indexer is None:
        indexer = lambda x, i: x.__eq__(i)
    return [i for (i, l) in enumerate(L) if indexer(l, item)]


def listitemsplit(L, items, withfirst=False, withlast=False, indexer=None):
    """
    Split a list into sublists at the indices of the given item.
    """
    idx = listfindall(L, items, indexer)

    if withfirst:
        idx = [0] + idx
    if withlast:
        idx += [len(L) - 1]

    return listsplit(L, idx)


def listrefind(L, pattern):
    R = []
    matcher = re.compile(pattern)
    for i, l in enumerate(L):
        m = matcher.match(l)
        if m:
            return i, m.group()
    return None, None


def find_missing_numbers(seq):
    """Find the gaps in a sequence of integers"""
    all_numbers = set(range(min(seq), max(seq) + 1))
    missing = all_numbers - set(seq)
    return sorted(missing)


def tally(seq):
    """Return dict of unique (item, indices) pairs for sequence."""
    t = DefaultOrderedDict(list)
    for i, item in enumerate(seq):
        t[item].append(i)
    return t


def count_repeats(seq):
    """Return dict of item, count pairs for sequence."""
    t = DefaultOrderedDict(int)
    for i, item in enumerate(seq):
        t[item] += 1
    return t


def gen_duplicates(seq):
    """Yield tuples of item, indices pairs for duplicate values."""
    tally_ = tally(seq)
    return ((key, locs) for key, locs in tally_.items() if len(locs) > 1)


def list_duplicates(seq):
    """Return tuples of item, indices pairs for duplicate values."""
    return list(gen_duplicates(seq))


def where_duplicate(seq):
    """Return lists of indices of duplicate entries"""
    return nth_zip(1, *gen_duplicates(seq))


def sort_by_index(*its, index=None):
    """Use index array to sort items in multiple sequences"""
    if index is None:
        return its
    else:
        return tuple(list(map(it.__getitem__, ix))
                     for it, ix in zip(its, itt.repeat(index)))


def rebuild_without(it, idx):
    """rebuild a sequence without items indicated by indices in idx"""
    idx = set(idx)
    return [v for i, v in enumerate(it) if i not in idx]


def echo(_):
    return _


def sortmore(*args, **kw):
    """
    Extends builtin list sorting with ability to to sorts any number of lists
    simultaneously according to:
        * optional sorting key function(s)
        * and/or a global sorting key function.

    Parameters
    ----------
    One or more lists

    Keywords
    --------
    global_key: None
        revert to sorting by key function
    global_key: callable
        Sort by evaluated value of some combination of all items in the lists
        (call signature of this function needs to be such that it accepts an
        argument tuple of items from each list.
        eg.: global_key = lambda *l: sum(l) will order all the lists by the
        sum of the items from each list

    if key: None
        sorting done by value of first input list
        (in this case the objects in the first iterable need the comparison
        methods __lt__ etc...)
    if key: callable
        sorting done by value of key(item) for items in first iterable
    if key: tuple
        sorting done by value of (key[0](item_0), ..., key[n](item_n)) for items in
        the first n iterables (where n is the length of the key tuple)
        i.e. the first callable is the primary sorting criterion, and the
        rest act as tie-breakers.

    Returns
    -------
    tuple of sorted lists

    Raises
    ------
    ValueError, KeyError

    Examples
    --------
    Capture sorting indices:
        l = list('CharacterS')
        In [1]: sortmore(l, range(len(l)))
        Out[1]: (['C', 'S', 'a', 'a', 'c', 'e', 'h', 'r', 'r', 't'],
                 [0, 9, 2, 4, 5, 7, 1, 3, 8, 6])
        In [2]: sortmore(l, range(len(l)), key=str.lower)
        Out[2]: (['a', 'a', 'C', 'c', 'e', 'h', 'r', 'r', 'S', 't'],
                 [2, 4, 0, 5, 7, 1, 3, 8, 9, 6])
    """
    # TODO: extend examples doc

    farg = list(args[0])
    if not len(farg):
        return args

    global_key = kw.pop('global_key', None)
    key = kw.pop('key', None)
    order = kw.pop('order', None)
    if kw.pop('reversed', None):
        order = 'reversed'

    if len(kw):
        raise ValueError('Unrecognised keyword(s): %s' % str(tuple(kw.keys())))

    # enable default behaviour
    if key is None:
        if global_key:
            # if global sort function given and no local (secondary) key given
            # ==> no tiebreakers
            key = lambda x: 0
        else:
            # if no global sort and no local sort keys given, sort by values
            key = lambda x: x
    if global_key is None:
        def global_key(*_):
            return 0

    # validity checks for sorting functions
    if not isinstance(global_key, coll.Callable):
        raise ValueError('global_key needs to be callable')

    if isinstance(key, coll.Callable):
        def _key(x):
            return global_key(*x), key(x[0])
    elif isinstance(key, tuple):
        key = (k if k else lambda x: 0 for k in key)

        def _key(x):
            return (global_key(*x),) + tuple(f(z) for (f, z) in zip(key, x))
    else:
        raise KeyError(("Keyword arg 'key' should be 'None', callable, or a"
                        "sequence of callables, not {}").format(type(key)))

    res = sorted(list(zip(*args)), key=_key)
    if order:
        if order == -1 or order.startswith(('descend', 'reverse')):
            res = reversed(res)

    return tuple(map(list, zip(*res)))


def sorter(*args, **kw):
    """alias for sortmore"""
    return sortmore(*args, **kw)


# copy docstring
sorter.__doc__ = sortmore.__doc__


class UniformObjectContainer(coll.UserList):
    """
    A helper class that simplifies working with lists of arbitrary objects.
    """

    # TODO: access container object attributes through __getattr__ ?

    # def __init__(self, obj):
    # check uniform ...

    # def __getattr__(self, item):

    def attrgetter(self, *attrs):
        """
        Fetch attributes from the inner class.
        see: builtin `operator.attrgetter` for details

        Parameters
        ----------
        attrs: tuple or str
            Attribute name(s) to retrieve

        Returns
        -------
        list of (tuples of) attribute values


        Examples
        --------
        >>> obs.attrgetter('emGain')
        >>> obs.attrgetter('date.year')
        """
        return list(map(operator.attrgetter(*attrs), self.data))

    def methodcaller(self, name, *args, **kws):
        """

        Parameters
        ----------
        name
        args
        kws

        Returns
        -------

        """
        return list(map(operator.methodcaller(name, *args, **kws), self.data))
