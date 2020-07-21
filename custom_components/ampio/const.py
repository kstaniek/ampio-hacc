"""Ampio platform consts."""


from homeassistant.components.alarm_control_panel import DOMAIN as ALARM_CONTROL_PANEL
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.components.switch import DOMAIN as SWITCH

COMPONENTS = (
    ALARM_CONTROL_PANEL,
    BINARY_SENSOR,
    COVER,
    LIGHT,
    SENSOR,
    SWITCH,
)

DOMAIN = "ampio"

CONF_BROKER = "broker"

AMPIO_CONNECTED = "ampio_connected"
AMPIO_DISCONNECTED = "ampio_disconnected"

DATA_AMPIO = "ampio"
DATA_AMPIO_MODULES = "modules"
DATA_AMPIO_API = "api"
DATA_AMPIO_CONFIG = "config"
DATA_AMPIO_PLATFORM_LOADED = "plarform_loaded"
DATA_AMPIO_DISPATCHERS = "dispatchers"
DATA_AMPIO_UNIQUE_IDS = "unique_ids"


DEFAULT_DISCOVERY = False
DEFAULT_QOS = 0
DEFAULT_RETAIN = False

PROTOCOL_311 = "3.1.1"


SIGNAL_ADD_ENTITIES = "ampio_add_new_entities"
AMPIO_DISCOVERY_NEW = "ampio_discovery_new_{}_{}"
AMPIO_DISCOVERY_UPDATED = "ampio_discovery_updated"
AMPIO_MODULE_DISCOVERY_UPDATED = "ampio_module_discovery_updated"
DATA_CONFIG_ENTRY_LOCK = "ampio_config_entry_lock"
CONFIG_ENTRY_IS_SETUP = "ampio_entry_is_setup"


CONF_STATE_TOPIC = "state_topic"
CONF_COMMAND_TOPIC = "command_topic"
CONF_BRIGHTNESS_STATE_TOPIC = "brightness_state_topic"
CONF_BRIGHTNESS_COMMAND_TOPIC = "brightness_command_topic"
CONF_UNIQUE_ID = "unique_id"
CONF_DEVICE_INFO = "device_info"
CONF_TILT_POSITION_TOPIC = "tilt_position_topic"
CONF_CLOSING_STATE_TOPIC = "cover_closing_state_topic"
CONF_OPENING_STATE_TOPIC = "cover_opening_state_topic"
CONF_RAW_TOPIC = "raw_topic"
CONF_RGB_STATE_TOPIC = "rgb_state_topic"
CONF_RGB_COMMAND_TOPIC = "rgb_command_topic"
CONF_WHITE_VALUE_STATE_TOPIC = "white_state_topic"
CONF_WHITE_VALUE_COMMAND_TOPIC = "white_command_topic"
CONF_ARMED_TOPIC = "armed_topic"
CONF_ALARM_TOPIC = "alarm_topic"
CONF_ENTRYTIME_TOPIC = "entrytime_topic"
CONF_EXITTIME10_TOPIC = "exittime10_topic"
CONF_EXITTIME_TOPIC = "exittime_topic"
CONF_AWAY_ZONES = "away_zones"
CONF_HOME_ZONES = "home_zones"

ATTR_VERSION = "version"
ATTR_DISCOVERY_PAYLOAD = "discovery_payload"
ATTR_DEVICE_INFO = "device_info"
ATTR_COMPONENT_CONFIGS = "configs"
