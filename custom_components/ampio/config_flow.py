"""Config flow to configure Ampio System."""
from collections import OrderedDict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.mqtt.config_flow import try_connection
from homeassistant.components.mqtt.const import CONF_BROKER
from homeassistant.const import CONF_PASSWORD, CONF_PORT, CONF_USERNAME

DOMAIN = "ampio"
CLIENT_ID = "HomeAssistant-{}".format("12312312")
KEEPALIVE = 600


@config_entries.HANDLERS.register("ampio")
class AmpioFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Ampio config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return await self.async_step_broker()

    async def async_step_broker(self, user_input=None):
        """Confirm the setup."""
        errors = {}

        if user_input is not None:
            can_connect = await self.hass.async_add_executor_job(
                try_connection,
                user_input[CONF_BROKER],
                user_input[CONF_PORT],
                user_input.get(CONF_USERNAME),
                user_input.get(CONF_PASSWORD),
            )

            if can_connect:
                return self.async_create_entry(
                    title=user_input[CONF_BROKER], data=user_input
                )

            errors["base"] = "cannot_connect"

        fields = OrderedDict()
        fields[vol.Required(CONF_BROKER)] = str
        fields[vol.Required(CONF_PORT, default=1883)] = vol.Coerce(int)
        fields[vol.Optional(CONF_USERNAME)] = str
        fields[vol.Optional(CONF_PASSWORD)] = str

        return self.async_show_form(
            step_id="broker", data_schema=vol.Schema(fields), errors=errors
        )
