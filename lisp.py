#!/usr/bin/env python
from blip import ListNode, TextNode, MarkNode, isList, isText, isMark, open_list
import json
import transpiler
from cps import Call, Lambda, Assign, Variable, Constant, Environ, null, true, false
import subprocess
import sys
import re

# call = Call([arguments]), call[i]
# lambda = Lambda([arguments], body), lambda[i]
# Assign(var, val, body)
# Variable(name, value)
# Constant(value)

def main():
    path = sys.argv[1]
    mks = []
    env = Environ()
    ret = env.new_argument("cont", False)

    env = env.new_environ()
    ret = env.new_argument('cont', False)
    exprs = open_list(path).strip_rec()
    #exprs = list(open_list("base.sl")) + list(open_list(path))
    program = env.close(compile_list(exprs, env, ret))
    program = program.coalesce()

    snakesource = "snakelisp.c"

    rootdecl = re.compile(r'newRoot\("(.+)",')
    with open(snakesource) as fd:
        src = fd.read()
        c_roots = dict((decl, "(root+{})".format(i)) for i, decl in enumerate(rootdecl.findall(src)))

    c_api = {
        "uncallable-hook": "&uncallable_hook",
        "type-error-hook": "&type_error_hook",
    }
    c_use = set()
    for var in env.seal():
        if var.name in c_roots:
            var.c_handle = c_roots[var.name]
            continue
        var.c_handle = c_api[var.name]
        c_use.add(var.c_handle)
    cdefns = ["extern value_t {};".format(value[1:]) for value in c_use]

    #import visuals
    #visuals.create_graph("demo.png", program)

    source = transpiler.transpile(program, cdefns, path)
    open(path+'.c', 'w').write(source)
    subprocess.call(["gcc", path+'.c', snakesource, "-I.", "-lm"])

constants = {'null': null, 'true':true, 'false':false}

def compile(expr, env, k):
    if isList(expr, 'include') and isText(expr[0]):
        return compile_list(open_list(expr[0].text).strip_rec(), env, k)
    if isList(expr, 'let') and isText(expr[0]):
        var = env.get_local(expr[0].text)
        return compile(expr[1], env, 
            (lambda val: Assign(var, val, retrieve(k, val))))
    if isList(expr, 'set') and isText(expr[0]):
        var = env.lookup(expr[0].text)
        return compile(expr[1], env, 
            (lambda val: Assign(var, val, retrieve(k, val))))
    if isList(expr, 'cond'):
        return compile_cond(expr, env, k)
    if isList(expr, 'while'):
        return compile_while(expr, env, k)
    if isList(expr, 'func'):
        env = env.new_environ()
        ret = env.new_argument('cont', False)
        for sym in expr[0]:
            assert sym.label == ''
            env.new_argument(sym.text)
        return retrieve(k, env.close(compile_list(expr[1:], env, ret)))
    if isList(expr, 'infix') and len(expr) == 3:
        return compile(ListNode([expr[1], expr[0], expr[2]]), env, k)
    if isList(expr, ''):
        params = []
        seq = list(expr)
        def next_parameter(param):
            params.append(param)
            if len(seq) > 0:
                return compile(seq.pop(0), env, next_parameter)
            else:
                callee = params.pop(0)
                return Call([callee, lift(k)] + params)
        return compile(seq.pop(0), env, next_parameter)
    #if expr.group == 'integer':
    #    return retrieve(k, Constant(expr.value))
    #if expr.group == 'double':
    #    return retrieve(k, Constant(expr.value))
    if isText(expr, "string"):
        return retrieve(k, Constant(expr.text))
    if isText(expr, ''):
        if expr.text[:1].isdigit():
            return retrieve(k, Constant(int(expr.text)))
        if expr.text in constants:
            param = constants[expr.text]
        else:
            param = env.lookup(expr.text)
        return retrieve(k, param)
    raise Exception("what is {}?".format(expr))

def compile_list(exprs, env, k):
    seq = list(exprs)
    def next_parameter(param):
        if len(seq) > 1:
            return compile(seq.pop(0), env, next_parameter)
        else:
            return compile(seq.pop(0), env, k)
    if len(exprs) == 0:
        return retrieve(k, null)
    return next_parameter(null)

def retrieve(k, param):
    if callable(k):
        return k(param)
    else:
        return Call([k, param])

def lift(k):
    if callable(k):
        x = Variable()
        return Lambda([x], k(x))
    else:
        return k

def compile_cond(expr, env, k):
    seq = list(expr[0:])
    if len(seq) == 0:
        return retrieve(k, null)
    def next_cond(k):
        if len(seq) == 0:
            return retrieve(k, null)
        head = seq.pop(0)
        if len(seq) == 0 and isList(head, 'else'):
            return compile_list(head[0:], env, k)
        if isList(head, 'else'):
            raise Exception("invalid cond expression")
        return compile(head[0], env,
            (lambda truth: pick(env, k, truth,
                enclose(head[1:], env),
                lambdaCont(next_cond))))
    return next_cond(k)

def compile_while(expr, env, k):
    self = Variable()
    seq  = expr[1:]
    def compile_body(k):
        return compile_list(expr[1:], env, (lambda _: Call([self, lift(k)])))
    cont = Variable()
    looplambda = Lambda([cont], compile(expr[0], env,
        (lambda truth: pick(env, cont, truth, lambdaCont(compile_body), lambdaNull()))))
    return Assign(self, looplambda, Call([self, lift(k)]), True)

def pick(env, k, truth, yes, no):
    return Call([env.new_implicit('pick'), lift(k), truth, yes, no])

def lambdaNull():
    cont = Variable()
    return Lambda([cont], Call([cont, null]))

def lambdaCont(func):
    cont = Variable()
    return Lambda([cont], func(cont))

def enclose(exprs, env):
    cont = Variable()
    return Lambda([cont], compile_list(exprs, env, cont))

#def open_list(path):
#    with open(path, 'r') as fd:
#        plop = json.load(fd)
#    return decodeJson(plop)
#
#def decodeJson(node):
#    if node["type"] == "list":
#        return ListNode([decodeJson(a) for a in node["list"]], node["label"] or '').strip()
#    elif node["type"] == 'text':
#        return TextNode(node["text"], node["label"] or '')
#    elif node["type"] == 'mark':
#        return MarkNode(node["label"] or '')
#    else:
#        raise Exception("unknown {}".format(node))

if __name__ == '__main__':
    main()
