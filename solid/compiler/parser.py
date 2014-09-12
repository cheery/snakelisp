def main():
    import sys
    while True:
        line = sys.stdin.readline()
        prog = parse(line)
        print(prog)

IDLE    = 0
COMMENT = 1
DIGIT   = 2
DIGITS  = 3
DOUBLE  = 4
SINGLEQUOTE = 5
DOUBLEQUOTE = 6
SYMBOL  = 7
ESCAPE  = 8
DOTS    = 9

def parse(source, index=0):
    stack   = []
    current = Annotation(index, index, 'list', [])
    for token in tokenize(source, index):
        current.stop = token.stop
        if token.group == 'left':
            next = Annotation(token.start, token.stop, 'list', [])
            current.value.append(next)
            stack.append(current)
            current = next
        elif token.group == 'right':
            if len(stack) > 0:
                current = stack.pop(-1)
        elif token.group == 'attribute':
            if len(current.value) > 0:
                subj = current.value.pop(-1)
                obj  = Annotation(subj.start, token.stop, 'member', [subj, token.value])
            else:
                obj  = token
            current.value.append(obj)
        else:
            current.value.append(token)
    while stack:
        last    = current
        current = stack.pop(-1)
        current.stop = last.stop
    return current

def tokenize(source, index=0):
    recov  = IDLE
    state  = IDLE
    string = ''
    for ch in source:
        if state == SYMBOL:
            if issym(ch):
                string += ch
            elif string + ch == '..':
                string += ch
                state = DOTS
            elif string.startswith('.'):
                yield Annotation(start, index, 'attribute', string)
                state = IDLE
            else:
                yield Annotation(start, index, 'symbol', string)
                state = IDLE
        elif state == DIGIT:
            if ch == 'x' or isnum(ch):
                string += ch
                state = DIGITS
            elif ch == '.':
                string += ch
                state = DOUBLE
            else:
                yield Annotation(start, index, 'num', make_num(string))
                state = IDLE
        elif state == DIGITS:
            if isnum(ch) or 'a' <= ch.lower() <= 'f':
                string += ch
            elif ch == '.':
                string += ch
                state = DOUBLE
            else:
                yield Annotation(start, index, 'num', make_num(string))
                state = IDLE
        elif state == DOUBLE:
            if isnum(ch):
                string += ch
            else:
                yield Annotation(start, index, 'double', float(string))
                state = IDLE
        elif state == DOTS:
            if ch == '.':
                string += ch
            else:
                yield Annotation(start, index, 'dots', string)
                state = IDLE

        if state == IDLE:
            string = ''
            start  = index
            if ch == '(':
                yield Annotation(index, index+1, 'left', ch)
            elif ch == ')':
                yield Annotation(index, index+1, 'right', ch)
            elif ch == '#':
                state = COMMENT
            elif isnum(ch):
                state = DIGIT
                string += ch
            elif ch == "'":
                state = SINGLEQUOTE
                string += ch
            elif ch == '"':
                state = DOUBLEQUOTE
                string += ch
            elif not isspace(ch):
                state = SYMBOL
                string += ch
        elif state == COMMENT:
            if ch == '\n':
                state = IDLE
        elif state == SINGLEQUOTE:
            string += ch
            if ch == '\\':
                recov = state
                state = ESCAPE
            if ch == "'":
                yield Annotation(start, index+1, 'string', string.decode('unicode-escape'))
                state = IDLE
        elif state == DOUBLEQUOTE:
            string += ch
            if ch == '\\':
                recov = state
                state = ESCAPE
            if ch == '"':
                yield Annotation(start, index+1, 'string', string.decode('unicode-escape'))
                state = IDLE
        elif state == ESCAPE:
            string += ch
            state = recov
        index += 1

def issym(ch):
    return ch not in ('(', ')', '#', '"', "'", '\n', '.') and not isspace(ch)

def isnum(ch):
    return ch.isdigit()

def isspace(ch):
    return ch.isspace()

def make_num(string):
    digits = '0' + string[2:]
    if string[0:2] == '0x':
        return int(digits, 16)
    if string[1:2] == 'x':
        return int(digits, int(string[0]))
    return int(string)

class Annotation(object):
    def __init__(self, start, stop, group, value):
        self.start = start
        self.stop  = stop
        self.group = group
        self.value = value

    @property
    def islist(self):
        return self.group == 'list'

    @property
    def issym(self):
        return self.group == 'symbol'

    @property
    def isnum(self):
        return self.group == 'num'

    @property
    def isdouble(self):
        return self.group == 'double'

    @property
    def isstring(self):
        return self.group == 'string'

    @property
    def assym(self):
        if self.issym:
            return self.value

    def __repr__(self):
        if self.group == 'list':
            return "(" + ' '.join(map(repr, self.value)) + ")"
        elif self.group == 'symbol':
            return self.value
        elif self.group == 'num':
            return repr(self.value)
        elif self.group == 'double':
            return repr(self.value)
        elif self.group == 'string':
            return repr(self.value)
        else:
            return '<{0.group} {0.value!r} {0.start}:{0.stop}>'.format(self)

    def __getitem__(self, index):
        return self.value[index]

    def __len__(self):
        return len(self.value)

if __name__=='__main__':
    main()
