"""Ampio MQTT api implementation."""
import asyncio
import json
import logging
import re
from itertools import groupby
from operator import attrgetter
from typing import List, Optional

import homeassistant.helpers.device_registry as dr
from homeassistant.components.mqtt import MQTT, Subscription
from homeassistant.components.mqtt.models import MessageCallbackType
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT
from homeassistant.core import Callable, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import (async_dispatcher_send,
                                              dispatcher_send)
from homeassistant.helpers.typing import HomeAssistantType

from .const import (AMPIO_CONNECTED, AMPIO_DISCONNECTED, AMPIO_DISCOVERY_NEW,
                    CONF_BROKER, CONFIG_ENTRY_IS_SETUP, DATA_CONFIG_ENTRY_LOCK)
from .models import AmpioModuleInfo, ItemName

AMPIO_TO_INFO_TOPIC = "ampio/to/info/version"
AMPIO_FROM_INFO_TOPIC = "ampio/from/info/version"

REQUEST_MODULE_DISCOVERY = "ampio/to/can/dev/list"
RESPONSE_MODULE_DISCOVERY = "ampio/from/can/dev/list"

REQUEST_MODULE_NAMES = "ampio/to/{mac}/description"
RESPONSE_MODULE_NAMES = "ampio/from/+/description"

# ampio/from/1B88/description
MAC_FROM_TOPIC_RE = re.compile(r"^ampio/from/(?P<mac>.*)/.*$")

AMPIO_EMPTY_PAYLOAD = ""
AMPIO_MODULES = "ampio_modules"

_LOGGER = logging.getLogger(__name__)


