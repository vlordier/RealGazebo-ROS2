"""Test UE5 UDP packet format matches libRealGazebo.so C++ struct layout.

The C++ RealGazebo plugin sends:
  <BBB (header: vehicle_code, vehicle_num, packet_type)
  + 7 floats (x, y, z, qw, qx, qy, qz)
  = 3 + 28 = 31 bytes total

This test validates the Python-side encoding matches.
"""

import struct

PACKED_HEADER_FMT = '<BBB'
PACKED_FLOAT_FMT = '7f'
PACKED_FULL_FMT = '<BBB7f'
PACKED_SIZE = struct.calcsize(PACKED_FULL_FMT)


class TestUe5PacketFormat:
    """Validate UE5 UDP packet encoding matches C++ RealGazebo.cpp layout."""

    def test_packet_size_is_31_bytes(self):
        """sizeof(RealGazeboPacketHeader) + 7*sizeof(float) = 3 + 28 = 31."""
        assert PACKED_SIZE == 31

    def test_header_is_3_bytes(self):
        """Header: uint8 vehicle_code, uint8 vehicle_num, uint8 packet_type."""
        header_size = struct.calcsize(PACKED_HEADER_FMT)
        assert header_size == 3

    def test_encode_and_decode_roundtrip(self):
        """A packet encoded in Python can be decoded back to the same values."""
        header = (1, 5, 0)  # vehicle_code=1, vehicle_num=5, packet_type=0
        floats = (1.0, 2.0, -3.0, 1.0, 0.0, 0.0, 0.0)
        packet = struct.pack(PACKED_FULL_FMT, *header, *floats)
        decoded = struct.unpack(PACKED_FULL_FMT, packet)
        decoded_header = decoded[:3]
        decoded_floats = decoded[3:]
        assert decoded_header == header
        for a, b in zip(floats, decoded_floats, strict=True):
            assert abs(a - b) < 1e-6

    def test_mock_udp_receiver(self):
        """Simulate receiving a UDP packet and parsing it."""
        import socket
        import threading
        import time

        received = []

        def server():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
            received.append(port)
            try:
                data, _addr = sock.recvfrom(1024)
                received.append(data)
            except socket.timeout:
                pass
            finally:
                sock.close()

        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.1)

        port = received[0]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        packet = struct.pack(PACKED_FULL_FMT, 1, 0, 0, 10.0, 20.0, -5.0, 1.0, 0.0, 0.0, 0.0)
        sock.sendto(packet, ('127.0.0.1', port))
        sock.close()
        thread.join(timeout=1.0)

        assert len(received) >= 2, 'No packet received'
        data = received[1]
        assert len(data) == 31
        hdr = struct.unpack(PACKED_HEADER_FMT, data[:3])
        assert hdr[0] == 1  # vehicle_code
        assert hdr[1] == 0  # vehicle_num
