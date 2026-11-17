"""yBMS sensor entities for Home Assistant."""

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

DEVICE_NAME = "yBMS"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up yBMS sensor entities from a config entry."""
    domain_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = domain_data["coordinator"]
    address = domain_data["address"]

    sensors = [
        _YBMSensor(
            coordinator=coordinator,
            address=address,
            key="voltage",
            name="Total Voltage",
            unit="V",
            device_class=SensorDeviceClass.VOLTAGE,
            state_fn=lambda data: data.get("voltage_V"),
        ),
        _YBMSensor(
            coordinator=coordinator,
            address=address,
            key="current",
            name="Current",
            unit="A",
            device_class=SensorDeviceClass.CURRENT,
            state_fn=lambda data: data.get("current_A"),
        ),
        _YBMSensor(
            coordinator=coordinator,
            address=address,
            key="temperature",
            name="Temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_fn=lambda data: data.get("temperature_c"),
        ),
        _YBMSensor(
            coordinator=coordinator,
            address=address,
            key="state_of_charge",
            name="State of Charge",
            unit="%",
            device_class=SensorDeviceClass.BATTERY,
            state_fn=lambda data: data.get("state_of_charge_pct"),
        ),
        _YBMSensor(
            coordinator=coordinator,
            address=address,
            key="capacity",
            name="Capacity",
            unit="Ah",
            device_class=None,
            state_fn=lambda data: data.get("capacity_ah"),
        ),
        _YBMSensor(
            coordinator=coordinator,
            address=address,
            key="status",
            name="Status",
            unit=None,
            device_class=None,
            state_fn=lambda data: data.get("status_flags"),
        ),
    ]

    for i in range(16):
        sensors.append(
            _YBMSensor(
                coordinator=coordinator,
                address=address,
                key=f"cell_{i+1}_voltage",
                name=f"Cell {i+1}",
                unit="mV",
                device_class=SensorDeviceClass.VOLTAGE,
                state_fn=lambda data, idx=i: (
                    data.get("cell_voltages_mV")[idx]
                    if data.get("cell_voltages_mV") and idx < len(data.get("cell_voltages_mV"))
                    else None
                ),
            )
        )

    async_add_entities(sensors)


class _YBMSensor(CoordinatorEntity, SensorEntity):
    """yBMS sensor entity connected to DataUpdateCoordinator."""

    def __init__(self, coordinator, address, key, name, unit, device_class, state_fn):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._address = address
        self._key = key
        self._attr_name = f"{DEVICE_NAME} {name}"
        self._attr_unique_id = f"ybmans_{address.replace(':', '_').lower()}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._state_fn = state_fn

    @property
    def native_value(self):
        """Return the current sensor value from coordinator data."""
        if not self.coordinator.data:
            return None
        return self._state_fn(self.coordinator.data)

    @property
    def device_info(self):
        """Group all 22 sensors into one unified yBMS device."""
        return {
            "identifiers": {(DOMAIN, self._address)},
            "name": DEVICE_NAME,
            "manufacturer": "Chi-Trip",
            "model": "yBMS v1.37 16S",
        }
