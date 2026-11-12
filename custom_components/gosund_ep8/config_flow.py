"""Config Flow and Options Flow for Gosund EP8."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DEVICE_NAME,
    DOMAIN,
)
from .lan_client import LanClient, LanClientError

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
        vol.Required(CONF_DEVICE_ID): TextSelector(),
        vol.Required(CONF_LOCAL_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): NumberSelector(
            NumberSelectorConfig(min=5, max=3600, mode=NumberSelectorMode.BOX, step=1)
        ),
    }
)


async def _async_validate(host: str, device_id: str, local_key: str) -> dict[str, str]:
    """Validate fields and require a successful Relay query."""
    errors: dict[str, str] = {}
    if not host.strip():
        errors[CONF_HOST] = "invalid_host"
    if not device_id.strip():
        errors[CONF_DEVICE_ID] = "invalid_device_id"
    if not local_key.strip():
        errors[CONF_LOCAL_KEY] = "invalid_local_key"
    if errors:
        return errors
    if len(local_key.encode("utf-8")) != 16:
        errors[CONF_LOCAL_KEY] = "invalid_local_key"
        return errors
    client = LanClient(host.strip(), device_id.strip(), local_key)
    try:
        await client.async_query_relay()
    except LanClientError:
        errors["base"] = "cannot_connect"
    except ValueError:
        errors[CONF_LOCAL_KEY] = "invalid_local_key"
    return errors


class GosundEp8ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Config Entry create flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect connection settings and verify Relay query."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = str(user_input[CONF_HOST])
            device_id = str(user_input[CONF_DEVICE_ID])
            local_key = str(user_input[CONF_LOCAL_KEY])
            poll = int(user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))
            errors = await _async_validate(host, device_id, local_key)
            if not errors:
                await self.async_set_unique_id(device_id.strip())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=DEVICE_NAME,
                    data={
                        CONF_HOST: host.strip(),
                        CONF_DEVICE_ID: device_id.strip(),
                        CONF_LOCAL_KEY: local_key,
                        CONF_POLL_INTERVAL: poll,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> GosundEp8OptionsFlow:
        """Return the Options Flow handler."""
        return GosundEp8OptionsFlow(config_entry)


class GosundEp8OptionsFlow(config_entries.OptionsFlow):
    """Allow updating host, device id, Local Key, and poll interval."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage Integration options."""
        errors: dict[str, str] = {}
        current = self._config_entry.data

        if user_input is not None:
            host = str(user_input[CONF_HOST])
            device_id = str(user_input[CONF_DEVICE_ID])
            local_key = str(user_input[CONF_LOCAL_KEY])
            poll = int(user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))
            errors = await _async_validate(host, device_id, local_key)
            if not errors:
                data = {
                    CONF_HOST: host.strip(),
                    CONF_DEVICE_ID: device_id.strip(),
                    CONF_LOCAL_KEY: local_key,
                    CONF_POLL_INTERVAL: poll,
                }
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=data, options=self._config_entry.options
                )
                return self.async_create_entry(title="", data={})

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current[CONF_HOST]): TextSelector(),
                vol.Required(
                    CONF_DEVICE_ID, default=current[CONF_DEVICE_ID]
                ): TextSelector(),
                vol.Required(
                    CONF_LOCAL_KEY, default=current[CONF_LOCAL_KEY]
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=current.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5, max=3600, mode=NumberSelectorMode.BOX, step=1
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
