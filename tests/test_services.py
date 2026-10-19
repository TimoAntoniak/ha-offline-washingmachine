"""Tests for action schemas."""

import probatio
import pytest

from custom_components.offline_laundry.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceNotSupported, ServiceValidationError

from .conftest import FINISHES_AT, STATUS


@pytest.mark.usefixtures("setup")
@pytest.mark.parametrize("data", [{}, {"duration": "-1:00"}, {"duration": "soon"}])
async def test_start_rejects_invalid_duration(
    hass: HomeAssistant, data: dict[str, str]
) -> None:
    with pytest.raises(probatio.Invalid):
        await hass.services.async_call(
            DOMAIN, "start", {"entity_id": STATUS, **data}, blocking=True
        )


@pytest.mark.usefixtures("setup")
async def test_start_rejects_zero_duration(hass: HomeAssistant) -> None:
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            "start",
            {"entity_id": STATUS, "duration": "00:00:00"},
            blocking=True,
        )
    assert err.value.translation_key == "invalid_duration"


@pytest.mark.usefixtures("setup")
async def test_start_accepts_string_duration(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        DOMAIN, "start", {"entity_id": STATUS, "duration": "01:15:00"}, blocking=True
    )
    assert hass.states.get(STATUS).attributes["duration"] == "1:15:00"


@pytest.mark.usefixtures("setup")
async def test_actions_only_target_status_sensor(hass: HomeAssistant) -> None:
    with pytest.raises(ServiceNotSupported):
        await hass.services.async_call(
            DOMAIN,
            "start",
            {"entity_id": FINISHES_AT, "duration": "01:00:00"},
            blocking=True,
        )
    assert hass.states.get(STATUS).state == "idle"
