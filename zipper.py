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

  def int8(self, int8):
    self.buffer.frombytes(struct.pack('b', int8))

  def int32(self, int32):
    self.buffer.frombytes(struct.pack('l', int32))

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
    return self.buffer[:length]

  def bits(self, length):
    bits = self.buffer[:length]
    del self.buffer[:length]
    return bits

  def int8(self):
    return self._unpack_format('b')

  def int32(self):
    return self._unpack_format('l')

  def _unpack_format(self, format):
    length = struct.calcsize(format) * 8
    bits = self.bits(length)
    return struct.unpack(format, bits.tobytes())[0]

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

  raise ValueError('byte ({}) not found in table'.format(byte))

def look_up_bits(table, unpacker):
  for row in table:
    next_bits = unpacker.peek(len(row.bits))
    if bitarray(row.bits) == next_bits:
      unpacker.bits(len(row.bits))
      return row.byte

  raise ValueError('bits not found in table')

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
