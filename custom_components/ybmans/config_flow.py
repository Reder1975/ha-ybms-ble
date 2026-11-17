"""Config flow for yBMS BLE integration."""
import bleak
from bleak_retry_connector import establish_connection
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import DOMAIN, SERVICE_UUID

DEFAULT_NAME = "yBMS"


class YBMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle yBMS config flow."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, address, connectable=True
            )
            if not ble_device:
                errors["base"] = "cannot_connect"
            else:
                try:
                    client = await establish_connection(
                        bleak.BleakClient,
                        ble_device,
                        ble_device.name or DEFAULT_NAME,
                        max_attempts=2,
                    )
                    await client.disconnect()
                    return self.async_create_entry(
                        title=user_input.get(CONF_NAME, DEFAULT_NAME),
                        data={CONF_ADDRESS: address},
                    )
                except Exception:
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
            errors=errors,
        )

    async_step_import = async_step_user

    async def async_step_bluetooth(self, discovery_info):
        """Handle discovery by Bluetooth."""
        address = discovery_info.address.upper()
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, address, connectable=True
        )
        if not ble_device:
            return self.async_abort(reason="cannot_connect")

        try:
            client = await establish_connection(
                bleak.BleakClient,
                ble_device,
                ble_device.name or DEFAULT_NAME,
                max_attempts=2,
            )
            service = client.services.get_service(SERVICE_UUID)
            await client.disconnect()

            if service is None:
                return self.async_abort(reason="not_ybms")

            return self.async_create_entry(
                title=f"yBMS ({address})",
                data={CONF_ADDRESS: address},
            )
        except Exception:
            return self.async_abort(reason="cannot_connect")
