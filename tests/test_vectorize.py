
from pyxides.vectorize import CallVectorize, AttrVectorize
import pytest


# ---------------------------------------------------------------------------- #
# Cases

class MyList(list, AttrVectorize):
    """My list"""


class Simple:
    def __init__(self, i):
        self.i = i
        self.hello = Hello()


class Hello:
    world = 'hi'


class Hi(list, CallVectorize):
    """Hi!"""

# ---------------------------------------------------------------------------- #


@pytest.fixture()
def simple_list():
    return MyList(map(Simple, [1, 2, 3]))


class TestAttrVectorize:

    def test_read(self, simple_list):
        assert simple_list.attrs.i == [1, 2, 3]
        assert simple_list.attrs('hello.world') == ['hi', 'hi', 'hi']

    def test_write(self, simple_list):
        simple_list.attrs.set(i=2)
        assert simple_list.attrs.i == [2, 2, 2]

        simple_list.attrs.set({'hello.world': 'x'})
        assert simple_list.attrs('hello.world') == ['x', 'x', 'x']


class TestCallVectorize:

    def test_calls(self):
        hi = Hi('hello')
        assert hi.calls.upper() == ['H', 'E', 'L', 'L', 'O']
        assert hi.calls.join('||') == ['|h|', '|e|', '|l|', '|l|', '|o|']
        # hi.calls.zfill(8)
        # hi.calls.encode(encoding='latin')
