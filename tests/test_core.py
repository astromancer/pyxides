
# std libs
import numbers
from collections import UserList

# third-party libs
import pytest
import numpy as np

#
from pyxides.type_check import OfType, ListOf, _TypeEnforcer
from recipes.testing import expected, mock, Throws, PASS

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

# ---------------------------------------------------------------------------- #


ex = expected(
    {  # This should be OK since numbers.Real derives from numbers.Integral
        (CoR, numbers.Integral):    PASS,
        # This should also be OK since bool derives from int
        (Coi, bool):                PASS,
        # multiple unrelated type estrictions requested in different
        # bases of container
        (CoI, float):                  Throws(TypeError),
        # OfTypes used without preceding Container type
        ((), float):                   Throws(TypeError),
        (list, float):                 PASS
    }
)

def multiple_inheritance(bases, allowed):
    if not isinstance(bases, tuple):
        bases = (bases, )
        
    class CoX(*bases, OfType(allowed)):
        pass

    # make sure the TypeEnforcer is higher in the mro
    assert issubclass(CoX.__bases__[0], _TypeEnforcer)
    # make sure the `_allowed_types` got updated
    assert CoX._allowed_types == (allowed, )

test_multiple_inheritance  = ex(multiple_inheritance)

class TestOfType:
    def test_empty_init(self):
        CoI()


    

    @pytest.mark.parametrize(
        'Container, ok, bad',
        [(CoI, [1, 2, 3], [1.]),
         (CoR, [1, np.float(1.)], [1j])]
    )
    def test_type_checking(self, Container, ok, bad):
        #
        cx = Container(ok)

        with pytest.raises(TypeError):
            cx.append(bad[0])

        with pytest.raises(TypeError):
            cx.extend(bad)

        with pytest.raises(TypeError):
            Container(bad)
