"""Ampio Sensors."""
import functools
import logging
from typing import Optional

from homeassistant.components import sensor
from homeassistant.const import CONF_DEVICE_CLASS, CONF_ICON, CONF_UNIT_OF_MEASUREMENT
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
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
from .debug_info import log_messages
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)

CONF_EXPIRE_AFTER = "expire_after"
DEFAULT_FORCE_UPDATE = False
DEFAULT_NAME = "Ampio Sensor"


class AmpioSensor(AmpioEntity, RestoreEntity, Entity):
    """Representation of Ampio Sensor."""

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
                self._state = float(payload)
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
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._config.get(CONF_UNIT_OF_MEASUREMENT)

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def icon(self):
        """Return the icon."""
        return self._config.get(CONF_ICON)

    @property
    def device_class(self) -> Optional[str]:
        """Return the device class of the sensor."""
        return self._config.get(CONF_DEVICE_CLASS)


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigType, async_add_entities
):
    """Set up MQTT sensors dynamically through MQTT discovery."""
    entities_to_create = hass.data[DATA_AMPIO][sensor.DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioSensor,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
