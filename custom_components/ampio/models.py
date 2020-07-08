"""Ampio data models."""
from __future__ import annotations

import base64
from collections import defaultdict
from enum import IntEnum
from typing import Any, Callable, Dict, List, Union

import attr

from homeassistant.const import (CONF_DEVICE, CONF_DEVICE_CLASS,
                                 CONF_FRIENDLY_NAME, CONF_ICON, CONF_NAME,
                                 CONF_UNIT_OF_MEASUREMENT)
from homeassistant.helpers import device_registry

from .const import (CONF_BRIGHTNESS_COMMAND_TOPIC, CONF_BRIGHTNESS_STATE_TOPIC,
                    CONF_CLOSING_STATE_TOPIC, CONF_COMMAND_TOPIC,
                    CONF_OPENING_STATE_TOPIC, CONF_RAW_TOPIC,
                    CONF_RGB_COMMAND_TOPIC, CONF_RGB_STATE_TOPIC,
                    CONF_STATE_TOPIC, CONF_TILT_POSITION_TOPIC, CONF_UNIQUE_ID,
                    CONF_WHITE_VALUE_COMMAND_TOPIC,
                    CONF_WHITE_VALUE_STATE_TOPIC, DOMAIN)
from .validators import (AMPIO_DESCRIPTIONS_SCHEMA, AMPIO_DEVICES_SCHEMA,
                         ATTR_AI, ATTR_AO, ATTR_BI, ATTR_BO, ATTR_D,
                         ATTR_DATE_PROD, ATTR_DEVICES, ATTR_FLAG, ATTR_MAC,
                         ATTR_N, ATTR_NAME, ATTR_PCB, ATTR_PROTOCOL,
                         ATTR_SOFTWARE, ATTR_T, ATTR_TYPE, ATTR_USERMAC)

DEVICE_CLASSES = {
    "B": "battery",
    "BC": "battery_charging",
    "C": "cold",
    "CO": "connectivity",
    "D": "door",
    "GD": "garage_door",
    "GA": "gas",
    "HE": "heat",
    "L": "light",
    "LO": "lock",
    "MI": "moisture",
    "M": "motion",
    "MV": "moving",
    "OC": "occupancy",
    "O": "opening",
    "P": "plug",
    "PW": "power",
    "PR": "presence",
    "PB": "problem",
    "S": "safety",
    "SO": "sound",
    "V": "vibration",
    "W": "window",
    # switches
    "OU": "outlet",
    # sensors
    "T": "temperature",
    "H": "humidity",
    "I": "illuminance",
    "SS": "signal_strength",
    "PS": "pressure",
    "TS": "timestamp",
    # covers
    "VA": "valve",
    "G": "garage",
    "BL": "blind",
}

TYPE_CODES = {
    44: "MSENS",
    3: "MROL-4s",
    4: "MPR-8s",
    5: "MDIM-8s",
    8: "MDOT-4",
    10: "MSERV-3s",
    11: "MDOT-9",
    12: "MRGBu-1",
    17: "MLED-1",
    22: "MRT-16s",
    25: "MCON",
    26: "MOC-4",
    27: "MDOT-15LCD",
    33: "MDOT-2",
    34: "METEO-1s",
    38: "MRDN-1s",
    49: "MWRC",
}


class ModuleCodes(IntEnum):
    """Module codes enum."""

    MLED1 = 17
    MCON = 25
    MDIM8s = 5
    MSENS = 44
    MDOT2 = 33


DOMAIN = "ampio"

PublishPayloadType = Union[str, bytes, int, float, None]


@attr.s(slots=True, frozen=True)
class Message:
    """MQTT Message."""

    topic = attr.ib(type=str)
    payload = attr.ib(type=PublishPayloadType)
    qos = attr.ib(type=int)
    retain = attr.ib(type=bool)


MessageCallbackType = Callable[[Message], None]


