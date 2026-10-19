"""Push notifications through the Companion app's notify actions.

Legacy ``notify.mobile_app_*`` actions are used on purpose: notify entities
cannot carry the ``data`` payload needed for the tag and the action button.
"""

import logging
from typing import Any

from homeassistant.components.notify import DOMAIN as NOTIFY_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import slugify

from .appliance import LaundryAppliance
from .const import DOMAIN, NOTIFICATION_ACTION_EMPTIED, LaundryEvent, LaundryState

_LOGGER = logging.getLogger(__name__)

MOBILE_APP_DOMAIN = "mobile_app"
MOBILE_APP_PREFIX = f"{MOBILE_APP_DOMAIN}_"
EVENT_NOTIFICATION_ACTION = "mobile_app_notification_action"


@callback
def async_mobile_app_targets(hass: HomeAssistant) -> dict[str, str]:
    """Return available Companion app notify actions mapped to device names."""
    titles = {
        slugify(f"{MOBILE_APP_PREFIX}{entry.data['device_name']}"): entry.title
        for entry in hass.config_entries.async_entries(MOBILE_APP_DOMAIN)
        if "device_name" in entry.data
    }
    return {
        service: titles.get(service, service)
        for service in hass.services.async_services_for_domain(NOTIFY_DOMAIN)
        if service.startswith(MOBILE_APP_PREFIX)
    }


class LaundryNotifier:
    """Notify phones when a cycle finishes and clear the notification later."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        appliance: LaundryAppliance,
        targets: list[str],
    ) -> None:
        """Initialize the notifier."""
        self._hass = hass
        self._entry_id = entry_id
        self._appliance = appliance
        self._targets = targets
        self._tag = f"{DOMAIN}_{entry_id}"

    @callback
    def async_handle(self, event: LaundryEvent) -> None:
        """React to appliance transitions."""
        if not self._targets:
            return
        if event is LaundryEvent.FINISHED:
            self._hass.async_create_task(self._async_send_finished(), eager_start=True)
        elif event in (
            LaundryEvent.EMPTIED,
            LaundryEvent.CANCELLED,
            LaundryEvent.STARTED,
        ):
            self._hass.async_create_task(
                self._async_send(
                    {"message": "clear_notification", "data": {"tag": self._tag}}
                ),
                eager_start=True,
            )

    async def _async_send_finished(self) -> None:
        strings = await async_get_translations(
            self._hass, self._hass.config.language, "common", [DOMAIN]
        )
        prefix = f"component.{DOMAIN}.common."
        load = self._appliance.cycle.load
        message_key = "notification_message_load" if load else "notification_message"
        await self._async_send(
            {
                "title": strings[f"{prefix}notification_title"].format(
                    name=self._appliance.name
                ),
                "message": strings[f"{prefix}{message_key}"].format(load=load),
                "data": {
                    "tag": self._tag,
                    "actions": [
                        {
                            "action": f"{NOTIFICATION_ACTION_EMPTIED}{self._entry_id}",
                            "title": strings[f"{prefix}notification_action_emptied"],
                        }
                    ],
                },
            }
        )

    async def _async_send(self, data: dict[str, Any]) -> None:
        for target in self._targets:
            if not self._hass.services.has_service(NOTIFY_DOMAIN, target):
                _LOGGER.warning("Notify action %s.%s not found", NOTIFY_DOMAIN, target)
                continue
            try:
                await self._hass.services.async_call(
                    NOTIFY_DOMAIN, target, data, blocking=True
                )
            except HomeAssistantError as err:
                _LOGGER.warning("Could not notify %s: %s", target, err)


@callback
def async_listen_notification_actions(hass: HomeAssistant) -> None:
    """Mark an appliance as emptied when its notification button is tapped."""

    @callback
    def _handle(event: Event) -> None:
        action: str = event.data.get("action", "")
        if not action.startswith(NOTIFICATION_ACTION_EMPTIED):
            return
        entry = hass.config_entries.async_get_entry(
            action.removeprefix(NOTIFICATION_ACTION_EMPTIED)
        )
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
        ):
            return
        appliance: LaundryAppliance = entry.runtime_data
        if appliance.cycle.state is LaundryState.FINISHED:
            appliance.empty()

    hass.bus.async_listen(EVENT_NOTIFICATION_ACTION, _handle)
