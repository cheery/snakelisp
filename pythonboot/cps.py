class Call(object):
    def __init__(self, args):
        self.args = args

class Lambda(object):
    def __init__(self, args, body, uid=''):
        self.args = args
        self.body = body
        self.uid = uid
        self.iscont = True
        self.newlocals = set()

class Let(object):
    def __init__(self, variable, value, body, newlocal=True):
        self.variable = variable
        self.value = value
        self.body = body
        self.newlocal = newlocal

class Variable(object):
    def __init__(self, name=None, uid=''):
        self.name = name
        self.uid = uid
        self.link = None
        self.glob = False
        self.slot = False

class Constant(object):
    def __init__(self, value):
        self.value = value

null = Constant(None)
true = Constant(True)
false = Constant(False)
