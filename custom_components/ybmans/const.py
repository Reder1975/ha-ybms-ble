"""Constants for the yBMS Home Assistant integration."""

DOMAIN = "ybmans"

# UUIDs for yBMS BLE service and characteristics
SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
CHAR_WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
CHAR_NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# Configuration keys
CONF_ADDRESS = "address"
CONF_NAME = "name"

# Defaults
DEFAULT_NAME = "yBMS"

# Diagnostic
DEBUG_KEY = "debug"

# Status flag bit definitions (importiert von __init__.py, sensor.py)
STATUS_FLAGS = {
    0: "overcharge_flag",
    1: "over_discharge_flag",
    2: "under_voltage_flag",
    3: "cell_balance_flag",
    4: "over_current_flag",
    5: "under_current_flag",
    6: "temp_high_flag",
    7: "temp_low_flag",
    8: "fault_flag",
    9: "wakeup_flag",
    10: "ready_flag",
    11: "charging_flag",
    12: "balancing_enabled_flag",
    13: "fault_reset_flag",
    14: "low_temp_protection_flag",
    15: "high_temp_protection_flag",
}
