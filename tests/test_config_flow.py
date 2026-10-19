"""Tests for the config and options flow."""

import probatio
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.offline_laundry.const import (
    CONF_APPLIANCE_TYPE,
    CONF_NOTIFY_TARGETS,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import PHONE


def _default(schema: dict, key: str) -> object:
    marker = next(m for m in schema if m == key)
    return marker.default()


async def test_user_flow_preselects_all_phones(hass: HomeAssistant) -> None:
    async_mock_service(hass, "notify", PHONE)
    async_mock_service(hass, "notify", "mobile_app_tablet")
    async_mock_service(hass, "notify", "persistent_notification")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    schema = result["data_schema"].schema
    assert sorted(_default(schema, CONF_NOTIFY_TARGETS)) == [
        "mobile_app_pixel",
        "mobile_app_tablet",
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Trockner",
            CONF_APPLIANCE_TYPE: "dryer",
            CONF_NOTIFY_TARGETS: [PHONE],
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Trockner"
    assert result["data"] == {}
    assert result["options"] == {
        CONF_APPLIANCE_TYPE: "dryer",
        CONF_NOTIFY_TARGETS: [PHONE],
    }
    await hass.async_block_till_done()
    assert hass.states.get("sensor.trockner").state == "idle"


async def test_user_flow_rejects_unknown_target(hass: HomeAssistant) -> None:
    async_mock_service(hass, "notify", PHONE)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with pytest.raises(probatio.Invalid):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"name": "X", CONF_APPLIANCE_TYPE: "washer", CONF_NOTIFY_TARGETS: ["nope"]},
        )


async def test_options_flow(hass: HomeAssistant, setup) -> None:
    result = await hass.config_entries.options.async_init(setup.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_APPLIANCE_TYPE: "dryer", CONF_NOTIFY_TARGETS: []}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert setup.options == {CONF_APPLIANCE_TYPE: "dryer", CONF_NOTIFY_TARGETS: []}
    assert hass.states.get("sensor.waschmaschine").state == "idle"


async def test_user_flow_without_phones_hides_targets(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert CONF_NOTIFY_TARGETS not in result["data_schema"].schema

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Waschmaschine", CONF_APPLIANCE_TYPE: "washer"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {CONF_APPLIANCE_TYPE: "washer"}
