"""Fixtures for Offline Laundry tests."""

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.offline_laundry.const import (
    CONF_APPLIANCE_TYPE,
    CONF_NOTIFY_TARGETS,
    DOMAIN,
)
from homeassistant.core import HomeAssistant, ServiceCall

STATUS = "sensor.waschmaschine"
FINISHES_AT = "sensor.waschmaschine_finishes_at"
CYCLE = "event.waschmaschine_cycle"
PHONE = "mobile_app_pixel"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in all tests."""


@pytest.fixture(autouse=True)
def whole_second(freezer: FrozenDateTimeFactory) -> None:
    """Start on a whole second; timestamp sensors drop microseconds."""
    freezer.move_to("2026-10-19T08:00:00+00:00")


@pytest.fixture
def entry() -> MockConfigEntry:
    """Return a washer config entry notifying one phone."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Waschmaschine",
        options={CONF_APPLIANCE_TYPE: "washer", CONF_NOTIFY_TARGETS: [PHONE]},
        entry_id="washer1",
    )


@pytest.fixture
def notify_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Capture calls to the phone's notify action."""
    return async_mock_service(hass, "notify", PHONE)


@pytest.fixture
async def setup(
    hass: HomeAssistant, entry: MockConfigEntry, notify_calls: list[ServiceCall]
) -> MockConfigEntry:
    """Set up the integration."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
