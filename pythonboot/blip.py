import sys
header = "\x89BLIP(alpha)\x0D\x0A\x1A\x0A"

def main():
    node = open_list(sys.argv[1])
    save_list(sys.argv[2], node)

def open_list(path):
    with open(path, 'rb') as fd:
        if path.endswith('.json'):
            import json
            return decodeJson(json.load(fd))
        else:
            return read_file(fd)

def save_list(path, node):
    with open(path, 'wb') as fd:
        write_file(fd, node)

def decodeJson(node):
    if node["type"] == "list":
        return ListNode([decodeJson(a) for a in node["list"]], node["label"] or '')
    elif node["type"] == 'text':
        return TextNode(node["text"], node["label"] or '')
    elif node["type"] == 'mark':
        return MarkNode(node["label"] or '')
    else:
        raise Exception("unknown {}".format(node))

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
    value = a << 0 | b << 8 | c << 16 | d << 24
    return value

def write_file(fd, node):
    fd.write(header)
    write_node(fd, node)

def write_node(fd, node):
    uid  = node.uid.encode('utf-8') if node.uid is not None else ''
    lab  = node.label.encode('utf-8')
    assert len(uid) <= 127
    assert len(lab) <= 127
    def begin(length):
        assert length <= 0xffff
        info = node._BLIP_TYPE
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
    fd.write(''.join(map(chr, (a,b,c,d))))

class ListNode(object):
    _BLIP_TYPE = 0
    def __init__(self, nodes, label='', uid=''):
        self.nodes = list(nodes)
        self.label = label
        self.uid = uid

    def __getitem__(self, index):
        return self.nodes[index]

    def __len__(self):
        return len(self.nodes)

    def strip(self):
        return ListNode([a for a in self if not isMark(a, 'cr')], self.label)

    def strip_rec(self):
        return ListNode([a.strip_rec() for a in self if not isMark(a, 'cr')], self.label)

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
        self.uid = uid

    def __repr__(self):
        return "Text:{}:{!r}".format(self.label, self.text)

    def strip_rec(self):
        return self

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
        self.uid = uid

    def __repr__(self):
        return "Data:{}:{!r}".format(self.label, self.data)

    def strip_rec(self):
        return self

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
        self.uid = uid

    def __repr__(self):
        return "Mark:{}".format(self.label)

    def strip_rec(self):
        return self

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

if __name__=='__main__':
    main()
