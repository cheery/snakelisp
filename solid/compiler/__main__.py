from parser import parse
import os
import sys
import subprocess
from os.path import join
from llvm.core import *
from functools import partial
from toplevel import Toplevel, macros

#macros = {
#    '+/2': (lambda bb, environ, globales, scope, expr: )
#}
#def build_procedure(proc, environ, globales, scope, body):
#    bb = Builder.new(proc.append_basic_block("entry"))
#    for expr in body:
#        head = expr[0]
#        if issym(head, "return") and len(expr) == 1:
#            bb.ret_void()
#        elif issym(head, "return") and len(expr) == 2:
#            bb.ret(build_expr(bb, environ, globales, scope, expr[1]))
#        else:
#            build_expr(bb, environ, globales, scope, expr)

def build(path, source):
    toplevel = Toplevel(
        typespace = {
            "void": Type.void(),
            "char": Type.int(8),
            "int": Type.int(32),
            "long": Type.int(64),
        },
        globspace = {
        },
        macros = list(macros),
        module = Module.new(path)
    )
    pipeline = []

    for expr in source:
        pipeline.append(toplevel.resolve(expr))

    for func in pipeline:
        cont = func()
        if callable(cont):
            pipeline.append(cont)
    return toplevel.module

try:
    path = sys.argv[1]
    with open(path) as fd:
        source = parse(fd.read())
    module = build(path, source)
    module.verify()
except Exception as e:
    print("error: " + str(e))
    sys.exit(1)

def gcc(src, dst, march=None):
    if march == 'mipsel':
        llc_postfix = ['-march=mipsel']
        cc = '/opt/gcw0-toolchain/usr/bin/mipsel-gcw0-linux-uclibc-gcc'
    else:
        llc_postfix = []
        cc = 'gcc'
    status = subprocess.call(['llc', src, '-o', dst+'.s'] + llc_postfix)
    if status != 0:
        sys.exit(status)
    status = subprocess.call([cc, dst+'.s', '-o', dst])
    if status != 0:
        sys.exit(status)

source = module.id + '.bc'
with open(source, 'w') as fd:
    module.to_bitcode(fd)
gcc(source, module.id + '.native')
gcc(source, module.id + '.mipsel', "mipsel")