class ItemTypes(IntEnum):
    """Item type codes."""

    OW = 3
    BinaryFlag = 6
    BinaryInput254 = 10
    BinaryInput509 = 11
    BinaryOutput254 = 12
    BinaryOutput509 = 13
    AnalogInput254 = 14
    AnalogInput509 = 15
    AnalogOutput254 = 16
    AnalogOutput509 = 17


def base64decode(value: str):
    """Decode base64 string."""
    try:
        return base64.b64decode(value).decode("utf-8").strip()
    except UnicodeDecodeError:
        return base64.b64decode(value).decode("cp1254").strip()


def base64encode(value: str):
    """Encode base64 string."""
    return base64.b64encode(value.encode("utf-8"))


@attr.s()
class ItemName:
    """Name of the ampio module Item (input, output, flag, etc)."""

    d = attr.ib(type=str, converter=base64decode)  # pylint: disable=invalid-name

    name = attr.ib(type=str)
    device_class = attr.ib(type=str)

    @name.default
    def extract_name(self):
        """Compute name."""
        parts = self.d.split(":")
        if len(parts) > 1:
            return "".join(parts[1:])
        return self.d

    @device_class.default
    def extract_device_class(self):
        """Compute device_class."""
        parts = self.d.split(":")
        if len(parts) > 1:
            prefix = parts[0]
            return DEVICE_CLASSES.get(prefix)

    @classmethod
    def from_topic_payload(cls, payload: Dict) -> List[ItemName]:
        """Read from topic payload."""
        names: Dict[str, Union[int, Dict]] = AMPIO_DESCRIPTIONS_SCHEMA(payload)
        result = {}
        for name in names[ATTR_D]:
            name_data = name[ATTR_D]
            name_type = name[ATTR_T]
            name_index = name[ATTR_N]
            if name_type not in result.keys():
                result[name_type] = {}
            result[name_type][name_index] = ItemName(name_data)
        return result


@attr.s()
class AmpioModuleInfo:
    """Ampio Module Information."""

    mac = attr.ib(type=str, converter=str.upper)
    user_mac = attr.ib(type=str, converter=str.upper)
    code = attr.ib(type=int)
    pcb = attr.ib(type=int)
    software = attr.ib(type=int)
    protocol = attr.ib(type=int)
    date_prod = attr.ib(type=str)
    bi = attr.ib(type=int)  # pylint: disable=invalid-name
    bo = attr.ib(type=int)  # pylint: disable=invalid-name
    ai = attr.ib(type=int)  # pylint: disable=invalid-name
    ao = attr.ib(type=int)  # pylint: disable=invalid-name
    flags = attr.ib(type=int)
    name = attr.ib(type=str, converter=base64decode)

    names = attr.ib(factory=dict)
    configs = attr.ib(factory=dict)

    def update_configs(self) -> None:
        """Update the config data for entities."""
        self.configs = defaultdict(list)  # clean up current configs
        for index, item in self.names.get(ItemTypes.BinaryFlag, {}).items():
            data = AmpioFlagConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["switch"].append(data.config)

        for index, item in self.names.get(ItemTypes.OW, {}).items():
            data = AmpioTempSensorConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["sensor"].append(data.config)

    @property
    def part_number(self) -> str:
        """Return module part number (code)."""
        return TYPE_CODES.get(self.code, self.code)

    @property
    def model(self) -> str:
        """Return model name."""
        return f"{self.part_number} [{self.mac.upper()}/{self.user_mac.upper()}]"

    def as_hass_device(self) -> Dict[str, Any]:
        """Return info in hass device format."""
        return {
            "connections": {(device_registry.CONNECTION_NETWORK_MAC, self.user_mac)},
            "identifiers": {(DOMAIN, self.user_mac)},
            "name": self.name,
            "manufacturer": "Ampio",
            "model": self.model,
            "sw_version": self.software,
            "via_device": None,
        }

    @classmethod
    def from_topic_payload(cls, payload: dict) -> AmpioModuleInfo:
        """Create a module object from topic payload."""
        devices = AMPIO_DEVICES_SCHEMA(payload)
        result = []
        for device in devices[ATTR_DEVICES]:
            klass = CLASS_FACTORY.get(device[ATTR_TYPE], AmpioModuleInfo)
            result.append(
                klass(
                    device[ATTR_MAC],
                    device[ATTR_USERMAC],
                    device[ATTR_TYPE],
                    device[ATTR_PCB],
                    device[ATTR_SOFTWARE],
                    device[ATTR_PROTOCOL],
                    device[ATTR_DATE_PROD],
                    device[ATTR_BI],
                    device[ATTR_BO],
                    device[ATTR_AI],
                    device[ATTR_AO],
                    device[ATTR_FLAG],
                    device[ATTR_NAME],
                )
            )
        return result

    def get_config_for_component(self, component: str) -> List:
        """Return list of entities for specific component."""
        return self.configs.get(component, [])


