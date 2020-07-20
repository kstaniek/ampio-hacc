"""Ampio Switch."""
import functools
import logging

from homeassistant.components import switch
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import discovery, subscription
from .client import async_publish
from .const import (
    CONF_COMMAND_TOPIC,
    CONF_STATE_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    DEFAULT_QOS,
    SIGNAL_ADD_ENTITIES,
)
from .debug_info import log_messages
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)


class AmpioSwitch(AmpioEntity, switch.SwitchEntity):
    """Representation of Ampio Light."""

    def __init__(self, config):
        """Initialize the sensor."""
        AmpioEntity.__init__(self, config)

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
        async_publish(self.hass, self._config[CONF_COMMAND_TOPIC], 0, 0, False)

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""

        async_publish(self.hass, self._config[CONF_COMMAND_TOPIC], 1, 0, False)


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigType, async_add_entities
):
    """Set up MQTT sensors dynamically through MQTT discovery."""
    entities_to_create = hass.data[DATA_AMPIO][switch.DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioSwitch,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
