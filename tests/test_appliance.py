"""Tests for the cycle state machine, driven through the actions."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.offline_laundry.const import DOMAIN
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util

from .conftest import CYCLE, FINISHES_AT, STATUS


async def _call(hass: HomeAssistant, action: str, **data: object) -> None:
    await hass.services.async_call(
        DOMAIN, action, {"entity_id": STATUS, **data}, blocking=True
    )


@pytest.mark.usefixtures("setup")
async def test_full_cycle(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    notify_calls: list[ServiceCall],
) -> None:
    assert hass.states.get(STATUS).state == "idle"
    assert hass.states.get(FINISHES_AT).state == "unknown"

    await _call(hass, "start", duration={"minutes": 90}, load=" Buntwäsche 40° ")
    end = dt_util.utcnow() + timedelta(minutes=90)
    state = hass.states.get(STATUS)
    assert state.state == "running"
    assert state.attributes["load"] == "Buntwäsche 40°"
    assert state.attributes["duration"] == "1:30:00"
    assert state.attributes["finishes_at"] == end.isoformat()
    assert hass.states.get(FINISHES_AT).state == end.isoformat()
    assert hass.states.get(CYCLE).attributes["event_type"] == "started"

    freezer.tick(timedelta(minutes=89))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "running"

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    state = hass.states.get(STATUS)
    assert state.state == "finished"
    assert state.attributes["load"] == "Buntwäsche 40°"
    assert state.attributes["finishes_at"] is None
    assert hass.states.get(CYCLE).attributes["event_type"] == "finished"

    finished = notify_calls[-1].data
    assert finished["title"] == "Waschmaschine is done"
    assert finished["message"] == "Buntwäsche 40° is ready."
    assert finished["data"]["tag"] == "offline_laundry_washer1"
    assert finished["data"]["actions"][0]["action"] == "OFFLINE_LAUNDRY_EMPTIED_washer1"

    await _call(hass, "empty")
    assert hass.states.get(STATUS).state == "idle"
    assert hass.states.get(STATUS).attributes["load"] is None
    assert hass.states.get(CYCLE).attributes["event_type"] == "emptied"
    assert notify_calls[-1].data == {
        "message": "clear_notification",
        "data": {"tag": "offline_laundry_washer1"},
    }


@pytest.mark.usefixtures("setup")
async def test_pause_resume_shifts_end(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _call(hass, "start", duration={"minutes": 60})
    freezer.tick(timedelta(minutes=20))

    await _call(hass, "pause")
    state = hass.states.get(STATUS)
    assert state.state == "paused"
    assert state.attributes["remaining"] == "0:40:00"
    assert state.attributes["finishes_at"] is None
    assert hass.states.get(FINISHES_AT).state == "unknown"

    freezer.tick(timedelta(hours=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "paused"

    await _call(hass, "resume")
    end = dt_util.utcnow() + timedelta(minutes=40)
    assert hass.states.get(STATUS).attributes["finishes_at"] == end.isoformat()

    freezer.tick(timedelta(minutes=40))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "finished"


@pytest.mark.usefixtures("setup")
async def test_cancel(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    notify_calls: list[ServiceCall],
) -> None:
    await _call(hass, "start", duration={"minutes": 30})
    await _call(hass, "cancel")
    assert hass.states.get(STATUS).state == "idle"
    assert hass.states.get(CYCLE).attributes["event_type"] == "cancelled"

    freezer.tick(timedelta(minutes=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "idle"
    assert all(call.data["message"] == "clear_notification" for call in notify_calls)


@pytest.mark.usefixtures("setup")
@pytest.mark.parametrize(
    ("action", "key"),
    [
        ("pause", "not_running"),
        ("resume", "not_paused"),
        ("cancel", "not_active"),
        ("empty", "not_finished"),
    ],
)
async def test_invalid_transitions_from_idle(
    hass: HomeAssistant, action: str, key: str
) -> None:
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, action)
    assert err.value.translation_key == key


@pytest.mark.usefixtures("setup")
async def test_start_requires_idle(hass: HomeAssistant) -> None:
    await _call(hass, "start", duration={"minutes": 30})
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "start", duration={"minutes": 30})
    assert err.value.translation_key == "not_idle"


async def test_unload_cancels_timer(
    hass: HomeAssistant, setup: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    await _call(hass, "start", duration={"minutes": 30})
    assert await hass.config_entries.async_unload(setup.entry_id)
    freezer.tick(timedelta(minutes=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "unavailable"
