"""Ampio Sensors."""

import logging
from typing import Optional

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components import mqtt, sensor
from homeassistant.components.sensor import DEVICE_CLASSES_SCHEMA
from homeassistant.const import (CONF_DEVICE, CONF_DEVICE_CLASS,
                                 CONF_FORCE_UPDATE, CONF_ICON, CONF_NAME,
                                 CONF_UNIT_OF_MEASUREMENT)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import (CONF_UNIQUE_ID, AmpioEntityDeviceInfo, BaseAmpioEntity,
               subscription)
from .const import AMPIO_DISCOVERY_NEW, CONF_STATE_TOPIC, DEFAULT_QOS
from .debug_info import log_messages
from .models import AmpioModuleInfo

_LOGGER = logging.getLogger(__name__)

CONF_EXPIRE_AFTER = "expire_after"
DEFAULT_FORCE_UPDATE = False
DEFAULT_NAME = "Ampio Sensor"

PLATFORM_SCHEMA = (
    mqtt.MQTT_RO_PLATFORM_SCHEMA.extend(
        {
            vol.Optional(CONF_DEVICE): mqtt.MQTT_ENTITY_DEVICE_INFO_SCHEMA,
            vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
            vol.Optional(CONF_EXPIRE_AFTER): cv.positive_int,
            vol.Optional(CONF_FORCE_UPDATE, default=DEFAULT_FORCE_UPDATE): cv.boolean,
            vol.Optional(CONF_ICON): cv.icon,
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
            vol.Optional(CONF_UNIQUE_ID): cv.string,
            vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
        }
    )
    .extend(mqtt.MQTT_AVAILABILITY_SCHEMA.schema)
    .extend(mqtt.MQTT_JSON_ATTRS_SCHEMA.schema)
)


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigType, async_add_entities
):
    """Set up MQTT sensors dynamically through MQTT discovery."""

    async def async_discover_sensor(module: AmpioModuleInfo):
        """Discover and add a discovered MQTT sensor."""
        configs = module.configs.get(sensor.DOMAIN)
        entities = [AmpioSensor(config, config_entry) for config in configs]
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, AMPIO_DISCOVERY_NEW.format(sensor.DOMAIN, "ampio"), async_discover_sensor
    )


class AmpioSensor(BaseAmpioEntity, AmpioEntityDeviceInfo, Entity):
    """Representation of Ampio Sensor."""

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
