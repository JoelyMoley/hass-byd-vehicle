"""The BYD vehicle integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import BYDVehicleAPI
from .coordinator import BYDDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "byd_vehicle"
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.CLIMATE,
    Platform.LOCK,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BYD vehicle from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API and coordinator
    api = BYDVehicleAPI(
        username=entry.data["username"],
        password=entry.data["password"],
        country=entry.data.get("country", "United Kingdom"),
    )

    coordinator = BYDDataUpdateCoordinator(
        hass=hass,
        api=api,
        entry=entry,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
