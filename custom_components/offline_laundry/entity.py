"""Base entity for the Offline Laundry integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .appliance import LaundryAppliance
from .const import CONF_APPLIANCE_TYPE, DOMAIN, ApplianceType, LaundryEvent


class LaundryEntity(Entity):
    """Entity bound to one appliance, updated on every transition."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry[LaundryAppliance], key: str) -> None:
        """Initialize the entity."""
        self._appliance = entry.runtime_data
        self._appliance_type = ApplianceType(
            entry.options.get(CONF_APPLIANCE_TYPE, ApplianceType.WASHER)
        )
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to appliance updates."""
        self.async_on_remove(self._appliance.async_add_listener(self._handle_event))

    @callback
    def _handle_event(self, event: LaundryEvent) -> None:
        self.async_write_ha_state()
