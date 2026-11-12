"""Relay switch entity for Gosund EP8."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DEVICE_NAME, DOMAIN
from .coordinator import Ep8Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Relay switch from a Config Entry."""
    coordinator: Ep8Coordinator = entry.runtime_data
    async_add_entities([Ep8RelaySwitch(coordinator, entry)])


class Ep8RelaySwitch(CoordinatorEntity[Ep8Coordinator], SwitchEntity):
    """Switch representing the EP8 Relay (DPS 1)."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: Ep8Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{device_id}_relay"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=DEVICE_NAME,
            manufacturer="Gosund",
            model="EP8",
        )

    @property
    def is_on(self) -> bool | None:
        """Return Relay state from the last successful Polling/command."""
        if self.coordinator.data is None:
            return None
        return bool(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the Relay on and wait for device ACK/status."""
        await self.coordinator.async_set_relay(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the Relay off and wait for device ACK/status."""
        await self.coordinator.async_set_relay(False)
