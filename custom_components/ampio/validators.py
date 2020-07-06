"""Data validators."""
from typing import Any, Union, TypeVar, List

import voluptuous as vol


ATTR_MAC = "mac"
ATTR_USERMAC = "user_mac"
ATTR_TYPE = "typ"
ATTR_PCB = "pcb"
ATTR_SOFTWARE = "soft_ver"
ATTR_PROTOCOL = "protocol"
ATTR_BI = "bi"
ATTR_BO = "bo"
ATTR_AI = "ai"
ATTR_AO = "ao"
ATTR_FLAG = "f"
ATTR_NAME = "name"
ATTR_DEVICES = "devices"
ATTR_DEVICE = "device"
ATTR_DATE_PROD = "date_prod"
ATTR_T = "t"
ATTR_N = "n"
ATTR_D = "d"
ATTR_S = "s"

T = TypeVar("T")


def string(value: Any) -> str:
    """Coerce value to string, except for None."""
    if value is None:
        raise vol.Invalid("string value is None")
    if isinstance(value, (list, dict)):
        raise vol.Invalid("value should be a string")

    return str(value)


def ensure_list(value: Union[T, List[T], None]) -> List[T]:
    """Wrap value in list if it is not one."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


AMPIO_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): string,
        vol.Required(ATTR_USERMAC): string,
        vol.Required(ATTR_TYPE): vol.Coerce(int),
        vol.Required(ATTR_PCB): vol.Coerce(int),
        vol.Required(ATTR_SOFTWARE): vol.Coerce(int),
        vol.Required(ATTR_PROTOCOL): vol.Coerce(int),
        vol.Required(ATTR_DATE_PROD): vol.Coerce(int),
        vol.Required(ATTR_BI): vol.Coerce(int),
        vol.Required(ATTR_BO): vol.Coerce(int),
        vol.Required(ATTR_AI): vol.Coerce(int),
        vol.Required(ATTR_AO): vol.Coerce(int),
        vol.Required(ATTR_FLAG): vol.Coerce(int),
        vol.Required(ATTR_NAME): string,
    }
)

AMPIO_DEVICES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICES): vol.All(
            ensure_list,
            # pylint: disable=unnecessary-lambda
            [lambda value: AMPIO_DEVICE_SCHEMA(value)],
        ),
    }
)

AMPIO_DESCRIPTION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_T): vol.Coerce(int),
        vol.Required(ATTR_N): vol.Coerce(int),
        vol.Required(ATTR_D): string,
    }
)

AMPIO_DESCRIPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_S): vol.Coerce(int),
        vol.Optional(ATTR_D, default=[]): vol.All(
            ensure_list,
            # pylint: disable=unnecessary-lambda
            [lambda value: AMPIO_DESCRIPTION_SCHEMA(value)],
        ),
    }
)
