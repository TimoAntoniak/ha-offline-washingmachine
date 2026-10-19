"""The Offline Laundry integration: timers dressed up as appliances."""

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .appliance import LaundryAppliance
from .const import CARD_FILENAME, CARD_URL_PATH, CONF_NOTIFY_TARGETS, DOMAIN
from .notify import LaundryNotifier, async_listen_notification_actions
from .services import async_setup_services

PLATFORMS = [Platform.EVENT, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type OfflineLaundryConfigEntry = ConfigEntry[LaundryAppliance]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up services, the notification listener and the dashboard card."""
    async_setup_services(hass)
    async_listen_notification_actions(hass)

    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL_PATH,
                str(Path(__file__).parent / "frontend" / CARD_FILENAME),
                cache_headers=True,
            )
        ]
    )
    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={integration.version}")
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: OfflineLaundryConfigEntry
) -> bool:
    """Set up an appliance from a config entry."""
    appliance = LaundryAppliance(hass, entry.entry_id, entry.title)
    notifier = LaundryNotifier(
        hass, entry.entry_id, appliance, entry.options.get(CONF_NOTIFY_TARGETS, [])
    )
    entry.async_on_unload(appliance.async_add_listener(notifier.async_handle))
    entry.async_on_unload(appliance.async_shutdown)
    await appliance.async_load()
    entry.runtime_data = appliance

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: OfflineLaundryConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant, entry: OfflineLaundryConfigEntry
) -> None:
    """Delete stored cycle data when the appliance is removed."""
    await LaundryAppliance(hass, entry.entry_id, entry.title).async_remove()
