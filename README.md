# yBMS BLE Battery Monitor for Home Assistant

[![HACS Custom](https://shields.io)](https://github.com)
[![Home Assistant](https://shields.io)](https://home-assistant.io)

Custom Home Assistant integration for **16S LiFePO4 / Li-Ion battery packs** using the **yBMS / Chi-Trip / HanderStar** Bluetooth Low Energy (BLE) BMS (Android App *yBMS v1.37*).  
Designed to work seamlessly via **ESPHome Bluetooth Proxies** as well as local Home Assistant Bluetooth adapters.

---

## Features & Exposed Entities (22 Sensors)

All entities are grouped under a single unified Home Assistant device (**Chi-Trip yBMS v1.37 16S**) with `SensorStateClass.MEASUREMENT` enabled for long-term statistics and energy dashboards:

- **Total Voltage** (`V`) – Pack voltage (`0.01 V` resolution)
- **Current** (`A`) – Signed charge/discharge current (`0.01 A` resolution)
- **Temperature** (`°C`) – BMS / cell temperature sensor
- **State of Charge** (`%`) – Remaining battery percentage (`0–100 %`)
- **Capacity** (`Ah`) – Remaining capacity in Ampere-hours (`0.01 Ah` resolution)
- **Status** – Health & cell balance summary (e.g., `OK (SOH 100%, Drift 51 mV)`)
- **Cell 1 – Cell 16** (`mV`) – Individual cell voltages for all 16 cells

---

## Installation

### Option 1: Via HACS (Recommended)

1. Open **HACS** in your Home Assistant instance.
2. Click the **three dots (`⋮`)** in the top right corner and select **Custom repositories**.
3. Paste the URL of this GitHub repository and select **Integration** as the category.
4. Click **Add**, search for **yBMS BLE Battery Monitor**, and click **Download**.
5. Restart Home Assistant (**Settings -> System -> Restart**).

### Option 2: Manual Installation

1. Copy the `custom_components/ybmans` folder into your Home Assistant `/config/custom_components/` directory.
2. Restart Home Assistant.

---

## Configuration

1. Make sure the **yBMS smartphone app is completely closed** (the BMS only accepts one active BLE connection at a time).
2. Go to **Settings -> Devices & Services -> Add Integration**.
3. Search for **yBMS** and enter your battery's **Bluetooth MAC address** (e.g., `AA:BB:CC:DD:EE:FF`).
4. The integration polls the BMS every **90 seconds** so passive BLE devices (such as Victron SmartSolar) sharing the same ESPHome Bluetooth Proxy continue operating smoothly.

---

## Reverse-Engineered BLE & Modbus RTU Register Map

This BMS uses the **Nordic UART Service (`6e400001-b5a3-f393-e0a9-e50e24dcca9e`)** (`Write`: `6e400002-...`, `Notify`: `6e400003-...`) tunneled with standard **Modbus RTU Function Code `0x03` (Read Holding Registers)** at Slave ID `0x01`:

| Register Block | Offset | Length | Description | Scaling |
| :--- | :--- | :--- | :--- | :--- |
| **`0xD000` – `0xD00F`** | `0..15` | 16 × `uint16` | Cell 1 to Cell 16 voltages | `1 mV` |
| **`0xD020`** | `0` | `uint16` | Highest cell voltage | `1 mV` |
| **`0xD021`** | `1` | `uint16` | Lowest cell voltage | `1 mV` |
| **`0xD022`** | `2` | `uint16` | Highest cell index | `1..16` |
| **`0xD023`** | `3` | `uint16` | Lowest cell index | `1..16` |
| **`0xD024`** | `4` | `uint16` | Cell voltage drift (delta) | `1 mV` |
| **`0xD025`** | `5` | `uint16` | Total pack voltage | `0.01 V` |
| **`0xD026`** | `6` | `uint16` | Temperature sensor 1 | `(raw - 273.15) / 10` (`°C`) |
| **`0xD027`** | `7` | `uint16` | Temperature sensor 2 | `(raw - 273.15) / 10` (`°C`) |
| **`0xD033`** | `3` | `int16` | Pack current (signed) | `0.01 A` |
| **`0xD034`** | `4` | `uint16` | State of Charge (SOC) | `1 %` |
| **`0xD035`** | `5` | `uint16` | State of Health (SOH) | `1 %` |
| **`0xD036`** | `6` | `uint16` | Remaining capacity | `0.01 Ah` |
| **`0xD037`** | `7` | `uint16` | Nominal pack capacity | `0.01 Ah` |
| **`0xD038`** | `8` | `uint16` | Full charge capacity | `0.01 Ah` |

---

## Disclaimer

This is an unofficial, community-developed integration and is not affiliated with Chi-Trip or HanderStar. Use at your own risk.
