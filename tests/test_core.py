
# std
import numbers
import contextlib
import itertools as itt
from collections import UserList

# third-party
import pytest
from pytest_steps import test_steps

# local
from recipes.testing import PASS, Throws, expected
from pyxides.typing import ListOf, OfType, _TypeEnforcer

# pylint: disable=C0111     # Missing %s docstring
# pylint: disable=R0201     # Method could be a function
# pylint: disable=R0901     # Too many ancestors (%s/%s)


# ---------------------------------------------------------------------------- #
# example container classes

class Coi(ListOf(int)):
    pass


class CoI(UserList, OfType(numbers.Integral)):
    pass


class CoR(UserList, OfType(numbers.Real)):
    pass


class CoiCoerceFloat(ListOf(int, coerce={float: int})):
    pass

# ---------------------------------------------------------------------------- #


ex = expected({
    # This should be OK since numbers.Real derives from numbers.Integral
    (CoR, numbers.Integral):        PASS,
    # This should also be OK since bool derives from int
    (Coi, bool):                    PASS,
    # multiple unrelated type estrictions requested in different
    # bases of container
    (CoI, float):                   Throws(TypeError),
    # OfTypes used without preceding Container type
    ((), float):                    Throws(TypeError),
    (list, float):                  PASS
})


def multiple_inheritance(bases, allowed):
    if not isinstance(bases, tuple):
        bases = (bases, )

    class CoX(*bases, OfType(allowed)):
        pass

    # make sure the TypeEnforcer is higher in the mro
    assert issubclass(CoX.__bases__[0], _TypeEnforcer)
    # make sure the `_allowed_types` got updated
    assert CoX._allowed_types == (allowed, )


test_multiple_inheritance = ex(multiple_inheritance)

_contexts = {'raise': pytest.raises(TypeError),
             'warn': pytest.warns(UserWarning),
             'ignore': contextlib.nullcontext()}


class TestOfType:

    def test_empty_init(self):
        CoI()

    @test_steps('init_good', 'append', 'extend', 'add', 'init_bad')
    @pytest.mark.parametrize(
        'Container, init, bad, action',
        [*itt.product([CoI], [(1, 2, 3)], [1.], _contexts),
         *itt.product([CoR], [(1., 2.)], [1j], _contexts)]
    )
    def test_type_checking(self, Container, init, bad, action):
        #
        context = _contexts[action]
        Container.set_type_validation(action)
        yield from self._generate_test_steps(Container, init, bad, context)

        # init_bad
        with context:
            Container([bad])
        yield

    @test_steps('init',  'append', 'extend', 'add')
    @pytest.mark.parametrize(
        'Container, init, add, action',
        [(CoiCoerceFloat, (1, 2, 3.), 1., 'ignore'),
         (CoiCoerceFloat, (1, 2, 3.), 1j, 'raise')]
    )
    def test_type_coercion(self, Container, init, add, action):
        yield from self._generate_test_steps(Container, init, add, _contexts[action])

    def _generate_test_steps(self, Container, init, add, context):
        cx = Container(init)
        assert all(isinstance(_, Container._allowed_types) for _ in cx)
        yield

        with context:
            cx.append(add)
        yield

        with context:
            cx.extend([add])
        yield

        with context:
            cx + [add]
        yield

    def test_add(self):
        assert isinstance(Coi([1, 2]) + [1, 3], Coi)
