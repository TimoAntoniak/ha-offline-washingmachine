"""Tests for phone notifications."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.offline_laundry.const import (
    CONF_APPLIANCE_TYPE,
    CONF_NOTIFY_TARGETS,
    DOMAIN,
)
from homeassistant.core import HomeAssistant, ServiceCall

from .conftest import STATUS


async def _run_to_finish(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    await hass.services.async_call(
        DOMAIN, "start", {"entity_id": STATUS, "duration": "00:01:00"}, blocking=True
    )
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("setup")
async def test_finished_without_load_name(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    notify_calls: list[ServiceCall],
) -> None:
    await _run_to_finish(hass, freezer)
    assert notify_calls[-1].data["message"] == "The laundry is ready."


@pytest.mark.usefixtures("setup")
async def test_notification_action_empties(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    notify_calls: list[ServiceCall],
) -> None:
    await _run_to_finish(hass, freezer)

    hass.bus.async_fire("mobile_app_notification_action", {"action": "OTHER"})
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "finished"

    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": "OFFLINE_LAUNDRY_EMPTIED_washer1"},
    )
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "idle"
    assert notify_calls[-1].data["message"] == "clear_notification"


@pytest.mark.usefixtures("setup")
async def test_stale_notification_action_is_ignored(hass: HomeAssistant) -> None:
    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": "OFFLINE_LAUNDRY_EMPTIED_washer1"},
    )
    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": "OFFLINE_LAUNDRY_EMPTIED_unknown"},
    )
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "idle"


async def test_no_targets_no_notifications(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    notify_calls: list[ServiceCall],
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Waschmaschine",
        options={CONF_APPLIANCE_TYPE: "washer", CONF_NOTIFY_TARGETS: []},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await _run_to_finish(hass, freezer)
    assert hass.states.get(STATUS).state == "finished"
    assert notify_calls == []


async def test_missing_target_is_skipped(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Waschmaschine",
        options={
            CONF_APPLIANCE_TYPE: "washer",
            CONF_NOTIFY_TARGETS: ["mobile_app_old"],
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await _run_to_finish(hass, freezer)
    assert hass.states.get(STATUS).state == "finished"
    assert "notify.mobile_app_old not found" in caplog.text
