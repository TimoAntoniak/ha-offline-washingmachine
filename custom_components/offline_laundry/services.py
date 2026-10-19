"""Actions of the Offline Laundry integration."""

import probatio

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, service

from .const import (
    ATTR_DURATION,
    ATTR_LOAD,
    DOMAIN,
    SERVICE_CANCEL,
    SERVICE_EMPTY,
    SERVICE_PAUSE,
    SERVICE_RESUME,
    SERVICE_START,
)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register entity actions; they are handled by the status sensor."""
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_START,
        entity_domain=SENSOR_DOMAIN,
        entity_device_classes=[SensorDeviceClass.ENUM],
        schema={
            probatio.Required(ATTR_DURATION): cv.positive_time_period,
            probatio.Optional(ATTR_LOAD): cv.string,
        },
        func="async_start",
    )
    for name in (SERVICE_PAUSE, SERVICE_RESUME, SERVICE_CANCEL, SERVICE_EMPTY):
        service.async_register_platform_entity_service(
            hass,
            DOMAIN,
            name,
            entity_domain=SENSOR_DOMAIN,
            entity_device_classes=[SensorDeviceClass.ENUM],
            schema=None,
            func=f"async_{name}",
        )
