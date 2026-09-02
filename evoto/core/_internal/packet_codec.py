"""
Framed packet codec with optional binary blob (protocol v2).

Layout: [2-byte magic][1-byte version][4-byte JSON len][4-byte binary len][JSON][binary][4-byte CRC32]

Changes vs v1:
- Added protocol version byte
- CRC32 over payload (was 2-byte XOR)
- 64MB max packet guard

Fields:
- Magic: 0xEF 0xFE
- Version: currently 2
- Lengths: big-endian uint32
- JSON: UTF-8
- Binary: raw bytes (optional)
- CRC32: zlib-compatible over version byte through end of binary
"""

import struct
import zlib
import logging

logger = logging.getLogger(__name__)


class PacketCodec:
    """Encoder/decoder for protocol v2 packets."""

    MAGIC_1 = 0xEF
    MAGIC_2 = 0xFE
    PROTOCOL_VERSION = 2
    HEADER_SIZE = 11   # 2 magic + 1 version + 4 json + 4 binary
    TAIL_SIZE = 4      # crc32
    MAX_PACKET_SIZE = 64 * 1024 * 1024  # 64MB

    @staticmethod
    def calculate_crc32(data: bytes) -> int:
        """CRC32 matching the zlib polynomial used on the wire."""
        return zlib.crc32(data) & 0xFFFFFFFF

    @staticmethod
    def encode(json_data: bytes, binary_data: bytes = b'') -> bytes:
        """
        Encode one packet.

        Args:
            json_data: UTF-8 JSON bytes
            binary_data: optional binary attachment
        """
        json_length = len(json_data)
        binary_length = len(binary_data)

        header = struct.pack('>BBBII',
            PacketCodec.MAGIC_1, PacketCodec.MAGIC_2,
            PacketCodec.PROTOCOL_VERSION,
            json_length, binary_length
        )

        crc_data = header[2:] + json_data + binary_data
        crc = PacketCodec.calculate_crc32(crc_data)
        tail = struct.pack('>I', crc)

        return header + json_data + binary_data + tail

    @staticmethod
    def decode(buffer: bytearray) -> tuple[list[tuple[bytes, bytes]], bytearray]:
        """
        Decode as many full packets as possible from buffer.

        Args:
            buffer: mutable incoming bytes (prefer bytearray to avoid O(n^2) copies)

        Returns:
            (list of (json_bytes, binary_bytes), leftover tail)
        """
        packets = []
        offset = 0

        while offset + PacketCodec.HEADER_SIZE + PacketCodec.TAIL_SIZE <= len(buffer):
            magic_pos = -1
            for i in range(offset, len(buffer) - PacketCodec.HEADER_SIZE - PacketCodec.TAIL_SIZE + 1):
                if buffer[i] == PacketCodec.MAGIC_1 and buffer[i + 1] == PacketCodec.MAGIC_2:
                    magic_pos = i
                    break

            if magic_pos == -1:
                if len(buffer) - offset > 1:
                    offset = len(buffer) - 1
                break

            offset = magic_pos

            if offset + PacketCodec.HEADER_SIZE > len(buffer):
                break

            m1, m2, version, json_length, binary_length = struct.unpack(
                '>BBBII', bytes(buffer[offset:offset + PacketCodec.HEADER_SIZE])
            )

            total_size = PacketCodec.HEADER_SIZE + json_length + binary_length + PacketCodec.TAIL_SIZE

            if total_size > PacketCodec.MAX_PACKET_SIZE:
                logger.warning(f"PacketCodec: Packet too large: {total_size} bytes (max {PacketCodec.MAX_PACKET_SIZE})")
                offset += 2
                continue

            if offset + total_size > len(buffer):
                break

            if version != PacketCodec.PROTOCOL_VERSION:
                logger.warning(f"PacketCodec: Unsupported protocol version: {version} (expected {PacketCodec.PROTOCOL_VERSION})")
                offset += 2
                continue

            tail_pos = offset + PacketCodec.HEADER_SIZE + json_length + binary_length
            received_crc = struct.unpack('>I', bytes(buffer[tail_pos:tail_pos + 4]))[0]

            crc_start = offset + 2
            crc_end = tail_pos
            expected_crc = PacketCodec.calculate_crc32(bytes(buffer[crc_start:crc_end]))

            if received_crc != expected_crc:
                logger.warning(f"PacketCodec: CRC32 mismatch! received: {received_crc:#010x}, expected: {expected_crc:#010x}")
                offset += 2
                continue

            json_start = offset + PacketCodec.HEADER_SIZE
            json_data = bytes(buffer[json_start:json_start + json_length])
            binary_data = bytes(buffer[json_start + json_length:json_start + json_length + binary_length])

            packets.append((json_data, binary_data))
            offset += total_size

        remaining = bytearray(buffer[offset:])
        return packets, remaining
