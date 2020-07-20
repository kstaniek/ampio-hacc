"""Ampio Cover."""
import functools
import logging

from homeassistant.components import cover
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import discovery, subscription
from .client import async_publish
from .const import (
    CONF_CLOSING_STATE_TOPIC,
    CONF_COMMAND_TOPIC,
    CONF_OPENING_STATE_TOPIC,
    CONF_RAW_TOPIC,
    CONF_STATE_TOPIC,
    CONF_TILT_POSITION_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    DEFAULT_QOS,
    SIGNAL_ADD_ENTITIES,
)
from .debug_info import log_messages
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)


class AmpioCover(AmpioEntity, cover.CoverEntity):
    """Representation of Ampio Cover."""

    def __init__(self, config):
        """Initialize the light component."""
        AmpioEntity.__init__(self, config)

        self._cover_position = None
        self._tilt_position = None
        self._opening = None
        self._closing = None
        self._index = None

        state_topic = self._config.get(CONF_STATE_TOPIC)
        if state_topic is not None:
            parts = state_topic.split("/")
            self._index = int(parts[-1])

        # AmpioModuleDiscoveryUpdate.__init__(self, self.discovery_update)
        # AmpioEntityDeviceInfo.__init__(self, device_info, config_entry)

    async def subscribe_topics(self):
        """(Re)Subscribe to topics."""
        topics = {}

        @callback
        @log_messages(self.hass, self.entity_id)
        def position_received(msg):
            """Handler new MQTT message."""
            payload = msg.payload
            try:
                self._cover_position = int(payload)
            except ValueError:
                return

            self.async_write_ha_state()

        if self._config.get(CONF_STATE_TOPIC) is not None:
            topics[CONF_STATE_TOPIC] = {
                "topic": self._config[CONF_STATE_TOPIC],
                "msg_callback": position_received,
                "qos": DEFAULT_QOS,
            }

        @callback
        @log_messages(self.hass, self.entity_id)
        def tilt_received(msg):
            payload = msg.payload
            try:
                self._tilt_position = int(payload)
            except ValueError:
                return

            self.async_write_ha_state()

        if self._config.get(CONF_TILT_POSITION_TOPIC) is not None:
            topics[CONF_TILT_POSITION_TOPIC] = {
                "topic": self._config[CONF_TILT_POSITION_TOPIC],
                "msg_callback": tilt_received,
                "qos": DEFAULT_QOS,
            }

        @callback
        @log_messages(self.hass, self.entity_id)
        def closing_received(msg):
            payload = msg.payload
            try:
                self._closing = bool(int(payload))
            except ValueError:
                return

            self.async_write_ha_state()

        if self._config.get(CONF_CLOSING_STATE_TOPIC) is not None:
            topics[CONF_CLOSING_STATE_TOPIC] = {
                "topic": self._config[CONF_CLOSING_STATE_TOPIC],
                "msg_callback": closing_received,
                "qos": DEFAULT_QOS,
            }

        @callback
        @log_messages(self.hass, self.entity_id)
        def opening_received(msg):
            payload = msg.payload
            try:
                self._opening = bool(int(payload))
            except ValueError:
                return

            self.async_write_ha_state()

        if self._config.get(CONF_OPENING_STATE_TOPIC) is not None:
            topics[CONF_OPENING_STATE_TOPIC] = {
                "topic": self._config[CONF_OPENING_STATE_TOPIC],
                "msg_callback": opening_received,
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
    def current_cover_position(self):
        """Return current position of cover.

        None is unknown, 0 is closed, 100 is fully open.
        """
        return self._cover_position

    @property
    def current_cover_tilt_position(self):
        """Return current position of cover tilt.

        None is unknown, 0 is closed, 100 is fully open.
        """
        return self._tilt_position

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening or not."""
        return self._opening

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing or not."""
        return self._closing

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed or not."""
        _is_closed = True
        if self._cover_position is not None:
            _is_closed = self._cover_position == 0
        if self._tilt_position is not None:
            _is_closed &= self._tilt_position == 0

        return _is_closed

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        async_publish(self.hass, self._config[CONF_COMMAND_TOPIC], 2, 0, False)

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        async_publish(self.hass, self._config[CONF_COMMAND_TOPIC], 1, 0, False)

    async def async_stop_cover(self, **kwargs):
        """Close cover."""
        async_publish(self.hass, self._config[CONF_COMMAND_TOPIC], 0, 0, False)

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get("position")
        if position is not None:
            cmd = b"\x00\x01"
            position = 0xFF & position
            position_bytes = position.to_bytes(1, byteorder="little")
            mask = 0xFF & (0x01 << (self._index - 1))
            mask_bytes = mask.to_bytes(1, byteorder="little")
            raw = (
                cmd + mask_bytes + position_bytes + b"\x66"
            )  # tilt to previous position
            async_publish(self.hass, self._config[CONF_RAW_TOPIC], raw.hex(), 0, False)

    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        cmd = b"\x00\x02"
        position = 0x64
        position_bytes = position.to_bytes(1, byteorder="little")
        mask = 0xFF & (0x01 << (self._index - 1))
        mask_bytes = mask.to_bytes(1, byteorder="little")
        raw = cmd + mask_bytes + position_bytes
        async_publish(self.hass, self._config[CONF_RAW_TOPIC], raw.hex(), 0, False)

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        cmd = b"\x00\x02"
        position = 0x00
        position_bytes = position.to_bytes(1, byteorder="little")
        mask = 0xFF & (0x01 << (self._index - 1))
        mask_bytes = mask.to_bytes(1, byteorder="little")
        raw = cmd + mask_bytes + position_bytes
        async_publish(self.hass, self._config[CONF_RAW_TOPIC], raw.hex(), 0, False)

    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position."""
        position = kwargs.get("tilt_position")
        if position is not None:
            cmd = b"\x00\x02"
            position = 0xFF & position
            position_bytes = position.to_bytes(1, byteorder="little")
            mask = 0xFF & (0x01 << (self._index - 1))
            mask_bytes = mask.to_bytes(1, byteorder="little")
            raw = cmd + mask_bytes + position_bytes
            async_publish(self.hass, self._config[CONF_RAW_TOPIC], raw.hex(), 0, False)

    async def async_stop_cover_tilt(self, **kwargs):
        """Stop the cover."""
        async_publish(self.hass, self._config[CONF_COMMAND_TOPIC], 0, 0, False)


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigType, async_add_entities
):
    """Set up MQTT sensors dynamically through MQTT discovery."""
    entities_to_create = hass.data[DATA_AMPIO][cover.DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioCover,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
