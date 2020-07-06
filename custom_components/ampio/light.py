"""Ampio Lights."""
import logging

import homeassistant.util.color as color_util
from homeassistant.components import light
from homeassistant.components.light import (ATTR_BRIGHTNESS, ATTR_HS_COLOR,
                                            ATTR_WHITE_VALUE,
                                            SUPPORT_BRIGHTNESS, SUPPORT_COLOR,
                                            SUPPORT_WHITE_VALUE)
from homeassistant.const import CONF_DEVICE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import AmpioEntityDeviceInfo, BaseAmpioEntity, subscription
from .const import (AMPIO_DISCOVERY_NEW, CONF_BRIGHTNESS_COMMAND_TOPIC,
                    CONF_BRIGHTNESS_STATE_TOPIC, CONF_COMMAND_TOPIC,
                    CONF_RGB_COMMAND_TOPIC, CONF_RGB_STATE_TOPIC,
                    CONF_STATE_TOPIC, CONF_WHITE_VALUE_COMMAND_TOPIC,
                    CONF_WHITE_VALUE_STATE_TOPIC, DEFAULT_QOS, DOMAIN)
from .debug_info import log_messages
from .models import AmpioModuleInfo

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
        self._hs = None
        self._white_value = None

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
            self._state = bool(int(payload))
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
            brightness = int(payload)
            if brightness > 0:
                self._brightness = brightness
                self._state = True
                self.async_write_ha_state()

        if self._config.get(CONF_BRIGHTNESS_STATE_TOPIC) is not None:
            topics[CONF_BRIGHTNESS_STATE_TOPIC] = {
                "topic": self._config[CONF_BRIGHTNESS_STATE_TOPIC],
                "msg_callback": brightness_received,
                "qos": DEFAULT_QOS,
            }
            self._brightness = 255
        elif self._config.get(CONF_BRIGHTNESS_COMMAND_TOPIC) is not None:
            self._brightness = 255
        else:
            self._brightness = None

        @callback
        @log_messages(self.hass, self.entity_id)
        def rgb_received(msg):
            """Handler new MQTT message."""
            payload = msg.payload
            rgb = list(map(int, payload.split(",")))
            if any(rgb):
                self._hs = color_util.color_RGB_to_hs(*rgb[:3])
                percent_bright = float(color_util.color_RGB_to_hsv(*rgb[:3])[2]) / 100.0
                self._brightness = percent_bright * 255
                self._state = True
            else:
                self._state = False

            self.async_write_ha_state()

        if self._config.get(CONF_RGB_STATE_TOPIC) is not None:
            topics[CONF_RGB_STATE_TOPIC] = {
                "topic": self._config[CONF_RGB_STATE_TOPIC],
                "msg_callback": rgb_received,
                "qos": DEFAULT_QOS,
            }
            self._hs = (0, 0)

        elif self._config.get(CONF_RGB_COMMAND_TOPIC) is not None:
            self._hs = (0, 0)

        @callback
        @log_messages(self.hass, self.entity_id)
        def white_value_received(msg):
            """Handle new MQTT messages for white value."""
            self._white_value = float(msg.payload)
            if self._white_value > 0:
                self._state = True
            self.async_write_ha_state()

        if self._config.get(CONF_WHITE_VALUE_STATE_TOPIC) is not None:
            topics[CONF_WHITE_VALUE_STATE_TOPIC] = {
                "topic": self._config.get(CONF_WHITE_VALUE_STATE_TOPIC),
                "msg_callback": white_value_received,
                "qos": DEFAULT_QOS,
            }
            self._white_value = 255
        elif self._config.get(CONF_WHITE_VALUE_COMMAND_TOPIC) is not None:
            self._white_value = 255
        else:
            self._white_value = None

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
        supported_features |= (
            self._config.get(CONF_RGB_COMMAND_TOPIC) is not None and SUPPORT_COLOR
        )
        supported_features |= (
            self._config.get(CONF_WHITE_VALUE_COMMAND_TOPIC) is not None
            and SUPPORT_WHITE_VALUE
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

    @property
    def white_value(self):
        """Return the white property."""
        white_value = self._white_value
        if white_value:
            white_value = min(round(white_value), 255)
        return white_value

    @property
    def hs_color(self):
        """Return the hs color value."""
        return self._hs

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        if self._config.get(CONF_RGB_COMMAND_TOPIC) is not None:
            await self.hass.data[DOMAIN].async_publish(
                self._config[CONF_RGB_COMMAND_TOPIC], "off", 0, False
            )
        else:
            await self.hass.data[DOMAIN].async_publish(
                self._config[CONF_COMMAND_TOPIC], 0, 0, False
            )

        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        if ATTR_BRIGHTNESS not in kwargs:
            kwargs[ATTR_BRIGHTNESS] = self._brightness if self._brightness else 255

        if (
            ATTR_HS_COLOR in kwargs
            and self._config.get(CONF_RGB_COMMAND_TOPIC) is not None
        ):
            hs_color = kwargs[ATTR_HS_COLOR]

            if self._config.get(CONF_BRIGHTNESS_COMMAND_TOPIC) is not None:
                brightness = 255
            else:
                brightness = kwargs.get(
                    ATTR_BRIGHTNESS, self._brightness if self._brightness else 255
                )
            rgb = color_util.color_hsv_to_RGB(
                hs_color[0], hs_color[1], brightness / 255 * 100
            )
            rgb_color_str = ",".join(map(str, rgb))
            await self.hass.data[DOMAIN].async_publish(
                self._config[CONF_RGB_COMMAND_TOPIC], rgb_color_str, 0, False
            )

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
        elif (
            ATTR_BRIGHTNESS in kwargs
            and ATTR_HS_COLOR not in kwargs
            and self._config.get(CONF_RGB_COMMAND_TOPIC) is not None
        ):
            rgb = color_util.color_hsv_to_RGB(
                self._hs[0], self._hs[1], kwargs[ATTR_BRIGHTNESS] / 255 * 100
            )
            rgb_color_str = ",".join(map(str, rgb))

            await self.hass.data[DOMAIN].async_publish(
                self._config[CONF_RGB_COMMAND_TOPIC], rgb_color_str, 0, False
            )

        if (
            ATTR_WHITE_VALUE in kwargs
            and self._config[CONF_WHITE_VALUE_COMMAND_TOPIC] is not None
        ):
            percent_white = float(kwargs[ATTR_WHITE_VALUE]) / 255
            white_scale = 255
            device_white_value = min(round(percent_white * white_scale), white_scale)
            await self.hass.data[DOMAIN].async_publish(
                self._config[CONF_WHITE_VALUE_COMMAND_TOPIC],
                device_white_value,
                0,
                False,
            )

        if self._config.get(CONF_COMMAND_TOPIC) is not None:
            await self.hass.data[DOMAIN].async_publish(
                self._config[CONF_COMMAND_TOPIC], kwargs[ATTR_BRIGHTNESS], 0, False
            )
