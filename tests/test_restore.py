"""Tests for restoring a cycle after a restart."""

from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.util import dt as dt_util

from .conftest import STATUS


def _stored(**cycle: Any) -> dict[str, Any]:
    return {
        "version": 1,
        "minor_version": 1,
        "key": "offline_laundry.washer1",
        "data": {
            "state": "running",
            "load": "Handtücher",
            "duration": 3600.0,
            "finishes_at": None,
            "remaining": None,
            **cycle,
        },
    }


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_restore_running(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    notify_calls: list[ServiceCall],
) -> None:
    end = dt_util.utcnow() + timedelta(minutes=10)
    hass_storage["offline_laundry.washer1"] = _stored(finishes_at=end.isoformat())
    await _setup(hass, entry)

    state = hass.states.get(STATUS)
    assert state.state == "running"
    assert state.attributes["finishes_at"] == end.isoformat()

    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "finished"
    assert notify_calls[-1].data["message"] == "Handtücher is ready."


async def test_restore_finished_while_down(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    entry: MockConfigEntry,
    notify_calls: list[ServiceCall],
) -> None:
    end = dt_util.utcnow() - timedelta(minutes=5)
    hass_storage["offline_laundry.washer1"] = _stored(finishes_at=end.isoformat())
    await _setup(hass, entry)

    assert hass.states.get(STATUS).state == "finished"
    assert notify_calls[-1].data["data"]["tag"] == "offline_laundry_washer1"


async def test_restore_paused(
    hass: HomeAssistant, hass_storage: dict[str, Any], entry: MockConfigEntry
) -> None:
    hass_storage["offline_laundry.washer1"] = _stored(state="paused", remaining=754.0)
    await _setup(hass, entry)

    state = hass.states.get(STATUS)
    assert state.state == "paused"
    assert state.attributes["remaining"] == "0:12:34"


async def test_invalid_storage_is_discarded(
    hass: HomeAssistant, hass_storage: dict[str, Any], entry: MockConfigEntry
) -> None:
    hass_storage["offline_laundry.washer1"] = _stored(state="spinning")
    await _setup(hass, entry)

    assert hass.states.get(STATUS).state == "idle"


async def test_remove_entry_deletes_storage(
    hass: HomeAssistant, hass_storage: dict[str, Any], entry: MockConfigEntry
) -> None:
    hass_storage["offline_laundry.washer1"] = _stored(state="paused", remaining=60.0)
    await _setup(hass, entry)

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "offline_laundry.washer1" not in hass_storage
