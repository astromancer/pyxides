"""
Enable construction of containers with uniform item type(s)
"""

# std
import warnings as wrn
import itertools as itt
from abc import ABCMeta
from typing import MutableMapping
from collections import UserList, abc

# local
from recipes.lists import split
from recipes.string import named_items
from recipes.functionals import echo0, raises


# ---------------------------------------------------------------------------- #
def ignore(_):
    pass


class OfTypes(ABCMeta):
    """
    Factory that creates TypeEnforcer classes. Allows for the following usage
    pattern:

    >>> class Container(UserList, OfTypes(int)):
    ...     pass

    This creates a container class `Container` that will only allow integer
    items inside. This constructor assigns a tuple of allowed types as class
    attribute `_allowed_types` for checking against.
    """

    # NOTE: inherit from ABCMeta to avoid metaclass conflict with UserList which
    # has metaclass abc.ABCMeta

    def __new__(cls, *args, coerce=None, **kws):
        # type coercion off by default since not always appropriate
        # eg: numbers.Real

        if isinstance(args[0], str):
            # This results from an internal call below during construction
            name, bases, attrs = args
            # create class
            return super().__new__(cls, name, cls.make_bases(name, bases),
                                   attrs)

        # we are here if invoked by direct call:
        # >>> cls = OfType(int)

        # create TypeEnforcer class that inherits from _TypeEnforcer.
        # `args` gives allowed type(s) for this container.
        # `_allowed_types` class attribute set to tuple of allowed types

        # check arguments are given and class objects

        if not args:
            raise ValueError(f'{cls.__name__}\'s constructor requires at least '
                             'one argument: the allowed type(s).')

        for kls in args:
            if isinstance(kls, type):
                continue

            raise TypeError(f'Arguments to {cls.__name__!r} constructor should'
                            f' be classes, received instance of {type(kls)}.')

        # create the type
        return super().__new__(
            #    name       bases
            cls, 'ListOf', (_TypeEnforcer, ),
            # namespace
            {'_allowed_types': tuple(args),
             # optional type coercion
             '_coerced_types': cls._check_coercion_mapping(args, coerce)},
        )

    # def __init__(self, name: str, bases: tuple[type, ...], namespace: dict[str, Any]):
    def __init__(self, *args, **kws):
        super().__init__(*args)

    @classmethod
    def make_bases(cls, name, bases):
        """
        sneakily place `_TypeEnforcer` ahead of `abc.Container` types in the
        inheritance order so that type checking happens on __init__ of classes
        (instances of this metaclass).

        Also check if there is another TypeEnforcer in the list of bases and
        make sure the `_allowed_types` are consistent - if any is a subclass of
        a type in the already defined `_allowed_types` higher up in the
        inheritance diagram by another `OfTypes` instance, this is allowed,
        else raise TypeError since it will lead to type enforcement being done
        for different types at different levels in the class heirarchy which is
        nonsensical.
        """

        # TODO: might want to do the same for ObjectArray1d.  If you register
        #   your classes as ABCs you can do this in one fell swoop!

        # enforcers = []
        # base_enforcers = []
        # indices = []
        # new_bases = list(bases)

        *indices, requested, currently_allowed = cls._get_allowed_types(bases)
        idx_enf, idx_cnt = indices

        # print('=' * 80)
        # print(name, bases)
        # print('requested', requested_allowed_types)
        # print('current', previous_allowed_types)

        # deal with multiple enforcers
        # en0, *enforcers = enforcers
        # ite, *indices = indices
        # if len(enforcers) > 0:
        #     # multiple enforcers defined like this:
        #     # >>> class Foo(list, OfType(int), OfType(float))
        #     # instead of like this:
        #     # >>> class Foo(list, OfTypes(int, float))
        #     # merge type checking
        #     warnings.warn(f'Multiple `TypeEnforcer`s in bases of {name}. '
        #                   'Please use `OfType(clsA, clsB)` to allow multiple '
        #                   'types in your containers')

        #     for i, ix in enumerate(indices):
        #         new_bases.pop(ix - i)

        cls._check_allowed_types(name, requested, currently_allowed)
        if idx_cnt is None:
            if issubclass(cls, ListOf):
                # No container types in list of parents. Add it!
                pre, post = split(bases, idx_enf + 1)
                bases = (*pre, UserList, *post)
            else:
                requested = ', '.join(kls.__name__ for kls in requested)
                raise TypeError(
                    f'Using "{cls.__name__}({requested})" without preceding '
                    f'container type in inheritence diagram. Did you mean to '
                    f'use "ListOf({requested})"?'
                )

        if (idx_enf is None) or (idx_cnt is None):
            return bases

        if idx_cnt < idx_enf:
            # _TypeEnforcer is before UserList in inheritance order so that
            # types get checked before initialization of the `Container`
            _bases = list(bases)
            _bases.insert(idx_cnt, _bases.pop(idx_enf))
            # print('new_bases', _bases)
            return tuple(_bases)

        return bases

    @classmethod
    def _get_allowed_types(cls, bases):

        idx_enf = None
        idx_cnt = None
        previous_allowed_types = []
        for i, base in enumerate(bases):
            # print('BASS', base)
            if issubclass(base, abc.Container):
                idx_cnt = i

            # base is a TypeEnforcer class
            if issubclass(base, _TypeEnforcer):
                # _TypeEnforcer !
                # print('_TypeEnforcer !', base,  base._allowed_types)
                requested_allowed_types = base._allowed_types
                idx_enf = i

            # look for other `_TypeEnforcer`s in the inheritance diagram so we
            # consolidate the type checking
            for bb in base.__bases__:
                if isinstance(bb, cls):
                    # this is a `_TypeEnforcer` base
                    previous_allowed_types.extend(bb._allowed_types)
                    # print(previous_allowed_types)
                    # base_enforcers.append(bb)
                    # original_base = base

        return idx_enf, idx_cnt, requested_allowed_types, previous_allowed_types

    @staticmethod
    def _check_allowed_types(name, requested_allowed_types,
                             previous_allowed_types):

        # consolidate allowed types
        if not previous_allowed_types:
            return

        # loop through currently allowed types
        for allowed, new in itt.product(previous_allowed_types,
                                        requested_allowed_types):
            if issubclass(new, allowed):
                # type restriction requested is a subclass of already
                # existing restriction type.  This means we narrow the
                # restriction to the new (subclass) type
                break

            # requested type restriction is a new type unrelated to
            # existing restriction. Disallow.
            raise TypeError(
                f'Multiple incompatible type restrictions ({new}, {allowed}) '
                f'requested in different bases of container class {name}.'
            )

    @staticmethod
    def _check_coercion_mapping(allowed_types, coerce):
        if not coerce:
            return {object: echo0}

        if coerce is True:
            # use the `_allowed_types` to coerce input items
            if len(allowed_types) == 1:
                return {object: allowed_types[0]}

            raise ValueError(f'`coerce=True` is ambiguous with polymorphic '
                             f'ListOf{allowed_types}')

        if callable(coerce):
            return {object: coerce}

        if not isinstance(coerce, MutableMapping):
            raise TypeError(
                f'Invalid type for `coerce` parameter: {type(coerce)}. This '
                f'should either be a callable object (generic function that '
                f'handles convertion of all types), or a mapping of type, '
                f'callable pairs for specific type convertion strategies.'
            )

        for kls, func in coerce.items():
            if not isinstance(kls, type):
                raise TypeError(f'Keys in the coercion mapping should be type '
                                f'objects, not {type(kls)}.')

            if not callable(func):
                many = (len(allowed_types) > 1)
                ok = allowed_types[... if many else 0]
                raise TypeError(
                    f'Coercion function for converting {kls} type items to '
                    f'{"one of" if many else ""} {ok} should be a callable '
                    f'object, not {type(func)}.'
                )

        return coerce


