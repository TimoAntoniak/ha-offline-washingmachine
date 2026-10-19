"""Event entity of the Offline Laundry integration."""

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import OfflineLaundryConfigEntry
from .const import ATTR_LOAD, LaundryEvent
from .entity import LaundryEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OfflineLaundryConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the event entity."""
    async_add_entities([LaundryCycleEvent(entry)])


class LaundryCycleEvent(LaundryEntity, EventEntity):
    """Fires on every transition, for automations."""

    _attr_translation_key = "cycle"
    _attr_event_types = list(LaundryEvent)

    def __init__(self, entry: OfflineLaundryConfigEntry) -> None:
        """Initialize the event entity."""
        super().__init__(entry, "cycle")

    @callback
    def _handle_event(self, event: LaundryEvent) -> None:
        self._trigger_event(event, {ATTR_LOAD: self._appliance.cycle.load})
        self.async_write_ha_state()
