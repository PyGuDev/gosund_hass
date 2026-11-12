#!/usr/bin/env python3
"""Extract Tuya 0x55AA LAN frames from a raw-IP PCAP capture.

The script uses only the Python standard library.  If a 16-byte Tuya local key
is supplied, it delegates AES-128-ECB decryption to the local OpenSSL binary.
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import struct
import subprocess
import zlib
from dataclasses import dataclass
from pathlib import Path


TUYA_PREFIX = b"\x00\x00\x55\xaa"
TUYA_SUFFIX = b"\x00\x00\xaa\x55"

COMMANDS = {
    0x07: "CONTROL",
    0x08: "STATUS",
    0x09: "HEART_BEAT",
    0x0A: "DP_QUERY",
    0x0D: "CONTROL_NEW",
    0x10: "DP_QUERY_NEW",
}


@dataclass(frozen=True)
class Packet:
    timestamp: dt.datetime
    source: str
    destination: str
    source_port: int
    destination_port: int
    payload: bytes


def read_pcap(path: Path) -> list[tuple[dt.datetime, bytes]]:
    data = path.read_bytes()
    if len(data) < 24:
        raise ValueError("PCAP file is shorter than its global header")

    magic = data[:4]
    formats = {
        b"\xd4\xc3\xb2\xa1": ("<", 1_000_000),
        b"\xa1\xb2\xc3\xd4": (">", 1_000_000),
        b"\x4d\x3c\xb2\xa1": ("<", 1_000_000_000),
        b"\xa1\xb2\x3c\x4d": (">", 1_000_000_000),
    }
    if magic not in formats:
        raise ValueError("Unsupported capture format (expected classic PCAP)")
    endian, fraction_scale = formats[magic]

    _, _, _, _, _, link_type = struct.unpack_from(f"{endian}HHiiii", data, 4)
    if link_type != 101:
        raise ValueError(f"Unsupported link type {link_type}; expected raw IPv4 (101)")

    packets: list[tuple[dt.datetime, bytes]] = []
    offset = 24
    while offset + 16 <= len(data):
        seconds, fraction, captured_length, _ = struct.unpack_from(
            f"{endian}IIII", data, offset
        )
        offset += 16
        raw = data[offset : offset + captured_length]
        offset += captured_length
        timestamp = dt.datetime.fromtimestamp(
            seconds + fraction / fraction_scale, tz=dt.timezone.utc
        ).astimezone()
        packets.append((timestamp, raw))
    return packets


def parse_tcp(timestamp: dt.datetime, raw: bytes) -> Packet | None:
    if len(raw) < 40 or raw[0] >> 4 != 4 or raw[9] != 6:
        return None
    ip_header_length = (raw[0] & 0x0F) * 4
    if len(raw) < ip_header_length + 20:
        return None
    source = str(ipaddress.ip_address(raw[12:16]))
    destination = str(ipaddress.ip_address(raw[16:20]))
    source_port, destination_port = struct.unpack_from("!HH", raw, ip_header_length)
    tcp_header_length = (raw[ip_header_length + 12] >> 4) * 4
    payload_offset = ip_header_length + tcp_header_length
    return Packet(
        timestamp,
        source,
        destination,
        source_port,
        destination_port,
        raw[payload_offset:],
    )


def unpad_pkcs7(data: bytes) -> bytes:
    if not data:
        return data
    padding = data[-1]
    if padding < 1 or padding > 16 or data[-padding:] != bytes([padding]) * padding:
        raise ValueError("invalid PKCS#7 padding (the local key may be wrong)")
    return data[:-padding]


def decrypt_aes_ecb(ciphertext: bytes, local_key: str) -> bytes:
    key = local_key.encode("utf-8")
    if len(key) != 16:
        raise ValueError("Tuya local_key must encode to exactly 16 bytes")
    process = subprocess.run(
        [
            "openssl",
            "enc",
            "-aes-128-ecb",
            "-d",
            "-nopad",
            "-K",
            key.hex(),
        ],
        input=ciphertext,
        capture_output=True,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.decode("utf-8", errors="replace").strip())
    return unpad_pkcs7(process.stdout)


def payload_ciphertext(frame: bytes, from_device: bool) -> bytes:
    body = frame[16:-8]
    if from_device and len(body) >= 4:
        body = body[4:]  # device response return code
    if body.startswith(b"3.3\x00") and len(body) >= 15:
        body = body[15:]
    return body if body and len(body) % 16 == 0 else b""


def extract_frames(packet: Packet) -> list[bytes]:
    frames: list[bytes] = []
    cursor = 0
    while True:
        start = packet.payload.find(TUYA_PREFIX, cursor)
        if start < 0 or start + 16 > len(packet.payload):
            break
        body_length = struct.unpack_from("!I", packet.payload, start + 12)[0]
        end = start + 16 + body_length
        if end > len(packet.payload):
            break
        frames.append(packet.payload[start:end])
        cursor = end
    return frames


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pcap", type=Path)
    parser.add_argument("--local-key", help="16-byte Tuya local_key for decryption")
    args = parser.parse_args()

    found = 0
    for timestamp, raw in read_pcap(args.pcap):
        packet = parse_tcp(timestamp, raw)
        if packet is None or not packet.payload:
            continue
        for frame in extract_frames(packet):
            found += 1
            sequence, command, body_length = struct.unpack_from("!III", frame, 4)
            stored_crc = struct.unpack_from("!I", frame, len(frame) - 8)[0]
            computed_crc = zlib.crc32(frame[:-8]) & 0xFFFFFFFF
            from_device = packet.source_port == 6668
            direction = "device -> app" if from_device else "app -> device"
            command_name = COMMANDS.get(command, "UNKNOWN")
            print(
                f"{timestamp.isoformat()}  {direction:13}  "
                f"seq=0x{sequence:04x} cmd=0x{command:02x} ({command_name}) "
                f"len={len(frame)} crc={'OK' if stored_crc == computed_crc else 'BAD'}"
            )
            print(f"  {packet.source}:{packet.source_port} -> "
                  f"{packet.destination}:{packet.destination_port}")

            ciphertext = payload_ciphertext(frame, from_device)
            if ciphertext:
                print(f"  AES-ECB ciphertext ({len(ciphertext)} bytes): {ciphertext.hex()}")
            if args.local_key and ciphertext:
                try:
                    plaintext = decrypt_aes_ecb(ciphertext, args.local_key)
                    decoded = plaintext.decode("utf-8")
                    try:
                        decoded = json.dumps(
                            json.loads(decoded), ensure_ascii=False, indent=2
                        )
                    except json.JSONDecodeError:
                        pass
                    print(f"  plaintext: {decoded}")
                except (ValueError, RuntimeError, UnicodeDecodeError) as error:
                    print(f"  decryption failed: {error}")
    if not found:
        print("No complete Tuya 0x55AA frames found")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
