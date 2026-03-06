"""Binary sensors for BYD vehicle."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .coordinator import BYDDataUpdateCoordinator


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up binary sensor platform."""
    if discovery_info is None:
        return

    coordinator: BYDDataUpdateCoordinator = discovery_info["coordinator"]
    byd_vehicle = discovery_info["vin"]

    entities: list[BinarySensorEntity] = []

    # Add existing BYD vehicle binary sensors
    for sensor_key in coordinator.data.get(byd_vehicle, {}):
        if sensor_key in BYDVehicleBinarySensor.SENSOR_TYPES:
            entities.append(
                BYDVehicleBinarySensor(
                    coordinator=coordinator,
                    vin=byd_vehicle,
                    sensor_type=sensor_key,
                )
            )

    # Add Zaptec plug sensor
    entities.append(BYDZaptecPlugSensor(hass))

    async_add_entities(entities)


class BYDVehicleBinarySensor(BinarySensorEntity):
    """Representation of BYD vehicle binary sensor."""

    SENSOR_TYPES: dict[str, tuple[BinarySensorDeviceClass, str]] = {
        "locked": (BinarySensorDeviceClass.LOCK, "Locked"),
        "doors_locked": (BinarySensorDeviceClass.LOCK, "Doors Locked"),
        "car_locked": (BinarySensorDeviceClass.LOCK, "Car Locked"),
        # Add other binary sensors as needed
    }

    def __init__(
        self,
        coordinator: BYDDataUpdateCoordinator,
        vin: str,
        sensor_type: str,
    ) -> None:
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self.vin = vin
        self.sensor_type = sensor_type

        device_class, name = self.SENSOR_TYPES[sensor_type]
        self._attr_device_class = device_class
        self._attr_name = name
        self._attr_unique_id = f"{vin}_{sensor_type}"

    @property
    def is_on(self) -> bool:
        """Return True if binary sensor is on."""
        return self.coordinator.data.get(self.vin, {}).get(self.sensor_type, False)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class BYDZaptecPlugSensor(BinarySensorEntity):
    """Binary sensor for BYD Sealion 7 plug status via Zaptec charger mode."""

    _attr_unique_id = "byd_sealion_7_plug"
    _attr_name = "BYD Sealion 7 Plug"
    _attr_device_class = BinarySensorDeviceClass.PLUG
    _attr_icon = "mdi:power-plug"

    # Source sensor for charger mode
    _source_sensor = "sensor.eleanor_zaptec_charger_mode"

    # State that indicates the charger is NOT plugged in
    _unplugged_state = "Disconnected"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the binary sensor."""
        self.hass = hass
        self._attr_is_on = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to state changes of the Zaptec charger mode sensor."""
        await super().async_added_to_hass()

        # Set initial state
        self._update_state()

        # Subscribe to state changes
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_sensor],
                self._on_sensor_state_changed,
            )
        )

    @callback
    def _on_sensor_state_changed(self, event) -> None:
        """Handle sensor state changes."""
        self._update_state()
        self.async_write_ha_state()

    @callback
    def _update_state(self) -> None:
        """Update the binary sensor state based on Zaptec charger mode."""
        state = self.hass.states.get(self._source_sensor)

        if state is None:
            # Sensor doesn't exist
            self._attr_is_on = None
            self._attr_available = False
        elif state.state in (STATE_UNKNOWN, "unknown"):
            # Unknown state - we don't know if it's plugged in
            self._attr_is_on = None
            self._attr_available = False
        elif state.state == self._unplugged_state:
            # Explicitly disconnected
            self._attr_is_on = False
            self._attr_available = True
        else:
            # Any other state = plugged in
            # Examples: "Connected", "Charging", "Ready", etc.
            self._attr_is_on = True
            self._attr_available = True

    @property
    def should_poll(self) -> bool:
        """No polling needed, we track state changes."""
        return False
