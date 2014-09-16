from llvm.core import *
from typevalue import *
from procedure import Procedure

class Toplevel(object):
    def __init__(self, typespace, globspace, macros, module):
        self.typespace = typespace
        self.globspace = globspace
        self.macros = macros
        self.module = module
        self.globalvars = {}

    def constant(self, value):
        if value in self.globalvars:
            return self.globalvars[value]
        var = self.module.add_global_variable(value.type, "g{}".format(len(self.globalvars)))
        var.initializer = value
        var.global_constant = True
        self.globalvars[value] = var
        return var

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

class FFIFunc(object):
    def __init__(self, proc):
        self.proc = proc

    def call(self, context, expr):
        args = [context.expr(a) for a in expr[1:]]
        return context.bb.call(self.proc, args)

@macros.append
def ffi_function(toplevel, expr):
    if not expr.islist:
        return
    if len(expr) != 3:
        return
    if expr[0].assym != 'c-function':
        return
    head, name, spec = expr
    if not name.issym:
        return
    tp = function_signature(toplevel, spec)
    if not isinstance(tp, FunctionType):
        raise Exception("invalid function signature {}".format(tp))
    toplevel.globspace[name.assym] = FFIFunc(toplevel.module.add_function(tp, name.assym))
    return (lambda: None)


#        if issym(head, "struct"):
#            name = sym(expr[1])
#            environ[name] = tp = Type.opaque(name)
#            pipeline.append(partial(build_struct, tp, environ, expr[2:]))
#def build_struct(tp, environ, fields):
#    g = iter(fields)
#    types = []
#    names = []
#    for spec, name in zip(g, g):
#        types.append(typeval(environ, spec))
#        names.append(sym(name))
#    tp.set_body(types)
#    tp.names = names
