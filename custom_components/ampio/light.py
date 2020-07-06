"""Ampio Lights."""
import logging

from homeassistant.core import callback
from homeassistant.components import light
from homeassistant.components.light import SUPPORT_BRIGHTNESS, ATTR_BRIGHTNESS
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import (
    CONF_DEVICE,
)

from .models import AmpioModuleInfo
from .const import (
    AMPIO_DISCOVERY_NEW,
    DOMAIN,
    CONF_STATE_TOPIC,
    CONF_COMMAND_TOPIC,
    CONF_BRIGHTNESS_COMMAND_TOPIC,
    CONF_BRIGHTNESS_STATE_TOPIC,
    DEFAULT_QOS,
)
from . import AmpioEntityDeviceInfo, subscription, BaseAmpioEntity
from .debug_info import log_messages

PLATFORM_SCHEMA = {}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up MQTT sensors dynamically through MQTT discovery."""

    async def async_discover_light(module: AmpioModuleInfo):
        """Discover and add a discovered MQTT sensor."""
        configs = module.configs.get(light.DOMAIN)
        entities = [AmpioLight(config, config_entry) for config in configs]
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, AMPIO_DISCOVERY_NEW.format(light.DOMAIN, "ampio"), async_discover_light
    )


class AmpioLight(BaseAmpioEntity, AmpioEntityDeviceInfo, light.LightEntity):
    """Representation of Ampio Light."""

    def __init__(self, config, config_entry):
        """Initialize the sensor."""
        BaseAmpioEntity.__init__(self, config, config_entry)

        self._brightness = None

        device_config = config.get(CONF_DEVICE)
        AmpioEntityDeviceInfo.__init__(self, device_config, config_entry)

    async def subscribe_topics(self):
        """(Re)Subscribe to topics."""
        topics = {}

        @callback
        @log_messages(self.hass, self.entity_id)
        def state_received(msg):
            """Handler new MQTT message."""
            payload = msg.payload
            try:
                self._state = bool(int(payload))
            except ValueError:
                self._state = None

            self.async_write_ha_state()

        if self._config.get(CONF_STATE_TOPIC) is not None:
            topics[CONF_STATE_TOPIC] = {
                "topic": self._config[CONF_STATE_TOPIC],
                "msg_callback": state_received,
                "qos": DEFAULT_QOS,
            }

        @callback
        @log_messages(self.hass, self.entity_id)
        def brightness_received(msg):
            """Handler new MQTT message."""
            payload = msg.payload
            try:
                brightness = int(payload)
            except ValueError:
                return

            if brightness > 0:
                self._brightness = brightness

            self.async_write_ha_state()

        if self._config.get(CONF_BRIGHTNESS_STATE_TOPIC) is not None:
            topics[CONF_BRIGHTNESS_STATE_TOPIC] = {
                "topic": self._config[CONF_BRIGHTNESS_STATE_TOPIC],
                "msg_callback": brightness_received,
                "qos": DEFAULT_QOS,
            }

        self._sub_state = await subscription.async_subscribe_topics(
            self.hass, self._sub_state, topics
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(
            self.hass, self._sub_state
        )

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = 0
        supported_features |= (
            self._config.get(CONF_BRIGHTNESS_COMMAND_TOPIC) is not None
            and SUPPORT_BRIGHTNESS
        )
        return supported_features

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        brightness = self._brightness
        if brightness:
            brightness = min(round(brightness), 255)
        return brightness

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        should_update = False
        await self.hass.data[DOMAIN].async_publish(
            self._config[CONF_COMMAND_TOPIC], 0, 0, False
        )
        if should_update:
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        if ATTR_BRIGHTNESS not in kwargs:
            kwargs[ATTR_BRIGHTNESS] = self._brightness if self._brightness else 255

        if (
            ATTR_BRIGHTNESS in kwargs
            and self._config.get(CONF_BRIGHTNESS_COMMAND_TOPIC) is not None
        ):
            brightness_normalized = kwargs[ATTR_BRIGHTNESS] / 255
            brightness_scale = 255
            device_brightness = min(
                round(brightness_normalized * brightness_scale), brightness_scale
            )
            # Make sure the brightness is not rounded down to 0
            device_brightness = max(device_brightness, 1)
            await self.hass.data[DOMAIN].async_publish(
                self._config[CONF_BRIGHTNESS_COMMAND_TOPIC], device_brightness, 0, False
            )

        await self.hass.data[DOMAIN].async_publish(
            self._config[CONF_COMMAND_TOPIC], 1, 0, False
        )
