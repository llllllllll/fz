import ast
from copy import copy
from inspect import Signature
from uuid import uuid4

from toolz import merge, assoc
from toolz.curried import operator as op

from codetransformer.transformers import asconstants


class _NameSubstitute(ast.NodeTransformer):
    """Substitute the roots of a placeholder lambda with a unique name node.

    Notes
    -----
    ``vist`` mutates this object in place, it should only be used to compile
    once.
    """
    def __init__(self):
        self.name_cache = {}

    def visit_placeholder(self, node):
        try:
            return self.name_cache[node]
        except KeyError:
            self.name_cache[node._name] = name = ast.Name(
                id=node._name,
                ctx=ast.Load(),
            )
            return name


_binop_map = {
    '__add__': (ast.Add, '+'),
    '__sub__': (ast.Sub, '-'),
    '__mul__': (ast.Mult, '*'),
    '__div__': (ast.Div, '/'),
    '__floordiv__': (ast.FloorDiv, '//'),
    '__mod__': (ast.Mod, '%'),
    '__pow__': (ast.Pow, '**'),
    '__and__': (ast.BitAnd, '&'),
    '__or__': (ast.BitOr, '|'),
    '__xor__': (ast.BitOr, '^'),
    '__lshift__': (ast.LShift, '<<'),
    '__rshift__': (ast.RShift, '>>'),
}

_cmpop_map = {
    '__lt__': (ast.Lt, '<'),
    '__le__': (ast.LtE, '<='),
    '__eq__': (ast.Eq, '=='),
    '__ne__': (ast.NotEq, '!='),
    '__ge__': (ast.GtE, '>='),
    '__gt__': (ast.Gt, '>'),
}

_unop_map = {
    '__neg__': (ast.USub, '-'),
    '__invert__': (ast.Invert, '~'),
}

_no_paren_nodes = ast.Attribute, ast.Call, ast.Name


def _normalize_arg(other, constants):
    """Get the name to use to build the string and turn the value into
    something that can go into the ast.

    If needed this will functionally update the constants.

    Parameters
    ----------
    other : any
        The object to normalize.
    constants : dict[str -> any]
        The constant namespace.

    Returns
    -------
    othername : str
        The name to use in the ``_name`` of the lambda.
    other : any
        The normalized value.
    constants : dict[str -> any]
        The potentially updated constants.
    """
    if not isinstance(other, placeholder):
        othername = repr(other)
        name = '_' + uuid4().hex
        constants = assoc(constants, name, other)
        other = ast.Name(id=name, ctx=ast.Load())
    elif other._tree is not other:
        othername = '(%s)' % other._name
    else:
        othername = other._name

    return othername, other, constants


class _class_doc:
    def __init__(self, class_doc, instance_prefix):
        self._class_doc = class_doc
        self._instance_prefix = instance_prefix

    def __get__(self, instance, owner):
        if instance is None:
            return self._class_doc
        return '\n\n'.join((self._instance_prefix, str(instance)))