class MSENSModuleInfo(AmpioModuleInfo):
    """MSENS Ampio module information."""

    def update_configs(self) -> None:
        super().update_configs()

        for ampio_config in (
            AmpioTempSensorConfig.from_ampio_device(
                self, ItemName(base64encode("T:Temperature"))
            ),
            AmpioHumiditySensorConfig.from_ampio_device(
                self, ItemName(base64encode("HU:Humidity"))
            ),
            AmpioPressureSensorConfig.from_ampio_device(
                self, ItemName(base64encode("OS:Pressure"))
            ),
            AmpioNoiseSensorConfig.from_ampio_device(
                self, ItemName(base64encode("SS:Noise"))
            ),
            AmpioIlluminanceSensorConfig.from_ampio_device(
                self, ItemName(base64encode("I:Illuminance"))
            ),
            AmpioAirqualitySensorConfig.from_ampio_device(
                self, ItemName(base64encode("Air Quality"))
            ),
        ):
            if ampio_config:
                self.configs["sensor"].append(ampio_config.config)


class MCONModuleInfo(AmpioModuleInfo):
    """MCON Ampio module information."""

    def update_configs(self) -> None:
        """Update config."""
        super().update_configs()
        if self.software % 100 == 1:  # INTEGRA
            for index, item in self.names.get(ItemTypes.BinaryInput254, {}).items():
                data = AmpioBinarySensorExtendedConfig.from_ampio_device(
                    self, item, index + 1
                )
                if data:
                    self.configs["binary_sensor"].append(data.config)

            for index, item in self.names.get(ItemTypes.BinaryInput509, {}).items():
                data = AmpioBinarySensorExtendedConfig.from_ampio_device(
                    self, item, index + 255
                )
                if data:
                    self.configs["binary_sensor"].append(data.config)

            for index, item in self.names.get(ItemTypes.AnalogOutput254, {}).items():
                data = AmpioSatelConfig.from_ampio_device(self, item, index + 1)
                if data:
                    self.configs["alarm_control_panel"].append(data.config)


class MLED1ModuleInfo(AmpioModuleInfo):
    """MLED-1 Ampio module information."""

    def update_configs(self) -> None:
        super().update_configs()
        for index, item in self.names.get(ItemTypes.AnalogOutput254, {}).items():
            data = AmpioDimmableLightConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["light"].append(data.config)


class MDIM8sModuleInfo(AmpioModuleInfo):
    """MDIM-8s Ampio module information."""

    def update_configs(self) -> None:
        super().update_configs()
        for index, item in self.names.get(ItemTypes.BinaryOutput254, {}).items():
            data = AmpioDimmableLightConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["light"].append(data.config)


class MOC4ModuleInfo(AmpioModuleInfo):
    """MOC-4 Ampio module information."""

    def update_configs(self) -> None:
        super().update_configs()
        for index, item in self.names.get(ItemTypes.BinaryOutput254, {}).items():
            data = AmpioDimmableLightConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["light"].append(data.config)


