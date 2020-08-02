"""Ampio Sensors."""
import functools
import logging

from homeassistant.components import binary_sensor
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import discovery, subscription
from .const import (
    CONF_STATE_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    DEFAULT_QOS,
    SIGNAL_ADD_ENTITIES,
)
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)

CONF_EXPIRE_AFTER = "expire_after"
DEFAULT_FORCE_UPDATE = False
DEFAULT_NAME = "Ampio Binary Sensor"


class AmpioBinarySensor(AmpioEntity, RestoreEntity, binary_sensor.BinarySensorEntity):
    """Representation of Ampio Sensor."""

    def __init__(self, config):
        """Initialize the light component."""
        AmpioEntity.__init__(self, config)

    async def subscribe_topics(self):
        """(Re)Subscribe to topics."""

        @callback
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

    async def async_added_to_hass(self):
        """Entity added to the hass."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if not last_state:
            return
        self._state = last_state.state

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(
            self.hass, self._sub_state
        )

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def available(self) -> bool:
        return True


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigType, async_add_entities
):
    """Set up MQTT sensors dynamically through MQTT discovery."""
    entities_to_create = hass.data[DATA_AMPIO][binary_sensor.DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioBinarySensor,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
