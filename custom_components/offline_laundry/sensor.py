"""Sensors of the Offline Laundry integration."""

from datetime import datetime, timedelta
from typing import Any, override

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import OfflineLaundryConfigEntry
from .appliance import cycle_attributes
from .const import LaundryState
from .entity import LaundryEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OfflineLaundryConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    async_add_entities([LaundryStatusSensor(entry), LaundryFinishesAtSensor(entry)])


class LaundryStatusSensor(LaundryEntity, SensorEntity):
    """Main entity: state of the appliance; target of all actions."""

    _attr_name = None
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(LaundryState)

    def __init__(self, entry: OfflineLaundryConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(entry, "status")
        self._attr_translation_key = self._appliance_type

    @property
    @override
    def native_value(self) -> str:
        """Return the state."""
        return self._appliance.cycle.state

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the cycle details."""
        return cycle_attributes(self._appliance.cycle)

    async def async_start(self, duration: timedelta, load: str | None = None) -> None:
        """Start a new cycle."""
        self._appliance.start(duration, load)

    async def async_pause(self) -> None:
        """Pause the cycle."""
        self._appliance.pause()

    async def async_resume(self) -> None:
        """Resume the cycle."""
        self._appliance.resume()

    async def async_cancel(self) -> None:
        """Cancel the cycle."""
        self._appliance.cancel()

    async def async_empty(self) -> None:
        """Mark the appliance as emptied."""
        self._appliance.empty()


class LaundryFinishesAtSensor(LaundryEntity, SensorEntity):
    """When the running cycle will finish."""

    _attr_translation_key = "finishes_at"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: OfflineLaundryConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(entry, "finishes_at")

    @property
    @override
    def native_value(self) -> datetime | None:
        """Return the finish time while running."""
        return self._appliance.cycle.finishes_at
