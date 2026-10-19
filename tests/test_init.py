"""Tests for integration setup."""

import pytest

from custom_components.offline_laundry.const import CARD_URL_PATH, DOMAIN
from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration


@pytest.mark.usefixtures("setup")
async def test_card_is_registered_with_version(hass: HomeAssistant) -> None:
    version = (await async_get_integration(hass, DOMAIN)).version
    assert f"{CARD_URL_PATH}?v={version}" in hass.data[DATA_EXTRA_MODULE_URL].urls
