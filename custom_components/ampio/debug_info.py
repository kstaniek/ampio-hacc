"""Helper to handle a set of topics to subscribe to."""
import logging
from collections import deque
from functools import wraps
from typing import Any

from homeassistant.helpers.typing import HomeAssistantType

from .models import MessageCallbackType

_LOGGER = logging.getLogger(__name__)

DATA_MQTT_DEBUG_INFO = "ampio_debug_info"
STORED_MESSAGES = 10


def log_messages(hass: HomeAssistantType, entity_id: str) -> MessageCallbackType:
    """Wrap an MQTT message callback to support message logging."""

    def _log_message(msg):
        """Log message."""
        debug_info = hass.data[DATA_MQTT_DEBUG_INFO]
        messages = debug_info["entities"][entity_id]["subscriptions"][
            msg.subscribed_topic
        ]["messages"]
        if msg not in messages:
            messages.append(msg)

    def _decorator(msg_callback: MessageCallbackType):
        @wraps(msg_callback)
        def wrapper(msg: Any) -> None:
            """Log message."""
            _log_message(msg)
            msg_callback(msg)

        setattr(wrapper, "__entity_id", entity_id)
        return wrapper

    return _decorator


def add_subscription(hass, message_callback, subscription):
    """Prepare debug data for subscription."""
    entity_id = getattr(message_callback, "__entity_id", None)
    if entity_id:
        debug_info = hass.data.setdefault(
            DATA_MQTT_DEBUG_INFO, {"entities": {}, "triggers": {}}
        )
        entity_info = debug_info["entities"].setdefault(
            entity_id, {"subscriptions": {}, "discovery_data": {}}
        )
        if subscription not in entity_info["subscriptions"]:
            entity_info["subscriptions"][subscription] = {
                "count": 0,
                "messages": deque([], STORED_MESSAGES),
            }
        entity_info["subscriptions"][subscription]["count"] += 1


def remove_subscription(hass, message_callback, subscription):
    """Remove debug data for subscription if it exists."""
    entity_id = getattr(message_callback, "__entity_id", None)
    if entity_id and entity_id in hass.data[DATA_MQTT_DEBUG_INFO]["entities"]:
        hass.data[DATA_MQTT_DEBUG_INFO]["entities"][entity_id]["subscriptions"][
            subscription
        ]["count"] -= 1
        if not hass.data[DATA_MQTT_DEBUG_INFO]["entities"][entity_id]["subscriptions"][
            subscription
        ]["count"]:
            hass.data[DATA_MQTT_DEBUG_INFO]["entities"][entity_id]["subscriptions"].pop(
                subscription
            )
