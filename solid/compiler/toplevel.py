from llvm.core import *
from typevalue import *
from procedure import Procedure

class Toplevel(object):
    def __init__(self, typespace, globspace, macros, module):
        self.typespace = typespace
        self.globspace = globspace
        self.macros = macros
        self.module = module

    def resolve(self, expr):
        for macro in reversed(self.macros):
            cont = macro(self, expr)
            if callable(cont):
                return cont
        raise Exception("macro missing for {}".format(expr))

macros = []

@macros.append
def procedure_macro(toplevel, expr):
    if len(expr) < 4:
        return
    head, name, spec, args = expr[:4]
    body = expr[4:]
    if head.assym != 'procedure':
        return
    if not name.issym:
        return
    if not args.islist:
        return
    tp = function_signature(toplevel, spec)
    args = read_arglist(args)
    if not isinstance(tp, FunctionType):
        raise Exception("invalid function signature {}".format(tp))
    proc = toplevel.module.add_function(tp, name.assym)
    procedure = Procedure(expr, toplevel, name.assym, proc, tp, args, body)
    toplevel.globspace[name.assym] = procedure
    return procedure

def read_arglist(args):
    out = []
    for a in args:
        if not a.issym:
            raise Exception("invalid argument name {}".format(tp))
        out.append(a.assym) 
    return out