class MPR8sModuleInfo(AmpioModuleInfo):
    """MPR-8s Ampio module information."""

    def update_configs(self) -> None:
        super().update_configs()
        for index, item in self.names.get(ItemTypes.BinaryOutput254, {}).items():
            if item.device_class == "light":
                data = AmpioLightConfig.from_ampio_device(self, item, index + 1)
                self.configs["light"].append(data.config)
            else:
                data = AmpioSwitchConfig.from_ampio_device(self, item, index + 1)
                self.configs["switch"].append(data.config)

        for index, item in self.names.get(ItemTypes.BinaryInput254, {}).items():
            data = AmpioBinarySensorConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["binary_sensor"].append(data.config)


class MDOTModuleInfo(AmpioModuleInfo):
    """Generic MDOT Ampio module information class."""

    _BUTTONS: int

    def update_configs(self) -> None:
        """Generat module configuration."""
        super().update_configs()
        for index in range(
            self._BUTTONS
        ):  # regardles of names module has always fixed physical touch buttons
            item = self.names.get(ItemTypes.BinaryInput254, {}).get(index)
            if item is None:
                item = ItemName(base64encode(f"{self.name} Touch"))
            data = AmpioTouchSensorConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["binary_sensor"].append(data.config)


class MDOT2ModuleInfo(MDOTModuleInfo):
    """MDOT-2 Ampio module information."""

    _BUTTONS = 2


class MDOT4ModuleInfo(MDOTModuleInfo):
    """MDOT-4 Ampio module information."""

    _BUTTONS = 4


class MDOT9ModuleInfo(MDOTModuleInfo):
    """MDOT-9 Ampio module information."""

    _BUTTONS = 9


class MDOT15LCDModuleInfo(MDOTModuleInfo):
    """MDOT-15LCD Ampio module information."""

    _BUTTONS = 15


class MRGBu1ModuleInfo(AmpioModuleInfo):
    """MRGB-1u Ampio module information."""

    def update_configs(self) -> None:
        """Update module specific configuration."""
        super().update_configs()
        data = AmpioRGBLightConfig.from_ampio_device(self, None, 1)
        if data:
            self.configs["light"].append(data.config)


class MSERV3sModuleInfo(AmpioModuleInfo):
    """MSERV-3s Ampio module information."""

    def update_configs(self) -> None:
        super().update_configs()
        for index, item in self.names.get(ItemTypes.BinaryOutput254, {}).items():
            data = AmpioSwitchConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["switch"].append(data.config)

        for index, item in self.names.get(ItemTypes.BinaryInput254, {}).items():
            data = AmpioBinarySensorConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["binary_sensor"].append(data.config)


class MROL4sModuleInfo(AmpioModuleInfo):
    """MROL-4s Ampio module information."""

    def update_configs(self) -> None:
        super().update_configs()

        for index, item in self.names.get(ItemTypes.BinaryOutput254, {}).items():
            data = AmpioCoverConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["cover"].append(data.config)

        for index, item in self.names.get(ItemTypes.BinaryInput254, {}).items():
            data = AmpioBinarySensorConfig.from_ampio_device(self, item, index + 1)
            if data:
                self.configs["binary_sensor"].append(data.config)


CLASS_FACTORY = {
    44: MSENSModuleInfo,
    25: MCONModuleInfo,
    17: MLED1ModuleInfo,
    5: MDIM8sModuleInfo,
    26: MOC4ModuleInfo,
    4: MPR8sModuleInfo,
    33: MDOT2ModuleInfo,
    8: MDOT4ModuleInfo,
    11: MDOT9ModuleInfo,
    27: MDOT15LCDModuleInfo,
    12: MRGBu1ModuleInfo,
    10: MSERV3sModuleInfo,
    3: MROL4sModuleInfo,
}


@attr.s
class AmpioConfig:
    """Generic Ampio Config  class."""

    config = attr.ib(type=dict)


