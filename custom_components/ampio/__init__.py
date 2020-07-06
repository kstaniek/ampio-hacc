"""Ampio Systems Platform."""
import json
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_CLIENT_ID, CONF_DEVICE,
                                 CONF_DEVICE_CLASS, CONF_FRIENDLY_NAME,
                                 CONF_ICON, CONF_NAME, CONF_PASSWORD,
                                 CONF_PORT, CONF_PROTOCOL, CONF_USERNAME,
                                 EVENT_HOMEASSISTANT_STOP)
from homeassistant.core import Event, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import event, template
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_registry import (EntityRegistry,
                                                   async_get_registry)
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .client import AmpioAPI
from .const import (AMPIO_CONNECTED, CONF_BROKER, CONF_STATE_TOPIC,
                    CONF_UNIQUE_ID, PROTOCOL_311)
from .models import AmpioModuleInfo

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ampio"


VERSION_TOPIC_FROM = "ampio/from/info/version"
VERSION_TOPIC_TO = "ampio/to/info/version"

DISCOVERY_TOPIC_FROM = "ampio/from/can/dev/list"
DISCOVERY_TOPIC_TO = "ampio/to/can/dev/list"

ATTR_DEVICES = "devices"

CONF_KEEPALIVE = "keepalive"

PROTOCOL_31 = "3.1"

DEFAULT_PORT = 1883
DEFAULT_KEEPALIVE = 60
DEFAULT_PROTOCOL = PROTOCOL_311


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            vol.Schema(
                {
                    vol.Optional(CONF_CLIENT_ID): cv.string,
                    vol.Optional(CONF_KEEPALIVE, default=DEFAULT_KEEPALIVE): vol.All(
                        vol.Coerce(int), vol.Range(min=15)
                    ),
                    vol.Optional(CONF_BROKER): cv.string,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                    vol.Optional(CONF_USERNAME): cv.string,
                    vol.Optional(CONF_PASSWORD): cv.string,
                    vol.Optional(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): vol.All(
                        cv.string, vol.In([PROTOCOL_31, PROTOCOL_311])
                    ),
                },
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Stub to allow setting up this component.
    Configuration through YAML is not supported at this time.
    """
    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up the Ampio component."""
    conf = CONFIG_SCHEMA({DOMAIN: dict(entry.data)})[DOMAIN]

    hass.data[DOMAIN]: AmpioAPI = AmpioAPI(
        hass, entry, conf,
    )

    async def async_connected():
        """Start discovery on connected."""
        await hass.data[DOMAIN].async_discovery(hass, entry)

    async_dispatcher_connect(hass, AMPIO_CONNECTED, async_connected)

    async def async_stop_ampio(_event: Event):
        """Stop MQTT component."""
        await hass.data[DOMAIN].async_disconnect()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_stop_ampio)

    await hass.data[DOMAIN].async_connect()

    return True


async def platform_async_setup_entry(
    hass: HomeAssistantType,
    entry: ConfigEntry,
    async_add_entities,
    *,
    component_key: str,
    info_type,
    entity_type,
    state_type,
) -> None:
    """Set up an esphome platform.
    This method is in charge of receiving, distributing and storing
    info and state updates.
    """
    _LOGGER.debug("Platform async setup entry")


class BaseAmpioEntity(Entity):
    """Base class for Ampio Entity."""

    def __init__(self, config, config_entry):
        """Initialize the sensor."""
        self._config: Dict[str, Any] = config
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._state = None
        self._sub_state = None

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._config[CONF_NAME]

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def device_class(self) -> Optional[str]:
        """Return the device class of the sensor."""
        return self._config.get(CONF_DEVICE_CLASS)

    @property
    def icon(self):
        """Return the icon."""
        return self._config.get(CONF_ICON)

    async def subscribe_topics(self):
        """Call to subscribe topics for entity."""
        return

    async def async_added_to_hass(self):
        """Action for initial topics subscription."""
        await self.subscribe_topics()
        entity_registry: EntityRegistry = await async_get_registry(self.hass)
        if self.registry_entry.name is None:
            entity_registry.async_update_entity(
                self.entity_id, name=self._config[CONF_FRIENDLY_NAME]
            )

    @property
    def device_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return device specific state attributes.
        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        state_topic = self._config.get(CONF_STATE_TOPIC)
        if state_topic:
            parts = state_topic.split("/")
            if len(parts) > 1:
                return {"value": parts[-2], "index": parts[-1]}
        return None


class AmpioEntityDeviceInfo(Entity):
    """Mixin used for mqtt platforms that support the device registry."""

    def __init__(self, device_config: Optional[ConfigType], config_entry=None) -> None:
        """Initialize the device mixin."""
        self._device_config = device_config
        self._config_entry = config_entry

    async def device_info_discovery_update(self, config: dict):
        """Handle updated discovery message."""
        _LOGGER.error("Device info discovery updated.")
        # self._device_config = config.get(CONF_DEVICE)
        # device_registry = await self.hass.helpers.device_registry.async_get_registry()
        # config_entry_id = self._config_entry.entry_id
        # device_info = self.device_info

        # if config_entry_id is not None and device_info is not None:
        #     device_info["config_entry_id"] = config_entry_id
        #     device_registry.async_get_or_create(**device_info)

    @property
    def device_info(self):
        """Return a device description for device registry."""
        return self._device_config

    @property
    def capability_attributes(self):
        """Return the capability attributes.

        Attributes that explain the capabilities of an entity.
        Implemented by component base class. Convention for attribute names
        is lowercase snake_case.
        """
        return {
            "model": self.device_info.get("model"),
            "manufacturer": self.device_info.get("manufacturer"),
            "module": self.device_info.get("name"),
            "sw_version": self.device_info.get("sw_version"),
        }
