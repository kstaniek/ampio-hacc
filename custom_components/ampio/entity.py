"""Ampio Entities."""
import logging
from typing import Any, Dict, Optional

from homeassistant.const import (
    CONF_DEVICE,
    CONF_DEVICE_CLASS,
    CONF_FRIENDLY_NAME,
    CONF_ICON,
    CONF_NAME,
)
from homeassistant.core import Event
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_registry import EntityRegistry, async_get_registry
from homeassistant.helpers.typing import ConfigType

from .const import CONF_STATE_TOPIC, CONF_UNIQUE_ID

_LOGGER = logging.getLogger(__name__)


class AmpioEntity(Entity):
    """Base class for Ampio Entity."""

    def __init__(self, config):
        """Initialize the sensor."""
        self._config: Dict[str, Any] = config
        self._device_info: Dict[str, Any] = config.get(CONF_DEVICE)
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
    def device_info(self):
        """Return a device description for device registry."""
        return self._device_info

    @property
    def icon(self):
        """Return the icon."""
        return self._config.get(CONF_ICON)

    async def subscribe_topics(self):
        """Call to subscribe topics for entity."""
        return

    async def async_added_to_hass(self):
        """Action for initial topics subscription."""
        await super().async_added_to_hass()
        await self.subscribe_topics()

        # Update name with configured if None
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

    async def discovery_update(self, device_config):
        """Handle updated discovery message."""
        self._device_config = device_config
        # device_info = module.as_hass_device()
        # await self._device_info_discovery_update(device_info)
        self.async_write_ha_state()

    # async def _device_info_discovery_update(self, config: dict):
    #     """Handle updated discovery message."""
    #     _LOGGER.debug("Device info discovery update: %s", config)
    #     self._device_config = config
    #     device_registry = await self.hass.helpers.device_registry.async_get_registry()
    #     config_entry_id = self._config_entry.entry_id
    #     device_info = self.device_info

    #     if config_entry_id is not None and device_info is not None:
    #         device_info["config_entry_id"] = config_entry_id
    #         device_registry.async_get_or_create(**device_info)

    @property
    def device_info(self):
        """Return a device description for device registry."""
        return self._device_config

    # @property
    # def capability_attributes(self):
    #     """Return the capability attributes.

    #     Attributes that explain the capabilities of an entity.
    #     Implemented by component base class. Convention for attribute names
    #     is lowercase snake_case.
    #     """
    #     if self.registry_entry:
    #         device_id = self.registry_entry.device_id
    #     return {
    #         "model": self.device_info.model,
    #         "manufacturer": self.device_info.manufacturer,
    #         "module": self.device_info.name,
    #         "sw_version": self.device_info.sw_version,
    #     }


class AmpioModuleDiscoveryUpdate(Entity):
    """Mixin used to handle updated discovery message."""

    def __init__(self, discovery_update=None) -> None:
        """Initialize the discovery update mixin."""
        self._discovery_update = discovery_update
        self._remove_signal = None
        self._removed_from_hass = False

    async def async_added_to_hass(self) -> None:
        """Subscribe to discovery updates."""
        await super().async_added_to_hass()

        async def device_registry_updated(_event: Event) -> None:
            data = _event.data
            if data["action"] == "update":
                device_id = data["device_id"]
                device_registry = (
                    await self.hass.helpers.device_registry.async_get_registry()
                )
                device_config = device_registry.async_get(device_id)
                self._discovery_update(device_config)

        self._remove_signal = self.hass.bus.async_listen(
            dr.EVENT_DEVICE_REGISTRY_UPDATED, device_registry_updated
        )

    async def async_will_remove_from_hass(self) -> None:
        """Stop listening to signal and cleanup discovery data.."""
        self._cleanup_discovery_on_remove()

    def _cleanup_discovery_on_remove(self) -> None:
        """Stop listening to signal and cleanup discovery data."""
        if self._remove_signal:
            self._remove_signal()
            self._remove_signal = None
