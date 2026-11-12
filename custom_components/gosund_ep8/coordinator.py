"""Polling coordinator for EP8 Relay state."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_TIMEOUT,
    DEVICE_NAME,
    DOMAIN,
)
from .lan_client import LanClient, LanClientError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class Ep8Coordinator(DataUpdateCoordinator[bool]):
    """Periodically query Relay state over a Direct LAN Session."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.client = self._build_client(entry)
        poll = int(entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_DEVICE_ID]}",
            update_interval=timedelta(seconds=poll),
            config_entry=entry,
        )

    @staticmethod
    def _build_client(entry: ConfigEntry) -> LanClient:
        return LanClient(
            entry.data[CONF_HOST],
            entry.data[CONF_DEVICE_ID],
            entry.data[CONF_LOCAL_KEY],
            timeout=DEFAULT_TIMEOUT,
        )

    async def _async_update_data(self) -> bool:
        try:
            return await self.client.async_query_relay()
        except LanClientError as err:
            _LOGGER.warning("%s Polling failed: %s", DEVICE_NAME, err)
            raise UpdateFailed(str(err)) from err

    async def async_set_relay(self, on: bool) -> None:
        """Command Relay; commit state after ACK, then refresh once more."""
        try:
            await self.client.async_set_relay(on)
        except LanClientError as err:
            _LOGGER.warning("%s control failed: %s", DEVICE_NAME, err)
            self.last_update_success = False
            self.async_update_listeners()
            raise
        # ACK/status already matched the command — commit before optional refresh.
        self.async_set_updated_data(on)
        try:
            current = await self.client.async_query_relay()
        except LanClientError as err:
            _LOGGER.warning(
                "%s post-command refresh failed (keeping ACK state): %s",
                DEVICE_NAME,
                err,
            )
            return
        self.async_set_updated_data(current)
