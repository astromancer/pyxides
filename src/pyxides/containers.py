"""
Container magic
"""


# std libs
from collections import UserList

# local libs
from recipes.oo import SelfAware, meta
from recipes.logging import LoggingMixin

# relative libs
from .getitem import ItemGetter
from .grouping import AttrGrouper
from .pprint import PPrintContainer
from .type_check import OfType  # @keep


class ArrayLike1D(ItemGetter, UserList):
    """
    A container class that emulates a one dimensional numpy array,
    providing all the array slicing niceties.

    Provides the following list-like functionality:
    >>> c = ArrayLike1D([1, 2, 3])
    >>> three = c.pop(-1)
    >>> c.append(id)
    >>> c.extend(['some', 'other', object])
    multi-index slicing ala numpy
    >>> c[[0, 3, 5]]    # [1, <function id(obj, /)>, 'other']

    """
    #     # TODO: __slots__


class Container(SelfAware, ArrayLike1D, AttrGrouper,
                PPrintContainer, LoggingMixin,
                metaclass=meta.classmaker()):
    """A good container"""
