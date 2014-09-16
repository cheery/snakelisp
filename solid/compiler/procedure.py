from llvm.core import *

class Procedure(object):
    def __init__(self, expr, toplevel, name, proc, spec, args, body):
        self.expr = expr
        self.toplevel = toplevel
        self.name = name
        self.proc = proc
        self.spec = spec
        self.args = args
        self.body = body
        self.noret = (toplevel.typespace['void'] == spec.return_type)

    def __call__(self):
        bb = Builder.new(self.proc.append_basic_block('entry'))
        env = dict(zip(self.args, self.proc.args))
        ctx = Context(self.toplevel, bb, env)
        for stmt in self.body:
            ctx.stmt(stmt)
        if not ctx.closed:
            if self.noret:
                bb.ret_void()
            else:
                raise Exception("missing return {}".format(self.expr))
        ctx.closed = True

    def call(self, context, expr):
        args = [context.expr(a) for a in expr[1:]]
        return context.bb.call(self.proc, args)


class Context(object):
    def __init__(self, toplevel, bb, env):
        self.toplevel = toplevel
        self.bb = bb
        self.env = env
        self.closed = False

    def expr(self, expr):
        if expr.islist and len(expr) > 0:
            unit = self.expr(expr[0])
            if not unit.noret:
                return unit.call(self, expr)
        return self.atom(expr)

    def stmt(self, expr):
        if expr.islist and len(expr) > 0:
            unit = self.expr(expr[0])
            return unit.call(self, expr)
        raise Exception("not an stmt: {}".format(expr))

    def atom(self, expr):
        globs = self.toplevel.globspace
        if expr.assym in globs:
            return globs[expr.assym]
        if expr.isnum:
            long_t = self.toplevel.typespace['long']
            return Constant.int(long_t, expr.value)
        if expr.isstring:
            s = Constant.stringz(expr.value.encode('utf-8'))
            mem = self.toplevel.constant(s)
            return self.bb.gep(mem, [Constant.int(Type.int(), 0)]*2)
        raise Exception("atom undefined {}".format(expr))
