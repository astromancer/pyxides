# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=no-self-use
# pylint: disable=redefined-outer-name


import pytest
from pyxides import ListOf
from pyxides.vectorize import CallVectorize, AttrVectorize, AttrVector


# ---------------------------------------------------------------------------- #
# Cases


class Hello:
    world = 'hi'


class Hi(list, CallVectorize):
    """Hi!"""

################################################################################


class List(list, AttrVectorize):
    """My list"""


class Simple:
    def __init__(self, i):
        self.i = i
        self.hello = Hello()

################################################################################


class Letter:
    def __init__(self, s):
        self.letter = s
        self.upper = s.upper()


class Word(ListOf(Letter)):
    def __init__(self, letters=()):
        # initialize container
        super().__init__(letters)

    # properties: vectorized attribute getters on `letters`
    letters = AttrVector('letter')
    uppers = AttrVector('upper')

# ---------------------------------------------------------------------------- #


@pytest.fixture()
def simple_list():

    return List(map(Simple, [1, 2, 3]))


def testAttrVector():

    word = Word(map(Letter, 'hello!'))
    assert word.letters == ['h', 'e', 'l', 'l', 'o', '!']
    assert word.uppers == ['H', 'E', 'L', 'L', 'O', '!']


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