class AmpioAPI(MQTT):
    """Ampio MQTT Api."""

    def _mqtt_on_connect(self, _mqttc, _userdata, _flags, result_code: int) -> None:
        """On connect callback.
        Resubscribe to all topics we were subscribed to and publish birth
        message.
        """
        # pylint: disable=import-outside-toplevel
        import paho.mqtt.client as mqtt

        if result_code != mqtt.CONNACK_ACCEPTED:
            _LOGGER.error(
                "Unable to connect to the MQTT broker: %s",
                mqtt.connack_string(result_code),
            )
            return

        self.connected = True
        dispatcher_send(self.hass, AMPIO_CONNECTED)
        _LOGGER.info(
            "Connected to Ampio MQTT Server %s:%s (%s)",
            self.conf[CONF_BROKER],
            self.conf[CONF_PORT],
            result_code,
        )

        # Group subscriptions to only re-subscribe once for each topic.
        keyfunc = attrgetter("topic")
        for topic, subs in groupby(sorted(self.subscriptions, key=keyfunc), keyfunc):
            # Re-subscribe with the highest requested qos
            max_qos = max(subscription.qos for subscription in subs)
            self.hass.add_job(self._async_perform_subscription, topic, max_qos)

    def _mqtt_on_disconnect(self, _mqttc, _userdata, result_code: int) -> None:
        """Disconnected callback."""
        self.connected = False
        dispatcher_send(self.hass, AMPIO_DISCONNECTED)
        _LOGGER.warning(
            "Disconnected from Ampio MQTT Server %s:%s (%s)",
            self.conf[CONF_BROKER],
            self.conf[CONF_PORT],
            result_code,
        )

    async def async_subscribe(
        self,
        topic: str,
        msg_callback: MessageCallbackType,
        qos: int,
        encoding: Optional[str] = None,
    ) -> Callable[[], None]:
        """Set up a subscription to a topic with the provided qos.
        This method is a coroutine.
        """
        if not isinstance(topic, str):
            raise HomeAssistantError("Topic needs to be a string!")

        subscription = Subscription(topic, msg_callback, qos, encoding)
        self.subscriptions.append(subscription)

        # Only subscribe if currently connected.
        if self.connected:
            await self._async_perform_subscription(topic, qos)

        @callback
        def async_remove() -> None:
            """Remove subscription."""
            if subscription not in self.subscriptions:
                raise HomeAssistantError("Can't remove subscription twice")
            self.subscriptions.remove(subscription)

            if any(other.topic == topic for other in self.subscriptions):
                # Other subscriptions on topic remaining - don't unsubscribe.
                return

            # Only unsubscribe if currently connected.
            if self.connected:
                self.hass.async_create_task(self._async_unsubscribe(topic))

        return async_remove

    async def _async_perform_subscription(self, topic: str, qos: int) -> None:
        """Perform a paho-mqtt subscription."""
        _LOGGER.debug("Subscribing to %s", topic)

        async with self._paho_lock:
            result: int = None
            result, _ = await self.hass.async_add_executor_job(
                self._mqttc.subscribe, topic, qos
            )
            _raise_on_error(result)

    async def async_discovery(self, hass: HomeAssistantType, config_entry=None) -> bool:
        """Start Ampio Modules Discovery."""

        async def async_device_names_received(msg):
            "Handle names update." ""

            matched = MAC_FROM_TOPIC_RE.match(msg.topic)
            if matched:
                mac = matched.group("mac").upper()
                if mac in hass.data[AMPIO_MODULES].keys():
                    module = hass.data[AMPIO_MODULES].get(mac)
                    if module is None:
                        return
                else:
                    return

            payload = msg.payload

            if payload:
                try:
                    payload = json.loads(payload)
                except ValueError:
                    _LOGGER.warning("Unable to parse JSON '%s'", payload)
                    return
            module.names = ItemName.from_topic_payload(payload)
            module.update_configs()

            _LOGGER.info(
                "Discovered: %s-%s (%s): %s",
                module.code,
                module.model,
                module.software,
                module.name,
            )

            for component in module.configs.keys():
                config_entries_key = f"{component}.ampio"

                async with hass.data[DATA_CONFIG_ENTRY_LOCK]:
                    if config_entries_key not in hass.data[CONFIG_ENTRY_IS_SETUP]:
                        await hass.config_entries.async_forward_entry_setup(
                            config_entry, component
                        )
                    hass.data[CONFIG_ENTRY_IS_SETUP].add(config_entries_key)

                async_dispatcher_send(
                    hass, AMPIO_DISCOVERY_NEW.format(component, "ampio"), module
                )

            _LOGGER.debug("Fully discovered %s", module)

        async def async_device_message_received(msg):
            """Process the received message."""
            payload = msg.payload
            if payload:
                try:
                    payload = json.loads(payload)
                except ValueError:
                    _LOGGER.warning("Unable to parse JSON '%s'", payload)
                    return

            if "devices" not in payload.keys():
                _LOGGER.warning("Missing discovery information")
                return

            modules: List[AmpioModuleInfo] = AmpioModuleInfo.from_topic_payload(payload)

            for module in modules:
                await _async_setup_device_registry(hass, config_entry, module)

                hass.data[AMPIO_MODULES][module.user_mac] = module

                await self.async_publish(
                    REQUEST_MODULE_NAMES.format(mac=module.user_mac), "1", 0, False
                )

        hass.data[DATA_CONFIG_ENTRY_LOCK] = asyncio.Lock()
        hass.data[CONFIG_ENTRY_IS_SETUP] = set()
        hass.data[AMPIO_MODULES] = {}

        # TODO: Unsubscribe
        await self.async_subscribe(
            RESPONSE_MODULE_DISCOVERY, async_device_message_received, 0
        )
        await self.async_subscribe(
            RESPONSE_MODULE_NAMES, async_device_names_received, 0
        )

        await self.async_publish(REQUEST_MODULE_DISCOVERY, "1", 0, False)


def _raise_on_error(result_code: int) -> None:
    """Raise error if error result."""
    # pylint: disable=import-outside-toplevel
    import paho.mqtt.client as mqtt

    if result_code != 0:
        raise HomeAssistantError(
            f"Error talking to Ampio MQTT: {mqtt.error_string(result_code)}"
        )


async def _async_setup_device_registry(
    hass: HomeAssistantType, entry: ConfigEntry, device_info: AmpioModuleInfo
):
    """Set up device registry feature for a particular config entry."""
    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id, **device_info.as_hass_device()
    )


# async def _sync_setup_entities(
#     hass: HomeAssistantType, device_info
# )
