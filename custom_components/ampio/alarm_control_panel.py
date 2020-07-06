"""Ampio Alarm Control Panel."""
import logging

from homeassistant.components import alarm_control_panel
from homeassistant.const import CONF_DEVICE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.const import (
    CONF_CODE,
    CONF_DEVICE,
    CONF_NAME,
    CONF_VALUE_TEMPLATE,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMED,
    STATE_ALARM_DISARMING,
    STATE_ALARM_PENDING,
    STATE_ALARM_TRIGGERED,
)

from . import AmpioEntityDeviceInfo, BaseAmpioEntity, subscription
from .const import (AMPIO_DISCOVERY_NEW, CONF_COMMAND_TOPIC, CONF_RAW_TOPIC,
                    CONF_STATE_TOPIC, DEFAULT_QOS, DOMAIN)
from .debug_info import log_messages
from .models import AmpioModuleInfo

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigType, async_add_entities
):
    """Set up MQTT sensors dynamically through MQTT discovery."""

    async def async_discover_switch(module: AmpioModuleInfo):
        """Discover and add a discovered MQTT sensor."""
        configs = module.configs.get(alarm_control_panel.DOMAIN)
        entities = [
            AmpioSatelAlarmControlPanel(config, config_entry) for config in configs
        ]
        async_add_entities(entities)

    async_dispatcher_connect(
        hass,
        AMPIO_DISCOVERY_NEW.format(alarm_control_panel.DOMAIN, "ampio"),
        async_discover_switch,
    )


class AmpioSatelAlarmControlPanel(
    BaseAmpioEntity, AmpioEntityDeviceInfo, alarm_control_panel.AlarmControlPanelEntity
):
    """Representation of Ampio Satel Alarm Control Panel."""

    def __init__(self, config, config_entry):
        """Initialize the sensor."""
        BaseAmpioEntity.__init__(self, config, config_entry)
        self._state = "armed"

        device_config = config.get(CONF_DEVICE)
        AmpioEntityDeviceInfo.__init__(self, device_config, config_entry)

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return alarm_control_panel.SUPPORT_ALARM_ARM_HOME