# alias
OfType = OfTypes


class ListOf(OfType):
    """
    A container metaclass implementing type assertion and type coercion
     - ensures that listed items are always of (a) certain type(s).

    >>> class Twinkie:
    ...     '''Yum!'''
    ...
    ... class TwinkieBox(ListOf(Twinkie)):
    ...     '''So much YUM!'''
    ...
    ... TwinkieBox()

    >>> class Integers(ListOf(int)):
    ...     pass
    """

    def __str__(self):
        names = ', '.join(kls.__name__ for kls in self._allowed_types)
        return f'{self.__class__.__name__}[{names}]'


class _TypeEnforcer:
    """
    Item type checking mixin for list-like containers.
    """

    _allowed_types = (object, )         # placeholder
    _coerced_types = {object: echo0}    # default convertion placeholder
    _validation_actions = {
        -1:         ignore,             # silently ignore invalid types
        0:          wrn.warn,           # emit warning
        1:          (bork := raises(TypeError)),    # raise TypeError
        'ignore':   ignore,
        'warn':     wrn.warn,
        'raise':    bork
    }
    # default is to raise TypeError on invalid types
    _default_validation_action = 'raise'
    emit = staticmethod(_validation_actions[_default_validation_action])

    @classmethod
    def set_type_validation(cls, action=_default_validation_action):
        action = action.lower().rstrip('s') if isinstance(action, str) else int(action)
        cls.emit = staticmethod(cls._validation_actions[action])

    def __init__(self, items=()):
        super().__init__(self.check_all_types(items))

    def check_all_types(self, itr, emit=None):
        """Generator that asserts types for sequence of items."""
        for i, obj in enumerate(itr):
            with wrn.catch_warnings():
                wrn.filterwarnings('once', 'Items in container class')
                yield self.check_types(obj, i, emit)

    def check_types(self, obj, i='', emit=None):
        """Type assertion for single item."""
        if isinstance(obj, self._allowed_types):
            return obj

        # optional type coercion
        obj = self.coerce(obj)
        if isinstance(obj, self._allowed_types):
            return obj

        emit = emit or self.emit
        emit(f'Items in container class {type(self).__name__!r} must derive '
             f'from{named_items(self._allowed_types, "", " one of ")}. '
             f'Item {i}{" " * (i != "")}is of type {type(obj)!r}.')

        return obj

    # alias
    check_type = check_types

    def get_converter(self, obj):
        """Get dispatch method for type coercion on object `obj`."""
        if coerce := self._coerced_types.get(type(obj)):
            return coerce

        # perhaps the object is a subclass of one of the types in the coercion map
        for kls, coerce in self._coerced_types.items():
            if isinstance(obj, kls):
                return coerce

        # There is no converter to coerce this type of object
        raise TypeError(f'Could not find a method to coerce object of type '
                        f'{type(obj).__name__} to '
                        f'{named_items(self._allowed_types, "", " one of ")} '
                        f'for container class {type(self).__name__!r}.')

    def coerce(self, obj):
        func = self.get_converter(obj)
        try:
            return func(obj)
        except Exception as err:
            raise TypeError(f'{self.__class__.__name__} could not coerce '
                            f'object of type {type(obj)}.') from err

    def append(self, item):
        item = self.check_types(item, len(self))
        super().append(item)

    def extend(self, itr):
        super().extend(self.check_all_types(itr))
