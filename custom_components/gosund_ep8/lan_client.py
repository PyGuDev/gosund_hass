"""Minimal Tuya LAN 3.3 client for EP8 Relay (DPS 1) over a Direct LAN Session."""

from __future__ import annotations

import asyncio
import json
import logging
import struct
import zlib
from collections.abc import Awaitable, Callable
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .const import DEFAULT_PORT, DEFAULT_TIMEOUT, RELAY_DPS

_LOGGER = logging.getLogger(__name__)

PREFIX = 0x000055AA
SUFFIX = 0x0000AA55
CMD_STATUS = 0x08
CMD_CONTROL_NEW = 0x0D
CMD_DP_QUERY_NEW = 0x10
VERSION_HEADER = b"3.3" + b"\x00" * 12
NO_PROTOCOL_HEADER_CMDS = {CMD_DP_QUERY_NEW}

ExchangeFn = Callable[[bytes], Awaitable[bytes]]


class LanClientError(Exception):
    """Raised when a Direct LAN Session query/control fails."""


class LanClient:
    """Async LAN Client: one short-lived TCP session per query or control."""

    def __init__(
        self,
        host: str,
        device_id: str,
        local_key: str,
        *,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        exchange: ExchangeFn | None = None,
    ) -> None:
        key = local_key.encode("utf-8")
        if len(key) != 16:
            raise ValueError("Local Key must encode to exactly 16 bytes")
        self._host = host
        self._device_id = device_id
        self._key = key
        self._port = port
        self._timeout = timeout
        self._exchange = exchange
        self._seq = 0

    async def async_query_relay(self) -> bool:
        """Return whether the Relay (DPS 1) is on."""
        self._seq += 1
        request = self._build_frame(self._seq, CMD_DP_QUERY_NEW, b"{}")
        try:
            raw = await self._session_exchange(request)
        except (OSError, TimeoutError, asyncio.TimeoutError) as err:
            _LOGGER.warning(
                "Direct LAN Session query failed for %s: %s", self._host, err
            )
            raise LanClientError(f"query Relay failed: {err}") from err
        try:
            dps = self._parse_dps_from_response(raw)
            return bool(dps[RELAY_DPS])
        except (KeyError, LanClientError, ValueError, json.JSONDecodeError) as err:
            _LOGGER.warning(
                "Direct LAN Session query decode failed for %s: %s", self._host, err
            )
            raise LanClientError(f"query Relay decode failed: {err}") from err

    async def async_set_relay(self, on: bool) -> None:
        """Set Relay on/off; succeed only after status/ACK matches the command."""
        self._seq += 1
        payload = json.dumps({"dps": {RELAY_DPS: on}}, separators=(",", ":")).encode()
        request = self._build_frame(self._seq, CMD_CONTROL_NEW, payload)
        try:
            raw = await self._session_exchange(request)
        except (OSError, TimeoutError, asyncio.TimeoutError) as err:
            _LOGGER.warning(
                "Direct LAN Session control failed for %s: %s", self._host, err
            )
            raise LanClientError(f"set Relay failed: {err}") from err
        try:
            self._require_set_ack(raw, on=on)
        except (KeyError, LanClientError, ValueError, json.JSONDecodeError) as err:
            _LOGGER.warning(
                "Direct LAN Session control ACK failed for %s: %s", self._host, err
            )
            raise LanClientError(f"set Relay ACK failed: {err}") from err

    async def _session_exchange(self, request: bytes) -> bytes:
        if self._exchange is not None:
            return await self._exchange(request)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout,
            )
        except (OSError, TimeoutError, asyncio.TimeoutError) as err:
            _LOGGER.warning(
                "Direct LAN Session connect failed to %s:%s: %s",
                self._host,
                self._port,
                err,
            )
            raise
        try:
            writer.write(request)
            await writer.drain()
            chunks: list[bytes] = []
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        reader.read(4096), timeout=self._timeout
                    )
                except (TimeoutError, asyncio.TimeoutError):
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                joined = b"".join(chunks)
                if self._has_complete_exchange(joined):
                    return joined
            joined = b"".join(chunks)
            if not joined:
                raise TimeoutError("no response from EP8")
            return joined
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    def _build_frame(self, seq: int, command: int, plaintext: bytes) -> bytes:
        encrypted = self._encrypt(plaintext)
        payload = encrypted
        if command not in NO_PROTOCOL_HEADER_CMDS:
            payload = VERSION_HEADER + encrypted
        length = len(payload) + 8
        header = struct.pack("!IIII", PREFIX, seq, command, length) + payload
        crc = zlib.crc32(header) & 0xFFFFFFFF
        return header + struct.pack("!II", crc, SUFFIX)

    def _encrypt(self, plaintext: bytes) -> bytes:
        pad = 16 - (len(plaintext) % 16)
        data = plaintext + bytes([pad]) * pad
        encryptor = Cipher(algorithms.AES(self._key), modes.ECB()).encryptor()
        return encryptor.update(data) + encryptor.finalize()

    def _decrypt(self, ciphertext: bytes) -> bytes:
        if not ciphertext or len(ciphertext) % 16 != 0:
            raise LanClientError("ciphertext length is invalid")
        decryptor = Cipher(algorithms.AES(self._key), modes.ECB()).decryptor()
        data = decryptor.update(ciphertext) + decryptor.finalize()
        pad = data[-1]
        if pad < 1 or pad > 16 or data[-pad:] != bytes([pad]) * pad:
            raise LanClientError("invalid PKCS#7 padding (Local Key may be wrong)")
        return data[:-pad]

    def _parse_frames(self, raw: bytes) -> list[tuple[int, int, bytes, int | None]]:
        frames: list[tuple[int, int, bytes, int | None]] = []
        cursor = 0
        while cursor + 16 <= len(raw):
            prefix, seq, command, length = struct.unpack_from("!IIII", raw, cursor)
            if prefix != PREFIX:
                cursor += 1
                continue
            end = cursor + 16 + length
            if end > len(raw):
                break
            frame = raw[cursor:end]
            stored_crc = struct.unpack_from("!I", frame, len(frame) - 8)[0]
            if stored_crc != (zlib.crc32(frame[:-8]) & 0xFFFFFFFF):
                raise LanClientError("CRC32 mismatch")
            if struct.unpack_from("!I", frame, len(frame) - 4)[0] != SUFFIX:
                raise LanClientError("bad frame suffix")
            body = frame[16:-8]
            retcode: int | None = None
            # Device responses include a 4-byte retcode before payload.
            if len(body) >= 4 and command in {
                CMD_STATUS,
                CMD_CONTROL_NEW,
                CMD_DP_QUERY_NEW,
            }:
                # Device answers always carry a 4-byte retcode before payload.
                retcode = struct.unpack_from("!I", body, 0)[0]
                body = body[4:]
            frames.append((seq, command, body, retcode))
            cursor = end
        if not frames:
            raise LanClientError("no Tuya frames in response")
        return frames

    def _payload_to_json(self, command: int, body: bytes) -> dict[str, Any] | None:
        if not body:
            return None
        data = body
        if data.startswith(b"3.3") and len(data) >= 15:
            data = data[15:]
        if not data:
            return None
        plaintext = self._decrypt(data)
        if not plaintext:
            return None
        return json.loads(plaintext.decode("utf-8"))

    def _parse_dps_from_response(self, raw: bytes) -> dict[str, Any]:
        for _seq, command, body, retcode in self._parse_frames(raw):
            if retcode not in (None, 0):
                raise LanClientError(f"device retcode {retcode}")
            parsed = self._payload_to_json(command, body)
            if parsed and "dps" in parsed:
                return parsed["dps"]
        raise LanClientError("response missing dps")

    def _require_set_ack(self, raw: bytes, *, on: bool) -> None:
        saw_matching_status = False
        for _seq, command, body, retcode in self._parse_frames(raw):
            if retcode not in (None, 0):
                raise LanClientError(f"device retcode {retcode}")
            parsed = self._payload_to_json(command, body)
            if parsed and "dps" in parsed and RELAY_DPS in parsed["dps"]:
                if bool(parsed["dps"][RELAY_DPS]) == on:
                    saw_matching_status = True
                else:
                    raise LanClientError("status DPS 1 does not match command")
        if not saw_matching_status:
            raise LanClientError("ACK/status missing matching Relay state")

    @staticmethod
    def _has_complete_exchange(raw: bytes) -> bool:
        """True when at least one full frame is present (query) or status+ack."""
        cursor = 0
        count = 0
        commands: list[int] = []
        while cursor + 16 <= len(raw):
            prefix, _seq, command, length = struct.unpack_from("!IIII", raw, cursor)
            if prefix != PREFIX:
                cursor += 1
                continue
            end = cursor + 16 + length
            if end > len(raw):
                return False
            count += 1
            commands.append(command)
            cursor = end
        if count == 0:
            return False
        if CMD_CONTROL_NEW in commands and CMD_STATUS in commands:
            return True
        if count >= 1 and CMD_DP_QUERY_NEW in commands:
            return True
        if count >= 1 and CMD_CONTROL_NEW in commands and CMD_STATUS not in commands:
            # Wait briefly for status; caller may still accept ACK-only path later.
            return count >= 2
        return count >= 1
