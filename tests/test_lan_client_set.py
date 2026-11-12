"""LAN Client seam: set Relay with ACK/status."""

from __future__ import annotations

import pytest

from custom_components.gosund_ep8.lan_client import LanClient, LanClientError
from tests.fixtures_lan import (
    ACK_ONLY_HEX,
    CTRL_OFF_REQ_HEX,
    CTRL_ON_REQ_HEX,
    STATUS_OFF_ACK_HEX,
    STATUS_ON_ACK_HEX,
    TEST_DEVICE_ID,
    TEST_HOST,
    TEST_LOCAL_KEY,
)


class _FakeExchange:
    def __init__(self, response: bytes) -> None:
        self.response = response
        self.sent: list[bytes] = []

    async def __call__(self, request: bytes) -> bytes:
        self.sent.append(request)
        return self.response


@pytest.mark.asyncio
async def test_set_relay_off_sends_control_and_accepts_matching_status() -> None:
    exchange = _FakeExchange(bytes.fromhex(STATUS_OFF_ACK_HEX))
    client = LanClient(
        TEST_HOST,
        TEST_DEVICE_ID,
        TEST_LOCAL_KEY,
        exchange=exchange,
    )

    await client.async_set_relay(False)

    assert exchange.sent[0] == bytes.fromhex(CTRL_OFF_REQ_HEX)


@pytest.mark.asyncio
async def test_set_relay_on_sends_control_and_accepts_matching_status() -> None:
    exchange = _FakeExchange(bytes.fromhex(STATUS_ON_ACK_HEX))
    client = LanClient(
        TEST_HOST,
        TEST_DEVICE_ID,
        TEST_LOCAL_KEY,
        exchange=exchange,
    )

    await client.async_set_relay(True)

    assert exchange.sent[0] == bytes.fromhex(CTRL_ON_REQ_HEX)


@pytest.mark.asyncio
async def test_set_relay_rejects_ack_without_matching_status() -> None:
    exchange = _FakeExchange(bytes.fromhex(ACK_ONLY_HEX))
    client = LanClient(
        TEST_HOST,
        TEST_DEVICE_ID,
        TEST_LOCAL_KEY,
        exchange=exchange,
    )

    with pytest.raises(LanClientError):
        await client.async_set_relay(True)


@pytest.mark.asyncio
async def test_set_relay_surfaces_timeout_as_error() -> None:
    async def boom(_: bytes) -> bytes:
        raise TimeoutError("timed out")

    client = LanClient(
        TEST_HOST,
        TEST_DEVICE_ID,
        TEST_LOCAL_KEY,
        exchange=boom,
    )

    with pytest.raises(LanClientError):
        await client.async_set_relay(False)
