"""
Enable construction of containers with uniform item type(s)
"""

# std libs
import warnings as wrn
from abc import ABCMeta
from collections import abc


# local libs
from recipes.iter import first_true_index
from recipes.functionals import echo0, raises as bork


class OfTypes(ABCMeta):
    """
    Factory that creates TypeEnforcer classes. Allows for the following usage
    pattern:

    >>> class Container(UserList, OfTypes(int)):
    ...     pass

    which creates a container class `Container` that will only allow integer
    items inside. This constructor assigns a tuple of allowed types as class
    attribute `_allowed_types`
    """

    # NOTE: inherit from ABCMeta to avoid metaclass conflict with UserList which
    # has metaclass abc.ABCMeta

    def __new__(cls, *args, **kws):

        if isinstance(args[0], str):
            # This results from an internal call during class construction
            name, bases, attrs = args
            # create class
            return super().__new__(cls, name, cls.make_bases(name, bases),
                                   attrs, **kws)

        # we are here if invoked by direct call:
        # >>> cls = OfTypes(int)

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
                               {'_allowed_types': tuple(args)}, **kws)

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
            # print('BASS', base)
            if issubclass(base, abc.Container):
                ic = i

            # base is a TypeEnforcer class
            if issubclass(base, _TypeEnforcer):
                # _TypeEnforcer !
                # print('_TypeEnforcer !', base,  base._allowed_types)
                requested_allowed_types = base._allowed_types
                ite = i

            # look for other `_TypeEnforcer`s in the inheritance diagram so we
            # consolidate the type checking
            for bb in base.__bases__:
                if isinstance(bb, cls):
                    # this is a `_TypeEnforcer` base
                    currently_allowed_types.extend(bb._allowed_types)
                    # print(currently_allowed_types)
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

                    # requested type restriction is a new type unrelated to
                    # existing restriction. Disallow
                    raise TypeError(
                        f'Multiple type restrictions ({new}, {allowed}) '
                        'requested in different bases of container class '
                        f'{name}.')  # To allow multiple

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
    
    # TODO: inherit from UserList, so we can init like 
    # from pyxides.type_check import OfType

    # class Twinkie:
    #     """Yum!"""

    # class Box(OfType(Twinkie)):
    #     """So much YUM!"""
    
    # Box()

    _allowed_types = (object, )     # placeholder
    _actions = {-1: echo0,          # silently ignore
                0: wrn.warn,
                1: bork(TypeError)}
    emit = staticmethod(_actions[1])              # default

    @classmethod
    def type_checking(cls, severity=1):
        cls.emit = staticmethod(cls._actions[int(severity)])

    def __init__(self, items=()):
        super().__init__(self.checks_type(items))
        # self.emit = self._actions[int(severity)]

    def checks_type(self, itr, raises=None, warns=None, silent=None):
        """Generator that checks types"""
        if raises is warns is silent is None:
            # default behaviour decided at init (default is to raise TypeError)
            raises = True

        emit = self._actions[1 - first_true_index((raises, warns, silent))]
        for i, obj in enumerate(itr):
            with wrn.catch_warnings():
                wrn.filterwarnings('once', 'Items in container class')
                self.check_type(obj, i, emit)
                yield obj

    def check_type(self, obj, i='', emit=None):
        """Type checker"""
        if isinstance(obj, self._allowed_types):
            return

        emit = emit or self.emit
        if emit is echo0:
            return

        many = len(self._allowed_types) > 1
        ok = self._allowed_types[... if many else 0]
        emit(f'Items in container class {self.__class__.__name__!r} must '
             f'derive from {"one of" if many else ""} {ok}. '
             f'Item {i}{" " * bool(i)} is of type {type(obj)!r}.')

    def append(self, item):
        self.check_type(item, len(self))
        super().append(item)

    def extend(self, itr):
        super().extend(self.checks_type(itr))
