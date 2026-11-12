"""Optional LAN Client checks against real capture frames (needs Local Key)."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.gosund_ep8.lan_client import LanClient, LanClientError
from tests.fixtures_lan import TEST_DEVICE_ID, TEST_HOST, TEST_LOCAL_KEY

# Independent known-good from PCAPdroid capture (device -> app DP_QUERY_NEW).
# Plaintext expectation is recorded in REVERSE_ENGINEERING.md / LOCAL_CONTROL.md.
# Host/device id below are synthetic; decryption uses Local Key from .secrets.
CAPTURE_QUERY_RESP_ON_HEX = (
    "000055aa0000060b000000100000006c00000000"
    "b73ceba9fe4a9ab56ced9609fc14abde"
    "891c81657d3182e9787819abcae23438"
    "11a3a7f83bfbd8ad0f6ec5360cf16c4a"
    "26f735331837ab66c13e2d72510e8fe2"
    "25654240c65f43cfd48f66f4f3c4856e"
    "f681967e3c04b92366fb038a35512787"
    "1615429d0000aa55"
)

# CONTROL_NEW OFF status (device -> app) from the same capture.
CAPTURE_STATUS_OFF_HEX = (
    "000055aa00000000000000080000004b00000000"
    "332e33000000000000241200000001"
    "3391d18780b76360c42a62e9a891aa37"
    "bf6979efb569d719d0066d930cd77a6c"
    "a72b9544940fe99f0f21a6c6e0bdfabd"
    "7c61ea5c0000aa55"
)
CAPTURE_ACK_OFF_HEX = "000055aa0000060c0000000d0000000c000000008fc508420000aa55"


def _load_local_key() -> str | None:
    path = Path(__file__).resolve().parents[1] / ".secrets" / "ep8.env"
    if not path.is_file():
        return None
    for line in path.read_text().splitlines():
        if line.startswith("LOCAL_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


@pytest.fixture
def local_key() -> str:
    key = _load_local_key()
    if not key:
        pytest.skip("Local Key not available in .secrets/ep8.env")
    return key


class _FakeExchange:
    def __init__(self, response: bytes) -> None:
        self.response = response
        self.sent: list[bytes] = []

    async def __call__(self, request: bytes) -> bytes:
        self.sent.append(request)
        return self.response


@pytest.mark.asyncio
async def test_query_relay_decodes_capture_response(local_key: str) -> None:
    exchange = _FakeExchange(bytes.fromhex(CAPTURE_QUERY_RESP_ON_HEX))
    client = LanClient(
        TEST_HOST,
        TEST_DEVICE_ID,
        local_key,
        exchange=exchange,
    )

    assert await client.async_query_relay() is True


@pytest.mark.asyncio
async def test_set_relay_accepts_capture_status_and_ack(local_key: str) -> None:
    exchange = _FakeExchange(
        bytes.fromhex(CAPTURE_STATUS_OFF_HEX + CAPTURE_ACK_OFF_HEX)
    )
    client = LanClient(
        TEST_HOST,
        TEST_DEVICE_ID,
        local_key,
        exchange=exchange,
    )

    await client.async_set_relay(False)


@pytest.mark.asyncio
async def test_query_relay_surfaces_connection_refused() -> None:
    async def boom(_: bytes) -> bytes:
        raise ConnectionRefusedError("connection refused")

    client = LanClient(
        "127.0.0.1",
        TEST_DEVICE_ID,
        TEST_LOCAL_KEY,
        exchange=boom,
    )

    with pytest.raises(LanClientError):
        await client.async_query_relay()
