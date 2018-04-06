#!/usr/bin/env python3
import sys
import struct

from bitarray import bitarray
from collections import namedtuple

class BinPacker:
  def __init__(self):
    self.buffer = bitarray(endian='little')

  def bits(self, bits):
    self.buffer.extend(bits)
    return self

  def int8(self, int8):
    self.buffer.frombytes(struct.pack('b', int8))
    return self

  def int32(self, int32):
    self.buffer.frombytes(struct.pack('l', int32))
    return self

  def pack(self):
    return self.buffer.tobytes()

  def debug(self):
    print(self.buffer)

    packed = self.pack()
    print('Packed string ({}): "{}"'.format(len(packed), packed))

class BinUnpacker:
  def __init__(self, bytes):
    self.buffer = bitarray(endian='little')
    self.buffer.frombytes(bytes)

  def peek(self, length):
    return self.buffer[0:length]

  def bits(self, length):
    bits = self.buffer[0:length]
    self.buffer = self.buffer[length:]
    return bits

  def int8(self):
    next = self.buffer[0:8]
    self.buffer = self.buffer[8:]
    i = struct.unpack('b', next.tobytes())[0]
    return i

  def int32(self):
    next = self.buffer[0:8*8]
    self.buffer = self.buffer[8*8:]
    i = struct.unpack('l', next.tobytes())[0]
    return i

Leaf = namedtuple('Leaf', ('byte', 'count'))
Node = namedtuple('Node', ('left', 'right', 'count'))

TableRow = namedtuple('TableRow', ('byte', 'bits'))

def compress(original):
  tree = build_tree(original)
  table = build_table(tree)

  packer = BinPacker()

  packer.int32(len(original))

  pack_table(table, packer)

  for byte in original.encode('utf8'):
    bits = look_up_byte(table, byte)
    packer.bits(bits)

  return packer.pack()

def decompress(compressed):
  unpacker = BinUnpacker(compressed)

  data_length = unpacker.int32()
  table = unpack_table(unpacker)

  bits = [look_up_bits(table, unpacker) for _ in range(data_length)]
  return bytes(bits).decode('utf8')

def build_tree(original):
  original_bytes = original.encode('utf8')
  unique_bytes = set(original_bytes) # Somehow we have ints now...

  nodes = [Leaf(byte=byte, count=original_bytes.count(byte)) for byte in unique_bytes]

  while len(nodes) > 1:
    node1 = min(nodes, key=lambda x: x.count)
    nodes.remove(node1)

    node2 = min(nodes, key=lambda x: x.count)
    nodes.remove(node2)

    parent = Node(left=node1, right=node2, count=node1.count + node2.count)
    nodes.append(parent)

  return nodes[0]

def build_table(node, path=[]):
  if isinstance(node, Node):
    return build_table(node.left, path=path+[0]) + build_table(node.right, path=path+[1])
  else:
    return [TableRow(node.byte, path)]

def look_up_byte(table, byte):
  for row in table:
    if row.byte == byte:
      return row.bits

  raise ValueError()

def look_up_bits(table, unpacker):
  for row in table:
    next_bits = unpacker.peek(len(row.bits))
    if bitarray(row.bits) == next_bits:
      unpacker.bits(len(row.bits))
      return row.byte

  raise ValueError()

def pack_table(table, packer):
  packer.int8(len(table) - 1)

  for row in table:
    packer.int8(row.byte)
    packer.int8(len(row.bits))
    packer.bits(row.bits)


def unpack_table(unpacker):
  table_length = unpacker.int8() + 1
  table = []

  for _ in range(table_length):
    byte = unpacker.int8()
    bit_count = unpacker.int8()
    bits = unpacker.bits(bit_count)

    table.append(TableRow(byte, bits))

  return table

if len(sys.argv) > 1 and sys.argv[1] == 'compress':
  sys.stdout.buffer.write(compress(sys.stdin.read()))
else:
  sys.stdout.write(decompress(sys.stdin.buffer.read()))

# symbols = dict((chr(row.byte), bitarray(row.bits)) for row in table)
# ba = bitarray()
# ba.encode(symbols, original)
# packer.bits(ba)
