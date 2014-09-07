from pythonboot.cps import Call, Lambda, Let, Constant, Variable
from string import printable

def transpile(program, globs, environ={}, sourcename="()"):
    listing = [
            '/* generated from: {} */'.format(sourcename),
            '#include "snake.h"'
    ]
    lambdas = harvest_lambdas(program, [])
    harvest_upscope(program)
    for i, lam in enumerate(lambdas):
        lam.c_uid = "f{}".format(i)
        listing.append("DECLARATION({});".format(lam.c_uid))

    planters = []
    for i, glob in enumerate(globs):
        glob.c_uid = "root[{}]".format(i)
        planters.append("  plant({});".format(environ[glob.name]))

    for lam in lambdas:
        header = [
                lam.c_uid,
                ["false", "true"][lam.iscont],
                to_cstring(lam.uid),
                str(len(lam.upscope))]
        header += list(to_cstring(var.uid) for var in lam.upscope)

        listing.append("DEFINITION({})".format(', '.join(header)))
        listing.append("{")

        if lam is program:
            listing.extend(planters)

        binding = {}
        for i, arg in enumerate(lam.args):
            name = "b{}".format(len(binding))
            if arg.slot:
                listing.append("  slot_t *{} = newSlot(ARGUMENT({}));".format(name, i))
            else:
                listing.append("  value_t {} = ARGUMENT({});".format(name, i))
            binding[arg] = name
        
        for i, var in enumerate(lam.upscope):
            binding[var] = "SLOT({})".format(i)

        for var in lam.newlocals:
            name = "b{}".format(len(binding))
            if arg.slot:
                listing.append("  slot_t *{} = newSlot(null);".format(name))
            else:
                listing.append("  value_t {} = null;".format(name))
            binding[var] = name

        body = lam.body
        while isinstance(body, Let):
            listing.append("  {} = {};".format(
                atom_string(body.variable, binding),
                atom_string(body.value, binding)))
            body = body.body
        assert isinstance(body, Call)
        args = [atom_string(arg, binding) for arg in body.args]
        listing.append("  call({});".format(', '.join(args)))
        listing.append("}")

    listing.append("MAIN_ENTRY(&{});".format(program.c_uid))

    return '\n'.join(listing) + '\n'

def harvest_lambdas(node, lambdas):
    if isinstance(node, Lambda):
        lambdas.append(node)
        lambdas = harvest_lambdas(node.body, lambdas)
    elif isinstance(node, Call):
        for arg in node.args:
            lambdas = harvest_lambdas(arg, lambdas)
    elif isinstance(node, Let):
        lambdas = harvest_lambdas(node.value, lambdas)
        lambdas = harvest_lambdas(node.body, lambdas)
    return lambdas

def harvest_upscope(node):
    if isinstance(node, Lambda):
        unbound = harvest_upscope(node.body)
        for arg in node.args:
            unbound.discard(arg)
        for newlocal in node.newlocals:
            unbound.discard(newlocal)
        node.upscope = list(unbound)
        for var in unbound:
            var.slot = True
        return unbound
    elif isinstance(node, Call):
        unbound = set()
        for expr in node.args:
            unbound |= harvest_upscope(expr)
        return unbound
    elif isinstance(node, Let):
        unbound = harvest_upscope(node.body)
        if node.newlocal:
            unbound.discard(node.variable)
        unbound |= harvest_upscope(node.value)
        return unbound
    elif isinstance(node, Variable) and not node.glob:
        if node.link is not None:
            node = node.link
        return {node}
    return set()

def to_cstring(string):
    string = string.encode('utf-8')
    return '"' + ''.join((ch if ch in printable and ch != '\n' else "\\x%02x" % ord(ch)) for ch in string) + '"'

def atom_string(atom, binding):
    if isinstance(atom, Variable) and atom in binding:
        if atom.slot:
            return "{}->value".format(binding[atom])
        else:
            return binding[atom]
    elif isinstance(atom, Variable) and atom.glob:
        return atom.c_uid
    elif isinstance(atom, Lambda):
        header = ['&'+atom.c_uid] + list(slot_string(a, binding) for a in atom.upscope)
        return "(value_t)procClosure({})".format(', '.join(header))
    elif isinstance(atom, Constant) and atom.value is None:
        return "null"
    elif isinstance(atom, Constant) and atom.value is True:
        return "boxBoolean(true)"
    elif isinstance(atom, Constant) and atom.value is False:
        return "boxBoolean(false)"
    elif isinstance(atom, Constant) and isinstance(atom.value, (int, long)):
        return "boxFixnum({})".format(atom.value)
    elif isinstance(atom, Constant) and isinstance(atom.value, float):
        return "boxDouble({})".format(atom.value)
    elif isinstance(atom, Constant) and isinstance(atom.value, (str, unicode)):
        return "newCString({})".format(to_cstring(atom.value))
    elif isinstance(atom, Constant):
        raise Exception("is {!r} an atom?".format(atom.value))
    else:
        raise Exception("is {} an atom?".format(atom))

def slot_string(slot, binding):
    assert slot.slot
    return binding[slot]
