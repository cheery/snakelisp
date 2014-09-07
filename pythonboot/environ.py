from .cps import Lambda, Variable

class Environ(object):
    def __init__(self, parent=None, uid=''):
        self.parent = parent
        self.uid = uid
        self.children = []
        if parent is not None:
            parent.children.append(self)
            self.implicit = parent.implicit
        else:
            self.implicit = {}
        self.cont = Variable('<cont>', ':cont')
        self.args = [self.cont]
        self.bound = {}
        self.newlocals = set()
        self.unbound_local = {}
        self.unbound = set()
        self.closed = False

    def newarg(self, name, uid=''):
        var = self.bound[name] = Variable(name, uid)
        self.args.append(var)
        return var

    def newlocal(self, name, uid=''):
        if name in self.bound:
            return self.bound[name]
        else:
            var = self.bound[name] = Variable(name, uid)
            self.newlocals.add(var)
            return var

    def newimplicit(self, name):
        if name in self.implicit:
            return self.implicit[name]
        else:
            var = self.implicit[name] = Variable(name)
            return var

    def lookup(self, name, uid=''):
        if name in self.bound:
            return self.bound[name]
        elif name in self.unbound_local:
            return self.unbound_local[name]
        else:
            var = self.unbound_local[name] = Variable(name)
            self.unbound.add(var)
            return var

    def close(self, body):
        for child in self.children:
            assert child.closed
            for variable in child.unbound:
                if variable.name in self.bound:
                    variable.link = self.bound[variable.name]
                else:
                    self.unbound.add(variable)
        self.closed = True
        lam = Lambda(self.args, body, self.uid)
        lam.newlocals.update(self.newlocals)
        lam.iscont = False
        return lam

    def seal(self):
        for var in self.unbound:
            var.glob = True
            yield var
        for var in self.implicit.values():
            var.glob = True
            yield var