class AmpioTempSensorConfig(AmpioConfig):
    """Ampio Temperature Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        if not item.name:
            name = f"Temperature {ampio_device.name}"
        else:
            name = item.name
        mac = ampio_device.user_mac
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-t{index}",
            CONF_NAME: f"{mac}-t{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_UNIT_OF_MEASUREMENT: "°C",
            CONF_DEVICE_CLASS: "temperature",
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/t/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioHumiditySensorConfig(AmpioConfig):
    """Ampio Humidity Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        if ampio_device.pcb < 3:  # MSENS-1
            state_topic = f"ampio/from/{mac}/state/au32/0"
        else:
            state_topic = f"ampio/from/{mac}/state/au16l/1"
        name = f"Humidity {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-h{index}",
            CONF_NAME: f"{mac}-h{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_UNIT_OF_MEASUREMENT: "%",
            CONF_DEVICE_CLASS: "humidity",
            CONF_STATE_TOPIC: state_topic,
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioPressureSensorConfig(AmpioConfig):
    """Ampio Pressure Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        if ampio_device.pcb < 3:  # MSENS-1
            state_topic = f"ampio/from/{mac}/state/au32/1"
        else:
            state_topic = f"ampio/from/{mac}/state/au16l/6"
        name = f"Pressure {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-ps{index}",
            CONF_NAME: f"{mac}-ps{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_DEVICE_CLASS: "pressure",
            CONF_STATE_TOPIC: state_topic,
            CONF_UNIT_OF_MEASUREMENT: "hPa",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioNoiseSensorConfig(AmpioConfig):
    """Ampio Noise Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        if ampio_device.pcb < 3:  # MSENS-1
            return None
        mac = ampio_device.user_mac
        name = f"Noise {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-n{index}",
            CONF_NAME: f"{mac}-n{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_DEVICE_CLASS: "signal_strength",
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16l/3",
            CONF_UNIT_OF_MEASUREMENT: "dB",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioIlluminanceSensorConfig(AmpioConfig):
    """Ampio Illuminance Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        if ampio_device.pcb < 3:  # MSENS-1
            return None
        mac = ampio_device.user_mac
        name = f"Illuminance {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-i{index}",
            CONF_NAME: f"{mac}-i{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_DEVICE_CLASS: "illuminance",
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16l/4",
            CONF_UNIT_OF_MEASUREMENT: "lx",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioAirqualitySensorConfig(AmpioConfig):
    """Ampio AirQuality Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        if ampio_device.pcb < 3:  # MSENS-1
            return None
        name = f"Air Quality {ampio_device.name}"
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-aq{index}",
            CONF_NAME: f"{mac}-aq{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/au16l/5",
            CONF_UNIT_OF_MEASUREMENT: None,
            CONF_DEVICE: ampio_device.as_hass_device(),
        }
        return cls(config=config)


class AmpioTouchSensorConfig(AmpioConfig):
    """Ampio Binary Sensor Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac

        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-i{index}",
            CONF_NAME: f"{mac}-i{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/i/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
            CONF_DEVICE_CLASS: "opening",
        }

        return cls(config=config)


class AmpioBinarySensorExtendedConfig(AmpioConfig):
    """Ampio Binary Sensor Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-bi{index}",
            CONF_NAME: f"{mac}-bi{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/bi/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        return cls(config=config)


class AmpioBinarySensorConfig(AmpioConfig):
    """Ampio Binary Sensor Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-i{index}",
            CONF_NAME: f"{mac}-i{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/i/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        return cls(config=config)


class AmpioDimmableLightConfig(AmpioConfig):
    """Ampio Dimable Light Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-a{index}",
            CONF_NAME: f"{mac}-a{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/o/{index}",
            CONF_COMMAND_TOPIC: f"ampio/to/{mac}/o/{index}/cmd",
            CONF_BRIGHTNESS_COMMAND_TOPIC: f"ampio/to/{mac}/o/{index}/cmd",
            CONF_BRIGHTNESS_STATE_TOPIC: f"ampio/from/{mac}/state/a/{index}",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        if ampio_device.code == ModuleCodes.MLED1:
            config[CONF_ICON] = "mdi:spotlight"

        return cls(config=config)


