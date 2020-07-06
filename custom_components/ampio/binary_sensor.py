"""Ampio Sensors."""
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components import binary_sensor, mqtt
from homeassistant.components.binary_sensor import (DEVICE_CLASSES_SCHEMA,
                                                    BinarySensorEntity)
from homeassistant.const import (CONF_DEVICE, CONF_DEVICE_CLASS,
                                 CONF_FORCE_UPDATE, CONF_ICON, CONF_NAME)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import (CONF_UNIQUE_ID, AmpioEntityDeviceInfo, BaseAmpioEntity,
               subscription)
from .const import AMPIO_DISCOVERY_NEW, CONF_STATE_TOPIC, DEFAULT_QOS
from .debug_info import log_messages
from .models import AmpioModuleInfo

_LOGGER = logging.getLogger(__name__)

CONF_EXPIRE_AFTER = "expire_after"
DEFAULT_FORCE_UPDATE = False
DEFAULT_NAME = "Ampio Binary Sensor"

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
        configs = module.configs.get(binary_sensor.DOMAIN)
        entities = [AmpioBinarySensor(config, config_entry) for config in configs]
        async_add_entities(entities)

    async_dispatcher_connect(
        hass,
        AMPIO_DISCOVERY_NEW.format(binary_sensor.DOMAIN, "ampio"),
        async_discover_sensor,
    )


class AmpioBinarySensor(BaseAmpioEntity, AmpioEntityDeviceInfo, BinarySensorEntity):
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

    @property
    def available(self) -> bool:
        return True
