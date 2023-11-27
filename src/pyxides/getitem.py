# std
import numbers

# third-party
import numpy as np


class ArrayLikeIndexing:
    """
    Mixin for vectorized item getting for index keys that are sequences of
    items: lists, tuples, numpy arrays
    """

    def __getitem__(self, key):
        getitem = super().__getitem__

        if isinstance(key, (list, tuple)):
            # if multiple item retrieval vectorizer!
            return list(map(getitem, key))

        if isinstance(key, np.ndarray):
            if key.ndim != 1:
                raise ValueError('Only 1D indexing arrays are allowed')

            if key.dtype.kind == 'b':
                if len(key) != len(self):
                    raise ValueError(
                        'Indexing with a boolean array of unequal size '
                        f'(len(key) = {len(key)} ≠ {len(self)} = len(self)).')

                key, = np.where(key)

            if key.dtype.kind == 'i':
                return list(map(getitem, key))

            raise ValueError('Index arrays should be of type int or bool not '
                             f'{key.dtype!r}')

        return getitem(key)


class IndexingMixin(ArrayLikeIndexing):  # IndexingMixin
    """
    Mixin that supports vectorized item getting like numpy arrays

    NOTE:  # needs to be before `UserList` in mro
    """
    # TODO: sort out mro automatically

    _returned_type = None

    def set_returned_type(self, obj):
        """Will change the type returned by __getitem__"""
        self._returned_type = obj

    def get_returned_type(self):
        """
        Return the class that wraps objects returned by __getitem__.
        Default is to return this class itself, so that
        `type(obj[[1]]) == type(obj)`

        This is useful for subclasses that overwrite `__init__` and don't
        want re-run initialization code
        """
        return self._returned_type or self.__class__

    def __getitem__(self, key):
        # get_single_item = super(ArrayLikeIndexing, self).__getitem__
        # getitem = super().__getitem__
        #
        if (isinstance(key, (numbers.Integral, slice, type(...)))
                and not isinstance(key, bool)):
            return super().__getitem__(key)
            # return super(ArrayLikeIndexing, self).__getitem__(key)

        if isinstance(key, (list, tuple, np.ndarray)):
            # if multiple item retrieval vectorizer!
            # wrap in required type
            return self.get_returned_type()(
                ArrayLikeIndexing.__getitem__(self, key)
            )

        raise TypeError('Invalid index type %r' % type(key))


# alias
IndexerMixin = IndexingMixin


class ContainerWrapper(IndexingMixin):

    _wraps = list
    # if you use this class without changing this class attribute, you may as
    # well just use UserList

    def __init__(self, items):
        self.data = self._wraps(items)

    def __len__(self):
        return len(self.data)