class AmpioLightConfig(AmpioConfig):
    """Ampio Light Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-a{index}",
            CONF_NAME: f"{mac}-a{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/o/{index}",
            CONF_COMMAND_TOPIC: f"ampio/to/{mac}/o/{index}/cmd",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        return cls(config=config)


class AmpioRGBLightConfig(AmpioConfig):
    """Ampio RGB Light Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item=None, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        name = ampio_device.name or "RGBW"
        index = 1
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-rgbw{index}",
            CONF_NAME: f"{mac}-rgbw{index}",
            CONF_FRIENDLY_NAME: name,
            CONF_RGB_STATE_TOPIC: f"ampio/from/{mac}/state/rgbw/{index}",
            CONF_RGB_COMMAND_TOPIC: f"ampio/to/{mac}/rgbw/{index}/cmd",
            CONF_WHITE_VALUE_STATE_TOPIC: f"ampio/from/{mac}/state/a/4",
            CONF_WHITE_VALUE_COMMAND_TOPIC: f"ampio/to/{mac}/o/4/cmd",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        return cls(config=config)


class AmpioSwitchConfig(AmpioConfig):
    """Ampio Switch Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-bo{index}",
            CONF_NAME: f"{mac}-bo{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/o/{index}",
            CONF_COMMAND_TOPIC: f"ampio/to/{mac}/o/{index}/cmd",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        if device_class == "heat":
            config[CONF_ICON] = "mdi:radiator"

        return cls(config=config)


class AmpioFlagConfig(AmpioConfig):
    """Ampio Flag Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-f{index}",
            CONF_NAME: f"{mac}-f{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/f/{index}",
            CONF_COMMAND_TOPIC: f"ampio/to/{mac}/f/{index}/cmd",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        config[CONF_ICON] = "mdi:flag"

        return cls(config=config)


class AmpioCoverConfig(AmpioConfig):
    """Ampio Cover Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        icon = None
        device_class = item.device_class
        if device_class is None:
            device_class = "shutter"
        if device_class == "valve":
            icon = "mdi:valve"

        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-co{index}",
            CONF_NAME: f"{mac}-co{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/a/{index}",
            CONF_CLOSING_STATE_TOPIC: f"ampio/from/{mac}/state/o/{2*(index-1)+1}",
            CONF_OPENING_STATE_TOPIC: f"ampio/from/{mac}/state/o/{2*(index)}",
            CONF_COMMAND_TOPIC: f"ampio/to/{mac}/o/{index}/cmd",
            CONF_RAW_TOPIC: f"ampio/to/{mac}/raw",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class not in ["garage", "valve"]:
            config.update(
                {CONF_TILT_POSITION_TOPIC: f"ampio/from/{mac}/state/a/{6+index}",}
            )

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        if icon:
            config[CONF_ICON] = icon

        return cls(config=config)


class AmpioSatelConfig(AmpioConfig):
    """Ampio Satel Entity Configuration."""

    @classmethod
    def from_ampio_device(cls, ampio_device: AmpioModuleInfo, item: ItemName, index=1):
        """Create config from ampio device."""
        mac = ampio_device.user_mac
        device_class = item.device_class
        config = {
            CONF_UNIQUE_ID: f"ampio-{mac}-z{index}",
            CONF_NAME: f"{mac}-z{index}",
            CONF_FRIENDLY_NAME: item.name,
            CONF_STATE_TOPIC: f"ampio/from/{mac}/state/a/{index}",
            CONF_RAW_TOPIC: f"ampio/to/{mac}/raw",
            CONF_DEVICE: ampio_device.as_hass_device(),
        }

        if device_class:
            config[CONF_DEVICE_CLASS] = device_class

        return cls(config=config)
