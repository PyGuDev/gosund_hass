"""LAN Client seam: query Relay state."""

from __future__ import annotations

import pytest

from custom_components.gosund_ep8.lan_client import LanClient, LanClientError
from tests.fixtures_lan import (
    BAD_DECRYPT_RESP_HEX,
    QUERY_REQ_HEX,
    QUERY_RESP_OFF_HEX,
    QUERY_RESP_ON_HEX,
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
async def test_query_relay_reports_on_from_known_response() -> None:
    exchange = _FakeExchange(bytes.fromhex(QUERY_RESP_ON_HEX))
    client = LanClient(
        TEST_HOST,
        TEST_DEVICE_ID,
        TEST_LOCAL_KEY,
        exchange=exchange,
    )

    assert await client.async_query_relay() is True
    assert exchange.sent[0] == bytes.fromhex(QUERY_REQ_HEX)


@pytest.mark.asyncio
async def test_query_relay_reports_off_from_known_response() -> None:
    exchange = _FakeExchange(bytes.fromhex(QUERY_RESP_OFF_HEX))
    client = LanClient(
        TEST_HOST,
        TEST_DEVICE_ID,
        TEST_LOCAL_KEY,
        exchange=exchange,
    )

    assert await client.async_query_relay() is False


@pytest.mark.asyncio
async def test_query_relay_surfaces_bad_decrypt_as_error() -> None:
    exchange = _FakeExchange(bytes.fromhex(BAD_DECRYPT_RESP_HEX))
    client = LanClient(
        TEST_HOST,
        TEST_DEVICE_ID,
        TEST_LOCAL_KEY,
        exchange=exchange,
    )

    with pytest.raises(LanClientError):
        await client.async_query_relay()


@pytest.mark.asyncio
async def test_query_relay_surfaces_timeout_as_error() -> None:
    async def boom(_: bytes) -> bytes:
        raise TimeoutError("timed out")

    client = LanClient(
        TEST_HOST,
        TEST_DEVICE_ID,
        TEST_LOCAL_KEY,
        exchange=boom,
    )

    with pytest.raises(LanClientError):
        await client.async_query_relay()
