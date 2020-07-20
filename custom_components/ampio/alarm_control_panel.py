"""Ampio Alarm Control Panel."""
import functools
import logging
from typing import Union

from homeassistant.components import alarm_control_panel as alarm
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMED,
    STATE_ALARM_DISARMING,
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
    CONF_ENTRYTIME_TOPIC,
    CONF_EXITTIME10_TOPIC,
    CONF_EXITTIME_TOPIC,
    CONF_RAW_TOPIC,
    DATA_AMPIO,
    DATA_AMPIO_DISPATCHERS,
    DEFAULT_QOS,
    SIGNAL_ADD_ENTITIES,
)
from .entity import AmpioEntity

_LOGGER = logging.getLogger(__name__)


class AmpioSatelAlarmControlPanel(AmpioEntity, alarm.AlarmControlPanelEntity):
    """Representation of Ampio Satel Alarm Control Panel."""

    def __init__(self, config):
        """Initialize the light component."""
        AmpioEntity.__init__(self, config)

        self._state = STATE_UNKNOWN
        self._armed = None
        self._alarm = None
        self._exittime = None
        self._exittime10 = None
        self._entrytime = None
        self._zone = None

        topic = self._config.get(CONF_ALARM_TOPIC)
        parts = topic.split("/")
        self._zone = int(parts[-1])
        mask = (0x01 << (self._zone - 1)) & 0xFFFFFFFF
        self._zone_mask: bytes = mask.to_bytes(4, byteorder="little")

    @property
    def state(self) -> Union[None, str, int, float]:
        """Return the state of the entity."""
        # _LOGGER.debug("%s,%s,%s,%s,%s", self._armed, self._alarm, self._exittime, self._exittime10, self._entrytime)
        if None in (
            self._armed,
            self._alarm,
            self._exittime,
            self._exittime10,
            self._entrytime,
        ):
            return None

        if self._alarm:
            return STATE_ALARM_TRIGGERED

        if self._armed:
            return STATE_ALARM_ARMED_HOME

        if self._exittime or self._exittime10:
            return STATE_ALARM_ARMING

        if self._entrytime:
            return STATE_ALARM_PENDING

        if not any(
            (
                self._armed,
                self._alarm,
                self._exittime,
                self._exittime10,
                self._entrytime,
            )
        ):
            return STATE_ALARM_DISARMED

        return self._state

    async def subscribe_topics(self):
        """(Re)Subscribe to topics."""
        topics = {}

        @callback
        def armed_message_received(msg):
            """Handler new MQTT message."""
            payload = msg.payload
            try:
                self._armed = bool(int(payload))
            except ValueError:
                _LOGGER.error("Unable to parse armed message: %s", payload)

            self.async_write_ha_state()

        topics[CONF_ARMED_TOPIC] = {
            "topic": self._config[CONF_ARMED_TOPIC],
            "msg_callback": armed_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def alarm_message_received(msg):
            """Handler new MQTT message."""
            payload = msg.payload
            try:
                self._alarm = bool(int(payload))
            except ValueError:
                _LOGGER.error("Unable to parse alarm message: %s", payload)

            self.async_write_ha_state()

        topics[CONF_ALARM_TOPIC] = {
            "topic": self._config[CONF_ALARM_TOPIC],
            "msg_callback": alarm_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def entrytime_message_received(msg):
            """Handler new MQTT message."""
            payload = msg.payload
            try:
                self._entrytime = bool(int(payload))
            except ValueError:
                _LOGGER.error("Unable to parse entrytime message: %s", payload)

            self.async_write_ha_state()

        topics[CONF_ENTRYTIME_TOPIC] = {
            "topic": self._config[CONF_ENTRYTIME_TOPIC],
            "msg_callback": entrytime_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def exittime_message_received(msg):
            """Handler new MQTT message."""
            payload = msg.payload
            try:
                self._exittime = bool(int(payload))
            except ValueError:
                _LOGGER.error("Unable to exittime alarm message: %s", payload)

            self.async_write_ha_state()

        topics[CONF_EXITTIME_TOPIC] = {
            "topic": self._config[CONF_EXITTIME_TOPIC],
            "msg_callback": exittime_message_received,
            "qos": DEFAULT_QOS,
        }

        @callback
        def exittime10_message_received(msg):
            """Handler new MQTT message."""
            payload = msg.payload
            try:
                self._exittime10 = bool(int(payload))
            except ValueError:
                _LOGGER.error("Unable to parse exittime10 message: %s", payload)

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
        return (
            alarm.SUPPORT_ALARM_ARM_HOME
            | alarm.SUPPORT_ALARM_ARM_AWAY
            | alarm.SUPPORT_ALARM_ARM_NIGHT
        )

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        cmd = f"1E0084{self._zone_mask.hex()}"
        _LOGGER.info("Command disarm: %s", cmd)
        async_publish(self.hass, self._config[CONF_RAW_TOPIC], cmd, 0, False)

    async def async_alarm_arm_night(self, code=None):
        """Send arm home command."""
        cmd = f"1E0080{self._zone_mask.hex()}"
        _LOGGER.debug("Command arm night: %s", cmd)
        async_publish(self.hass, self._config[CONF_RAW_TOPIC], cmd, 0, False)

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        cmd = f"1E0080{self._zone_mask.hex()}"
        _LOGGER.debug("Command arm home: %s", cmd)
        async_publish(self.hass, self._config[CONF_RAW_TOPIC], cmd, 0, False)

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        cmd = f"1E0080{self._zone_mask.hex()}"
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
