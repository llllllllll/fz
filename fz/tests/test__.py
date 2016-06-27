from functools import partial
import operator as op

import pytest

from _ import _1, _2, _3, _f, _binop_map


def test_identity():
    ob = object()
    assert _1(ob) is ob
    assert _2(None, ob) is ob


@pytest.mark.parametrize('op', map(partial(getattr, op), _binop_map))
def test_arithmetic(op):
    f = op(_1, 1)

    for n in range(-5, 5):
        assert f(n) == op(n, 1)
