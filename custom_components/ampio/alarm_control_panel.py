"""Ampio Alarm Control Panel."""
import asyncio
import functools
import logging
from typing import Optional, Union

from homeassistant.components import alarm_control_panel as alarm
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMED,
    STATE_ALARM_PENDING,
    STATE_ALARM_TRIGGERED,
    STATE_UNKNOWN,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import discovery, subscription
from .client import async_publish
from .const import (
    CONF_ALARM_TOPIC,
    CONF_ARMED_TOPIC,
    CONF_AWAY_ZONES,
    CONF_ENTRYTIME_TOPIC,
    CONF_EXITTIME10_TOPIC,
    CONF_EXITTIME_TOPIC,
    CONF_HOME_ZONES,
    CONF_RAW_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    DEFAULT_QOS,
    SIGNAL_ADD_ENTITIES,
)
from .entity import AmpioEntity
from .models import IndexIntData

_LOGGER = logging.getLogger(__name__)


class AmpioSatelAlarmControlPanel(AmpioEntity, alarm.AlarmControlPanelEntity):
    """Representation of Ampio Satel Alarm Control Panel."""

    def __init__(self, config):
        """Initialize the light component."""
        AmpioEntity.__init__(self, config)

        self._state = STATE_UNKNOWN
        self._armed = set()
        self._alarm = set()
        self._exittime = set()
        self._exittime10 = set()
        self._entrytime = set()

        self._home_zones = set()
        self._home_cmd_data: Optional[str] = None
        self._away_zones = set()
        self._away_cmd_data: Optional[str] = None
        self._all_cmd_data: Optional[str] = None
        self._supported_features = 0

        if CONF_AWAY_ZONES in self._config:
            self._away_zones = self._config[CONF_AWAY_ZONES]
            self._supported_features |= alarm.SUPPORT_ALARM_ARM_AWAY
            mask = 0
            for zone in self._away_zones:
                mask |= (0x01 << (zone - 1)) & 0xFFFFFFFF
            self._away_cmd_data = mask.to_bytes(4, byteorder="little").hex()

        if CONF_HOME_ZONES in self._config:
            self._home_zones = self._config[CONF_HOME_ZONES]
            self._supported_features |= alarm.SUPPORT_ALARM_ARM_HOME
            mask = 0
            for zone in self._home_zones:
                mask |= (0x01 << (zone - 1)) & 0xFFFFFFFF
            self._home_cmd_data = mask.to_bytes(4, byteorder="little").hex()

        all_zones = self._home_zones | self._away_zones
        mask = 0
        for zone in all_zones:
            mask |= (0x01 << (zone - 1)) & 0xFFFFFFFF
        self._all_cmd_data = mask.to_bytes(4, byteorder="little").hex()

    @property
    def state(self) -> Union[None, str, int, float]:
        """Return the state of the entity."""
        if self._away_zones == self._armed & self._away_zones:
            self._state = STATE_ALARM_ARMED_AWAY

        if self._home_zones == self._armed & self._home_zones:
            self._state = STATE_ALARM_ARMED_HOME

        if self._alarm:
            self._state = STATE_ALARM_TRIGGERED

        if self._exittime or self._exittime10:
            self._state = STATE_ALARM_ARMING

        if self._entrytime:
            self._state = STATE_ALARM_PENDING

        if not any(
            (
                self._armed,
                self._alarm,
                self._exittime,
                self._exittime10,
                self._entrytime,
            )
        ):
            self._state = STATE_ALARM_DISARMED

        return self._state

    async def subscribe_topics(self):
        """(Re)Subscribe to topics."""
        topics = {}

        @callback
        def armed_message_received(msg):
            """Handler new MQTT message."""
            data = IndexIntData.from_msg(msg)
            if data is None:
                _LOGGER.error("Undable to parse MQTT message")

            if data.value == 1:
                self._armed.add(data.index)
            else:
                self._armed.discard(data.index)

            _LOGGER.debug("Armed: %s", self._armed)
            self.async_write_ha_state()

        topics[CONF_ARMED_TOPIC] = {
            "topic": self._config[CONF_ARMED_TOPIC],
            "msg_callback": armed_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def alarm_message_received(msg):
            """Handler new MQTT message."""
            data = IndexIntData.from_msg(msg)
            if data is None:
                _LOGGER.error("Undable to parse MQTT message")

            if data.value == 1:
                self._alarm.add(data.index)
            else:
                self._alarm.discard(data.index)

            _LOGGER.debug("Alarm: %s", self._alarm)
            self.async_write_ha_state()

        topics[CONF_ALARM_TOPIC] = {
            "topic": self._config[CONF_ALARM_TOPIC],
            "msg_callback": alarm_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def entrytime_message_received(msg):
            """Handler new MQTT message."""
            data = IndexIntData.from_msg(msg)
            if data is None:
                _LOGGER.error("Undable to parse MQTT message")

            if data.value == 1:
                self._entrytime.add(data.index)
            else:
                self._entrytime.discard(data.index)

            _LOGGER.debug("Entry Time: %s", self._entrytime)
            self.async_write_ha_state()

        topics[CONF_ENTRYTIME_TOPIC] = {
            "topic": self._config[CONF_ENTRYTIME_TOPIC],
            "msg_callback": entrytime_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def exittime_message_received(msg):
            """Handler new MQTT message."""
            data = IndexIntData.from_msg(msg)
            if data is None:
                _LOGGER.error("Undable to parse MQTT message")

            if data.value == 1:
                self._exittime.add(data.index)
            else:
                self._exittime.discard(data.index)

            _LOGGER.debug("Arming <10s: %s", self._exittime)
            self.async_write_ha_state()

        topics[CONF_EXITTIME_TOPIC] = {
            "topic": self._config[CONF_EXITTIME_TOPIC],
            "msg_callback": exittime_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def exittime10_message_received(msg):
            """Handler new MQTT message."""
            data = IndexIntData.from_msg(msg)
            if data is None:
                _LOGGER.error("Undable to parse MQTT message")

            if data.value == 1:
                self._exittime10.add(data.index)
            else:
                self._exittime10.discard(data.index)

            _LOGGER.debug("Arming >10s: %s", self._exittime10)
            self.async_write_ha_state()

        topics[CONF_EXITTIME10_TOPIC] = {
            "topic": self._config[CONF_EXITTIME10_TOPIC],
            "msg_callback": exittime10_message_received,
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
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return self._supported_features

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        clear_alarm = self._state == STATE_ALARM_TRIGGERED
        cmd = f"1E0084{self._all_cmd_data}"
        _LOGGER.debug("Command disarm: %s", cmd)
        async_publish(self.hass, self._config[CONF_RAW_TOPIC], cmd, 0, False)

        if clear_alarm:
            # Wait 1s before clearing the alarm
            await asyncio.sleep(1)
            cmd = f"1E0085{self._all_cmd_data}"
            _LOGGER.debug("Command clear: %s", cmd)
            async_publish(self.hass, self._config[CONF_RAW_TOPIC], cmd, 0, False)

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        cmd = f"1E0080{self._home_cmd_data}"
        _LOGGER.debug("Command arm home: %s", cmd)
        async_publish(self.hass, self._config[CONF_RAW_TOPIC], cmd, 0, False)

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        cmd = f"1E0080{self._away_cmd_data}"
        _LOGGER.debug("Command arm home: %s", cmd)
        async_publish(self.hass, self._config[CONF_RAW_TOPIC], cmd, 0, False)


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigType, async_add_entities
):
    """Set up MQTT sensors dynamically through MQTT discovery."""
    entities_to_create = hass.data[DATA_AMPIO][alarm.DOMAIN]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
            AmpioSatelAlarmControlPanel,
        ),
    )
    hass.data[DATA_AMPIO][DATA_AMPIO_DISPATCHERS].append(unsub)
