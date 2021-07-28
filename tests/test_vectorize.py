# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=no-self-use
# pylint: disable=redefined-outer-name



# std libs
import itertools as itt

# third-party libs
import pytest
from pyxides import ListOf
from pyxides.vectorize import (CallVectorizerMixin, AttrVectorizerMixin,
                               AttrVectorizer, repeat)


# ---------------------------------------------------------------------------- #
# Cases
class Letter:
    def __init__(self, s):
        self.letter = s
        self.upper = s.upper()


class Word(ListOf(Letter)):

    # properties: vectorized attribute getters on `letters`
    letters = AttrVectorizer('letter')
    uppers = AttrVectorizer('upper')


class Hello:
    world = 'hi'


class Simple:
    def __init__(self, i):
        self.i = i
        self.hello = Hello()


class List(list, AttrVectorizerMixin):
    """My list"""
    ii = AttrVectorizer('i')


@pytest.fixture()
def simple_list():
    return List(map(Simple, [1, 2, 3]))


# ---------------------------------------------------------------------------- #
# Test


class TestAttrVectorizer:
    def test_getter(self):
        word = Word(map(Letter, 'hello!'))
        assert word.letters == list('hello!')
        assert word.uppers == list('HELLO!')

    def test_setter(self, simple_list):
        # word = Word(map(Letter, 'hello!'))
        # word.letters = 'world!'
        # word.uppers == 'WORLD!'.split()

        simple_list.ii = [1, 2, 3]
        assert [s.i for s in simple_list] == [1, 2, 3]

        with pytest.raises(TypeError):
            simple_list.ii = 2

        with pytest.raises(ValueError):
            simple_list.ii = [2]


class TestAttrVectorizerMixin:

    def test_read(self, simple_list):
        assert simple_list.attrs.i == [1, 2, 3]
        assert simple_list.attrs('hello.world') == ['hi', 'hi', 'hi']

    def test_write(self, simple_list):
        simple_list.attrs.set(i=itt.repeat(2))
        assert simple_list.attrs.i == [2, 2, 2]

        simple_list.attrs.set({'hello.world': 'xxx'})
        assert simple_list.attrs('hello.world') == list('xxx')

        simple_list.attrs.set(repeat({'hello.world': 'x'}))
        assert simple_list.attrs('hello.world') == list('xxx')


# ---------------------------------------------------------------------------- #


class Hi(list, CallVectorizerMixin):
    """Hi!"""

# ---------------------------------------------------------------------------- #
# Test


class TestCallVectorizerMixin:

    def test_calls(self):
        hi = Hi('hello')
        assert hi.calls.upper() == ['H', 'E', 'L', 'L', 'O']
        assert hi.calls.join('||') == ['|h|', '|e|', '|l|', '|l|', '|o|']
        # hi.calls.zfill(8)
        # hi.calls.encode(encoding='latin')
