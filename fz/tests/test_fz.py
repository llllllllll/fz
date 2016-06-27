from functools import partial
import operator as op

import pytest

from fz import _1, _2, _3, _v, _f, _binop_map


def test_identity():
    ob = object()
    assert _1(ob) is ob
    assert _2(None, ob) is ob
    assert _3(None, None, ob) is ob


@pytest.mark.parametrize('op', map(partial(getattr, op), _binop_map))
def test_arithmetic(op):
    for n in range(1, 6):  # many ops fail with rhs <= 0
        f = op(_1, n)
        g = op(_1, _2)
        for m in range(-5, 6):
            assert f(m) == op(m, n)
            assert g(m, n) == op(m, n)


@pytest.mark.parametrize('op', (op.add, op.sub, op.truediv, op.floordiv))
def test_negative_rhs(op):
    for n in range(-5, 0):
        f = op(_1, n)
        g = op(_1, _2)
        for m in range(-5, 6):
            assert f(m) == op(m, n)
            assert g(m, n) == op(m, n)


def test_getattr():
    class c:
        attr = 1
        other = 2

    assert _1.attr(c) == 1
    assert _1.other(c) == 2
    assert _2.attr(None, c) == 1
    assert _2.other(None, c) == 2
    assert _3.attr(None, None, c) == 1
    assert _3.other(None, None, c) == 2


def test_getitem():
    d = _v({'a': 1, 'b': 2})

    assert d[_1]('a') == 1
    assert d[_1]('b') == 2
    assert d[_2](None, 'a') == 1
    assert d[_2](None, 'b') == 2
    assert d[_3](None, None, 'a') == 1
    assert d[_3](None, None, 'b') == 2


def test_value_call():
    called = []

    @_f
    def f(a):
        called.append(a)
        return a

    expected = [object(), object(), object()]

    assert f(_1)(expected[0]) is expected[0]
    assert f(_2)(None, expected[1]) is expected[1]
    assert f(_3)(None, None, expected[2]) is expected[2]

    assert len(called) == 3
    for a, b in zip(called, expected):
        assert a is b


def test_flip():
    flip = _f(_1)(_3, _2)
    assert flip(op.pow, 2, 3) == 3 ** 2
