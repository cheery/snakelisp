header = "\x89BLIP(alpha)\x0D\x0A\x1A\x0A"

def read_file(fd):
    assert fd.read(len(header)) == header
    return read_node(fd)

def read_node(fd):
    info = read_integer(fd)
    cls = nodespecs[info >> 0 & 3]
    uidlen = info >> 2 & 127
    lablen = info >> 9 & 127
    datlen = info >> 16 & 0xffff
    uid = fd.read(uidlen).decode('utf-8')
    lab = fd.read(lablen).decode('utf-8')
    return cls._decode_node(fd, uid, lab, datlen)

def read_integer(fd):
    a, b, c, d = map(ord, fd.read(4))
    return sum(a << 0, b << 8, c << 16, d << 24)

def write_file(fd, node):
    fd.write(header)
    write_node(fd, node)

def write_node(fd, node):
    info = node._BLIP_TYPE
    uid  = node.uid.encode('utf-8')
    lab  = node.label.encode('utf-8')
    assert len(uid) <= 127
    assert len(lab) <= 127
    def begin(length):
        assert length <= 0xffff
        info |= len(uid) << 2
        info |= len(lab) << 9
        info |= length << 16
        write_integer(fd, info)
        fd.write(uid)
        fd.write(lab)
        return fd
    node._encode_node(begin)

def write_integer(fd, value):
    a = value >> 0 & 255
    b = value >> 8 & 255
    c = value >> 16 & 255
    d = value >> 24 & 255
    return ''.join(map(chr, (a,b,c,d)))

class ListNode(object):
    _BLIP_TYPE = 0
    def __init__(self, nodes, label='', uid=''):
        self.nodes = list(nodes)
        self.label = label

    def __getitem__(self, index):
        return self.nodes[index]

    def __len__(self):
        return len(self.nodes)

    def strip(self):
        return ListNode([a for a in self if not isMark(a, 'cr')], self.label)

    def __repr__(self):
        return "List:{}/{}".format(self.label, len(self))

    @classmethod
    def _decode_node(cls, fd, uid, label, length):
        nodes = [read_node(fd) for i in range(length)]
        return cls(nodes, label, uid)

    def _encode_node(self, begin):
        fd = begin(len(self))
        for node in self:
            write_node(fd, node)

class TextNode(object):
    _BLIP_TYPE = 1
    def __init__(self, text, label='', uid=''):
        self.text = text
        self.label = label

    def __repr__(self):
        return "Text:{}:{!r}".format(self.label, self.text)

    @classmethod
    def _decode_node(cls, fd, uid, label, length):
        text = fd.read(length).decode('utf-8')
        return cls(text, label, uid)

    def _encode_node(self, begin):
        data = self.text.encode('utf-8')
        fd = begin(len(data))
        fd.write(data)

class DataNode(object):
    _BLIP_TYPE = 2
    def __init__(self, data, label='', uid=''):
        self.data = data
        self.label = label

    def __repr__(self):
        return "Data:{}:{!r}".format(self.label, self.data)

    @classmethod
    def _decode_node(cls, fd, uid, label, length):
        data = fd.read(length)
        return cls(data, label, uid)

    def _encode_node(self, begin):
        fd = begin(len(self.data))
        fd.write(self.data)

class MarkNode(object):
    _BLIP_TYPE = 3
    def __init__(self, label='', uid=''):
        self.label = label

    def __repr__(self):
        return "Mark:{}".format(self.label)

    @classmethod
    def _decode_node(cls, fd, uid, label, length):
        return cls(label, uid)

    def _encode_node(self, begin):
        begin(0)

nodespecs = dict((a._BLIP_TYPE, a)
        for a in [ListNode, DataNode, TextNode, MarkNode])

def isList(node, label=None):
    return isinstance(node, ListNode) and (label is None or node.label == label)

def isText(node, label=None):
    return isinstance(node, TextNode) and (label is None or node.label == label)

def isMark(node, label=None):
    return isinstance(node, MarkNode) and (label is None or node.label == label)
