
from io import BufferedIOBase
import struct
from typing import BinaryIO


def read_integer(file: BufferedIOBase, size: int = 4, signed: bool = False) -> int:
    return int.from_bytes(file.read(size), byteorder="little", signed=signed)


def read_float(file: BufferedIOBase, size: int = 4, signed: bool = False) -> float:
    data = file.read(size)
    value = int.from_bytes(data, byteorder="little", signed=signed)
    return float(value)


def read_float2(file: BinaryIO, size: int = 4) -> float:
    """
    Another attempt to read a float to see any differences.
    """
    data = file.read(size)
    return struct.unpack('<f', data)[0]


def read_string(file: BufferedIOBase, descriptor_length: int = 4) -> str:
    size = int.from_bytes(file.read(descriptor_length), byteorder="little")
    raw_bytes = file.read(size)
    null_terminator_index = raw_bytes.find(b'\x00')
    if null_terminator_index != -1:
        raw_bytes = raw_bytes[:null_terminator_index]
    return raw_bytes.decode("utf-8")


def read_bytes(file: BufferedIOBase, size: int) -> bytes:
    return file.read(size)


def read_bytes_as_string(file: BufferedIOBase, size: int) -> str:
    raw_bytes = file.read(size)
    null_terminator_index = raw_bytes.find(b'\x00')
    if null_terminator_index != -1:
        raw_bytes = raw_bytes[:null_terminator_index]
    return raw_bytes.decode("utf-8")
