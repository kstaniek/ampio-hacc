"""Ampio Switch."""
import logging

from homeassistant.core import callback
from homeassistant.components import switch
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import CONF_DEVICE


from .models import AmpioModuleInfo
from .const import (
    AMPIO_DISCOVERY_NEW,
    DOMAIN,
    CONF_STATE_TOPIC,
    CONF_COMMAND_TOPIC,
    DEFAULT_QOS,
)
from . import AmpioEntityDeviceInfo, subscription, BaseAmpioEntity
from .debug_info import log_messages

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigType, async_add_entities
):
    """Set up MQTT sensors dynamically through MQTT discovery."""

    async def async_discover_switch(module: AmpioModuleInfo):
        """Discover and add a discovered MQTT sensor."""
        configs = module.configs.get(switch.DOMAIN)
        entities = [AmpioSwitch(config, config_entry) for config in configs]
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, AMPIO_DISCOVERY_NEW.format(switch.DOMAIN, "ampio"), async_discover_switch
    )


class AmpioSwitch(BaseAmpioEntity, AmpioEntityDeviceInfo, switch.SwitchEntity):
    """Representation of Ampio Light."""

    def __init__(self, config, config_entry):
        """Initialize the sensor."""
        BaseAmpioEntity.__init__(self, config, config_entry)

        device_config = config.get(CONF_DEVICE)
        AmpioEntityDeviceInfo.__init__(self, device_config, config_entry)


    async def subscribe_topics(self):
        """(Re)Subscribe to topics."""

        @callback
        @log_messages(self.hass, self.entity_id)
        def state_message_received(msg):
            """Handler new MQTT message."""
            payload = msg.payload
            try:
                self._state = bool(int(payload))
            except ValueError:
                self._state = None

            self.async_write_ha_state()

        self._sub_state = await subscription.async_subscribe_topics(
            self.hass,
            self._sub_state,
            {
                "state_topic": {
                    "topic": self._config[CONF_STATE_TOPIC],
                    "msg_callback": state_message_received,
                    "qos": DEFAULT_QOS,
                }
            },
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(
            self.hass, self._sub_state
        )

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self.hass.data[DOMAIN].async_publish(
            self._config[CONF_COMMAND_TOPIC], 0, 0, False
        )

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""

        await self.hass.data[DOMAIN].async_publish(
            self._config[CONF_COMMAND_TOPIC], 1, 0, False
        )
