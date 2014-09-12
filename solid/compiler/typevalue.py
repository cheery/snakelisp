from llvm.core import *

def function_signature(toplevel, spec):
    if spec.islist:
        ts = [typevalue(toplevel, a) for a in spec]
        return Type.function(ts.pop(0), ts)
    return typevalue(toplevel, spec)

def typevalue(toplevel, expr):
    if expr.issym:
        name = expr.assym.rstrip("*")
        if name in toplevel.typespace:
            tp = toplevel.typespace[name]
            for i in range(len(name), len(expr.assym)):
                tp = Type.pointer(tp)
            return tp
    raise Exception("type missing for {}".format(expr))
