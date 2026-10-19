"""Config flow for the Offline Laundry integration."""

from typing import Any, override

import probatio

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import CONF_APPLIANCE_TYPE, CONF_NOTIFY_TARGETS, DOMAIN, ApplianceType
from .notify import async_mobile_app_targets


def _options_schema(hass: HomeAssistant) -> probatio.Schema:
    schema: dict[probatio.Marker, Any] = {
        probatio.Required(
            CONF_APPLIANCE_TYPE, default=ApplianceType.WASHER
        ): SelectSelector(
            SelectSelectorConfig(
                options=list(ApplianceType),
                mode=SelectSelectorMode.LIST,
                translation_key=CONF_APPLIANCE_TYPE,
            )
        )
    }
    # Phones are preselected; without the Companion app there is nothing to offer.
    if targets := async_mobile_app_targets(hass):
        schema[probatio.Optional(CONF_NOTIFY_TARGETS, default=list(targets))] = (
            SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=service, label=label)
                        for service, label in targets.items()
                    ],
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            )
        )
    return probatio.Schema(schema)


class OfflineLaundryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create an appliance."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            name = user_input.pop(CONF_NAME)
            return self.async_create_entry(title=name, data={}, options=user_input)

        schema = probatio.Schema({probatio.Required(CONF_NAME): TextSelector()}).extend(
            _options_schema(self.hass).schema
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> OfflineLaundryOptionsFlow:
        """Return the options flow."""
        return OfflineLaundryOptionsFlow()


class OfflineLaundryOptionsFlow(OptionsFlowWithReload):
    """Change appliance type and notification targets."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        available = async_mobile_app_targets(self.hass)
        current = {
            **self.config_entry.options,
            CONF_NOTIFY_TARGETS: [
                target
                for target in self.config_entry.options.get(CONF_NOTIFY_TARGETS, [])
                if target in available
            ],
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(self.hass), current
            ),
        )
