"""Ampio platform consts."""
DOMAIN = "ampio"

CONF_BROKER = "broker"

AMPIO_CONNECTED = "ampio_connected"
AMPIO_DISCONNECTED = "ampio_disconnected"

DEFAULT_DISCOVERY = False
DEFAULT_QOS = 0
DEFAULT_RETAIN = False

PROTOCOL_311 = "3.1.1"


AMPIO_DISCOVERY_NEW = "ampio_discovery_new_{}_{}"
DATA_CONFIG_ENTRY_LOCK = "ampio_config_entry_lock"
CONFIG_ENTRY_IS_SETUP = "ampio_entry_is_setup"


CONF_STATE_TOPIC = "state_topic"
CONF_COMMAND_TOPIC = "command_topic"
CONF_BRIGHTNESS_STATE_TOPIC = "brightness_state_topic"
CONF_BRIGHTNESS_COMMAND_TOPIC = "brightness_command_topic"
CONF_UNIQUE_ID = "unique_id"
CONF_TILT_POSITION_TOPIC = "tilt_position_topic"
CONF_CLOSING_STATE_TOPIC = "cover_closing_state_topic"
CONF_OPENING_STATE_TOPIC = "cover_opening_state_topic"
CONF_RAW_TOPIC = "raw_topic"
