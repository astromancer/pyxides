
# std libs
import numbers
from collections import UserList

# third-party libs
import pytest
import numpy as np

#
from pyxis.type_check import OfTypes, _TypeEnforcer


# pylint: disable=C0111     # Missing %s docstring
# pylint: disable=R0201     # Method could be a function
# pylint: disable=R0901     # Too many ancestors (%s/%s)


# ---------------------------------------------------------------------------- #
# example container classes

class Coi(UserList, OfTypes(int)):
    pass


class CoI(UserList, OfTypes(numbers.Integral)):
    pass


class CoR(UserList, OfTypes(numbers.Real)):
    pass

# ---------------------------------------------------------------------------- #
class TestOfTypes:
    def test_empty_init(self):
        CoI()
        
    
    @pytest.mark.parametrize(
        'base, allowed',
        (  # This should be OK since numbers.Real derives from numbers.Integral
            (CoR, numbers.Integral),
            # This should also be OK since bool derives from int
            (Coi, bool)
        )
    )
    def test_multiple_inheritance(self, base, allowed):
        class CoX(base, OfTypes(allowed)):
            pass

        # make sure the TypeEnforcer is higher in the mro
        assert issubclass(CoX.__bases__[0], _TypeEnforcer)
        # make sure the `_allowed_types` got updated
        assert CoX._allowed_types == (allowed, )

    def test_multiple_inheritance_fails(self):
        with pytest.raises(TypeError):
            # multiple unrelated type estrictions requested in different
            # bases of container
            class CoF(CoI, OfTypes(float)):
                pass

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
