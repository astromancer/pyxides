"""
Recipes involving lists
"""

# std libs
import re
import itertools as itt

# third-party libs
import more_itertools as mit

# relative libs
from .dicts import DefaultOrderedDict
from ..iter import nth_zip


def _echo(_):
    return _


def _zero(*_):
    return 0


def _make_key(master_key, funcs):
    def sort_key(x):
        values = ((f or _zero)(z) for f, z in zip(funcs, x))
        return (master_key(*x),) + tuple(values)
    return sort_key


def sortmore(*lists, **kws):
    """
    Extended co-sorting of lists. Sort any number of lists simultaneously
    according to:
        * optional sorting function(s)
        * and/or a global sorting function.

    Parameters
    ----------
    One or more lists

    Keywords
    --------
    master_key: callable
        Sort by evaluated value of some combination of all items in the lists
        (call signature of this function needs to be such that it accepts an
        argument tuple of items from each list.
        eg.: master_key = lambda *l: sum(l) will order all the lists by the
        sum of the items from each list.
        If not provided, revert to sorting by `key` function
    key: callable or tuple of callables
        If callble sorting done by value of key(item) for items in first
        iterable If tuple sorting done by value of
        (key[0](item_0), ..., key[n](item_n)) for items in the first n iterables
        (where n is the length of the key tuple) i.e. the first callable is the
        primary sorting criterion, and the rest act as tie-breakers.
        If not provided sorting done by value of first input list. 

    Returns
    -------
    tuple of sorted lists

    Raises
    ------
    ValueError, KeyError

    Examples
    --------
    Sorting multiple lists in sympathy:
    >>> sortmore('32145', range(5))

    Capture sorting indices:
    >>> l = list('CharacterS')
    >>> sortmore(l, range(len(l)))
    (['C', 'S', 'a', 'a', 'c', 'e', 'h', 'r', 'r', 't'],
     [0, 9, 2, 4, 5, 7, 1, 3, 8, 6])
    >>> sortmore(l, range(len(l)), key=str.lower)
    (['a', 'a', 'C', 'c', 'e', 'h', 'r', 'r', 'S', 't'],
     [2, 4, 0, 5, 7, 1, 3, 8, 9, 6])
    """
    # TODO: extend examples doc

    # convert to lists
    lists = list(map(list, lists))

    # check that all lists have the same length
    if len(set(map(len, lists))) != 1:
        raise ValueError('Cannot co-sort raggedly shaped lists')

    list0 = list(lists[0])
    if len(list0) == 0:  # all lists are zero length
        return lists

    master_key = kws.pop('master_key', None)
    key = kws.pop('key', None)
    order = kws.pop('order', 1)
    if kws:
        raise ValueError(f'Unrecognised keyword(s): {tuple(kws.keys())}')

    # enable default behaviour
    if key is None:
        # if global sort function given and no local (secondary) key given
        #   ==> no tiebreakers
        # if no global sort and no local sort keys given, sort by values
        key = _zero if master_key else _echo

    # if no master key, use null func
    master_key = master_key or _zero

    # validity checks for sorting functions
    if not callable(master_key):
        raise ValueError('master_key needs to be callable')

    if callable(key):
        key = (key, )
    if not isinstance(key, (tuple, list)):
        raise KeyError("Keyword arg 'key' should be 'None', callable, or a"
                       f"sequence of callables, not {type(key)}")

    res = sorted(zip(*lists), key=_make_key(master_key, key))
    if order == -1:
        res = reversed(res)

    return tuple(map(list, zip(*res)))


def cosort(*lists, key=None, order=1):
    return sortmore(*lists, key=key, order=order)


def sort_by_index(*its, index=None):
    """Use index array to sort items in multiple sequences"""
    if index is None:
        return its
    return tuple(list(map(it.__getitem__, ix))
                 for it, ix in zip(its, itt.repeat(index)))


def where(l, item, default=None):
    """
    A multi-indexer for lists. Return index locations of all occurances of `item`
    in `l` as a list

    Parameters
    ----------
    l : list
        The list to search
    item :
        Item to be searched for
    default : 
        The default return value in case `item` is not found, by default None

    Returns
    -------
    list of int or None
        The indices
    """
    return list(_where(l, item)) or default


def _where(l, item):
    i = 0
    while i < len(l):
        try:
            i = l.index(item, i)
            yield i
        except ValueError:
            # done
            return
        else:
            i += 1  # start next search one on


def flatten(l):
    return list(mit.collapse(l))


def lists(mapping):
    """create a sequence of lists from a mapping / iterator /generator"""
    return list(map(list, mapping))


def split(l, idx):
    """Split a list into sublists at the given indices"""
    return list(map(l.__getitem__, itt.starmap(slice, mit.pairwise(idx))))


def find(l, item, start=0, indexer=None):
    """
    List indexing with a bit of spice

    Parameters
    ----------
    l : [type]
        [description]
    item : [type]
        [description]
    start : int, optional
        [description], by default 0
    indexer : [type], optional
        [description], by default None

    Returns
    -------
    [type]
        [description]
    """
    if indexer is None:
        return l.index(item, start)

    for i, x in enumerate(l[start:]):
        if indexer(x, item):
            return i


def findall(l, item, indexer=None):
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
    >>> l = ['ab', 'Ba', 'cb', 'dD']
    >>> findall(l, 'a', str.__contains__)
    [0, 1]
    >>> findall(l, 'a', indexer=str.startswith)
    [0]

    """
    indexer = indexer or (lambda x, i: (x == i))
    return [i for (i, x) in enumerate(l) if indexer(x, item)]


def item_split(l, items, withfirst=False, withlast=False, indexer=None):
    """
    Split a list into sublists at the indices of the given item.
    """
    idx = findall(l, items, indexer)

    if withfirst:
        idx = [0] + idx
    if withlast:
        idx += [len(l) - 1]

    return split(l, idx)


def re_find(l, pattern):
    R = []
    matcher = re.compile(pattern)
    for i, x in enumerate(l):
        m = matcher.match(x)
        if m:
            R.append((i, m.group()))
    return R


def find_missing_numbers(l):
    """Find the gaps in a sequence of integers"""
    all_numbers = set(range(min(l), max(l) + 1))
    missing = all_numbers - set(l)
    return sorted(missing)


def tally(l):
    """Return dict of unique (item, indices) pairs for sequence."""
    t = DefaultOrderedDict(list)
    for i, item in enumerate(l):
        t[item].append(i)
    return t


def count_repeats(l):
    """Return dict of item, count pairs for sequence."""
    t = DefaultOrderedDict(int)
    for i, item in enumerate(l):
        t[item] += 1
    return t


def gen_duplicates(l):
    """Yield tuples of item, indices pairs for duplicate values."""
    tally_ = tally(l)
    return ((key, locs) for key, locs in tally_.items() if len(locs) > 1)


def duplicates(l):
    """Return tuples of item, indices pairs for duplicate values."""
    return list(gen_duplicates(l))


def where_duplicate(l):
    """Return lists of indices of duplicate entries"""
    return nth_zip(1, *gen_duplicates(l))