class placeholder(ast.AST):
    """An object that represents a lambda expression.

    Parameters
    ----------
    name : str
        The name of lambda.
    tree : ast.AST, optional
        The ast for the lambda.
    constants : dict[str -> any], optional
        The constants in the tree.

    Examples
    --------
    >>> (_1 + 1)(2)
    3

    >>> list(map(_1 ** 2, range(5)))
    [0, 1, 4, 9, 16]

    >>> list(map(_1.imag, (1j, 1 + 2j, 2 + 3j)))
    [1.0, 2.0, 3.0]
    """
    __doc__ = _class_doc(__doc__, 'A lambda function which will execute:')
    __slots__ = '_name', '_tree', '_constants', '_maybe_fn'

    def __init__(self, name, tree=None, constants=None):
        self._name = name
        self._tree = tree if tree is not None else self
        self._constants = constants or {}
        self._maybe_fn = None

    @property
    def _compiled_fn(self):
        maybe_fn = self._maybe_fn
        if maybe_fn is None:
            self._maybe_fn = maybe_fn = self._compile()
        return maybe_fn

    @property
    def __signature__(self):
        return Signature.from_function(self._compiled_fn)

    @property
    def _pname(self):
        t = self._tree
        return (
            self._name
            if t is self or isinstance(t, _no_paren_nodes) else
            '(%s)' % self._name
        )

    def __call__(self, *args, **kwargs):
        return self._compiled_fn(*args, **kwargs)

    def __repr__(self):
        return '<%s-lambda: %s>' % (type(self).__name__, self._name)

    def __str__(self):
        return self._name

    def __hash__(self):
        return id(self)

    def __copy__(self):
        return type(self)(self._name, self._tree, self._constants)

    def _compile(self):
        c = _NameSubstitute()
        t = c.visit(copy(self._tree))
        name = repr(self)
        maxarg = max((int(name[1:]) for name in c.name_cache), default=0) + 1
        args = [
            ast.arg(arg='_%d' % n, annotation=None)
            for n in range(1, maxarg)
        ]
        code = compile(
            ast.fix_missing_locations(ast.Module(
                body=[
                    ast.FunctionDef(
                        name=name,
                        args=ast.arguments(
                            args=args,
                            vararg=None,
                            kwonlyargs=[],
                            kw_defaults=[],
                            kwarg=None,
                            defaults=[],
                        ),
                        body=[ast.Return(value=t)],
                        decorator_list=[],
                        returns=None,
                        lineno=1,
                        col_offset=0,
                    ),
                ],
            )),
            name,
            'exec',
        )
        ns = {}
        exec(code, ns)
        return asconstants(**self._constants)(ns[name])

    def __getattr__(self, attr):
        return type(self)(
            '%s.%s' % (self._pname, attr),
            ast.Attribute(
                value=self._tree,
                attr=attr,
                ctx=ast.Load(),
            ),
            self._constants,
        )

    def __getitem__(self, key):
        keyname, key, constants = _normalize_arg(key, self._constants)
        return type(self)(
            '%s[%s]' % (self._pname, keyname),
            ast.Subscript(
                value=self._tree,
                slice=ast.Index(value=key),
                ctx=ast.Load(),
            ),
            constants,
        )

    for opname, (opnode, sym) in _binop_map.items():
        @op.setitem(locals(), opname)
        def _binop(self, other, *, _opnode=opnode, _sym=sym):
            othername, other, constants = _normalize_arg(
                other,
                self._constants,
            )

            return type(self)(
                '%s %s %s' % (self._pname, _sym, othername),
                ast.BinOp(
                    left=self._tree,
                    op=_opnode(),
                    right=other,
                ),
                merge(constants, getattr(other, '_constants', {})),
            )

    for opname, (opnode, sym) in _cmpop_map.items():
        @op.setitem(locals(), opname)  # noqa
        def _binop(self, other, *, _opnode=opnode, _sym=sym):
            othername, other, constants = _normalize_arg(
                other,
                self._constants,
            )

            return type(self)(
                '%s %s %s' % (self._pname, _sym, othername),
                ast.Compare(
                    left=self._tree,
                    ops=[_opnode()],
                    comparators=[other],
                ),
                merge(constants, getattr(other, '_constants', {})),
            )

    del _binop

    for opname, (opnode, sym) in _unop_map.items():
        @op.setitem(locals(), opname)
        def _unop(self, *, _opnode=opnode, _sym=sym):
            return type(self)(
                '%s%s' % (_sym, self._pname),
                ast.UnaryOp(
                    op=_opnode(),
                    operand=self._tree,
                ),
                self._constants,
            )

    del opname, opnode, sym, _unop

    for _fnname in ('abs', 'next', 'iter'):
        @op.setitem(locals(), '__%s__' % _fnname)
        def _fnname(self, *, _fnname=_fnname):
            return type(self)(
                '%s(%s)' % (_fnname, self._name),
                ast.Call(
                    func=ast.Name(id=_fnname, ctx=ast.Load()),
                    args=[self._tree],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                ),
                self._constants,
            )
    del _fnname


class callable_placeholder:
    """A wrapper around a callable for use in a placeholder lambda.

    This is used when you want to call a function on an input to the lambda.
    Normally, call means execute the lambda expression so we need another
    wrapper for this.

    Parameters
    ----------
    fn : callable
        The callable to wrap.
    tree : ast.AST, optional
        The ast for the lambda.
    constants : dict[str -> any], optional
        The constants in the tree.

    Examples
    --------
    >>> def f(a, b):
    ...     return a + b

    >>> _(f)(_1, 2)(3)
    5

    >>> _(print)('a', _1)(1)
    a 1
    """
    __slots__ = '_fn', '_tree', '_constants'

    def __init__(self, fn):
        self._fn = fn
        self._tree = ast.Name(id=self._name, ctx=ast.Load())
        self._constants = {} if isinstance(fn, placeholder) else {
            fn.__name__: fn,
        }

    @property
    def __signature__(self):
        try:
            return self._fn.__signature__
        except AttributeError:
            pass

        try:
            return Signature.from_function(self._fn)
        except TypeError:
            pass

        try:
            return Signature.from_buultin(self._fn)
        except TypeError:
            pass

        return None

    @property
    def _name(self):
        fn = self._fn
        if isinstance(fn, placeholder):
            return fn._name
        return fn.__name__

    def __call__(self, *args, **kwargs):
        constants = self._constants
        argnames = []
        argvalues = []
        for arg in args:
            argname, argvalue, constants = _normalize_arg(arg, constants)
            argnames.append(argname)
            argvalues.append(argvalue)

        kwargnames = []
        kwargvalues = []
        for k, v in kwargs.items():
            kwargname, kwargvalue, constants = _normalize_arg(v, constants)
            kwargnames.append(kwargname)
            kwargvalues.append(kwargvalue)

        return placeholder(
            '%s(%s%s%s)' % (
                self._name,
                ', '.join(argnames),
                ', ' if args and kwargs else '',
                ', '.join(map(op.mod('%s=%s'), kwargnames)),
            ),
            ast.Call(
                func=self._tree,
                args=argvalues,
                keywords=kwargvalues,
                starargs=None,
                kwargs=None,
            ),
            constants,
        )

    def __repr__(self):
        return '<%s: %s>' % (type(self).__name__, self._name)


_ = _f = callable_placeholder


# populate the namespace with _1, _2, ... _255
for n in range(255):
    name = '_%d' % (n + 1)
    globals()[name] = placeholder(name)
del name
