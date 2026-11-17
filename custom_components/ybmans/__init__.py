"""Support for yBMS BLE battery monitor (Bluetooth-proxy)."""

import struct
import asyncio
import logging
from datetime import timedelta
import bleak
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    CHAR_WRITE_UUID,
    CHAR_NOTIFY_UUID,
    CONF_ADDRESS,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_NAME = "yBMS"
DEFAULT_NAME = "yBMS"


def _find_characteristics(client):
    """Find matching write and notify/indicate characteristics automatically."""
    all_chars = {}
    for service in client.services:
        for char in service.characteristics:
            all_chars[char.uuid.lower()] = char

    notify_uuid = CHAR_NOTIFY_UUID.lower() if CHAR_NOTIFY_UUID.lower() in all_chars else None
    write_uuid = CHAR_WRITE_UUID.lower() if CHAR_WRITE_UUID.lower() in all_chars else None

    if not notify_uuid:
        for uuid, char in all_chars.items():
            if "notify" in char.properties or "indicate" in char.properties:
                notify_uuid = uuid
                break

    if not write_uuid:
        for uuid, char in all_chars.items():
            if "write" in char.properties or "write-without-response" in char.properties:
                write_uuid = uuid
                break

    return notify_uuid, write_uuid


def _modbus_read(slave: int, start_addr: int, count: int) -> bytes:
    """Build a Modbus RTU Read Holding Registers (0x03) frame with CRC-16."""
    frame = bytearray([
        slave,
        0x03,
        (start_addr >> 8) & 0xFF,
        start_addr & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF,
    ])
    crc = 0xFFFF
    for b in frame:
        crc ^= b
        for _ in range(8):
            crc = ((crc >> 1) ^ 0xA001) if (crc & 1) else (crc >> 1)
    frame.extend([crc & 0xFF, (crc >> 8) & 0xFF])
    return bytes(frame)


async def _read_register_block(client, write_uuid: str, rx_buf: bytearray, packet_done: asyncio.Event, start_addr: int, count: int) -> tuple:
    """Read `count` 16-bit holding registers starting at `start_addr` with retry."""
    frame = _modbus_read(0x01, start_addr, count)
    last_err = None
    for attempt in range(2):
        rx_buf.clear()
        packet_done.clear()
        try:
            try:
                await client.write_gatt_char(write_uuid, frame, response=False)
            except Exception:
                await client.write_gatt_char(write_uuid, frame, response=True)

            await asyncio.wait_for(packet_done.wait(), timeout=4.0)
            payload = bytes(rx_buf[3 : 3 + count * 2])
            return struct.unpack(f">{count}H", payload)
        except Exception as err:
            last_err = err
            await asyncio.sleep(0.5)
    raise last_err


async def async_setup_entry(hass, entry):
    """Set up yBMS from a config entry."""
    address = entry.data[CONF_ADDRESS]

    ble_device = bluetooth.async_ble_device_from_address(
        hass, address, connectable=True
    )
    if not ble_device:
        raise ConfigEntryNotReady(
            f"yBMS Gerät {address} noch nicht über Bluetooth erreichbar"
        )

    async def _async_update_data():
        return await _async_update_telemetry(hass, entry)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="yBMS",
        update_method=_async_update_data,
        update_interval=timedelta(seconds=90),
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "address": address,
        "coordinator": coordinator,
        "telemetry": {},
    }

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def _async_update_telemetry(hass, entry):
    """Fetch live 16S telemetry from Modbus banks 0xD000, 0xD020, 0xD030."""
    domain_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not domain_data:
        return {}

    address = domain_data["address"]
    ble_device = bluetooth.async_ble_device_from_address(
        hass, address, connectable=True
    )
    if not ble_device:
        return domain_data.get("telemetry", {})

    client = await establish_connection(
        bleak.BleakClient,
        ble_device,
        ble_device.name or "yBMS",
        max_attempts=3,
    )

    rx_buf = bytearray()
    packet_done = asyncio.Event()

    def handle_notify(sender, data: bytearray):
        rx_buf.extend(data)
        if rx_buf.startswith(b"\x01\x03") and len(rx_buf) >= 37:
            packet_done.set()

    try:
        notify_uuid, write_uuid = _find_characteristics(client)
        if not notify_uuid or not write_uuid:
            return domain_data.get("telemetry", {})

        await client.start_notify(notify_uuid, handle_notify)
        await asyncio.sleep(0.3)

        # 1. 16 Einzelzellspannungen (0xD000..0xD00F, in mV)
        cells = list(await _read_register_block(client, write_uuid, rx_buf, packet_done, 0xD000, 16))
        await asyncio.sleep(0.45)

        # 2. Pack-Spannung & Temperaturen (0xD020..0xD02F)
        (
            max_cell_mv,
            min_cell_mv,
            max_cell_idx,
            min_cell_idx,
            drift_mv,
            pack_v_raw,
            temp1_raw,
            temp2_raw,
            *_rest20,
        ) = await _read_register_block(client, write_uuid, rx_buf, packet_done, 0xD020, 16)
        await asyncio.sleep(0.45)

        # 3. Strom, SOC, SOH & Restkapazität (0xD030..0xD03F)
        (
            _r0,
            _r1,
            _r2,
            current_raw,
            soc_pct,
            soh_pct,
            rem_cap_raw,
            nom_cap_raw,
            full_cap_raw,
            *_rest30,
        ) = await _read_register_block(client, write_uuid, rx_buf, packet_done, 0xD030, 16)

        await client.stop_notify(notify_uuid)

        voltage_v = round(pack_v_raw / 100.0, 2)
        temp_c = round((temp1_raw - 273.15) / 10.0, 1) if temp1_raw > 200 else round(temp1_raw * 0.1, 1)

        raw_current_signed = current_raw - 65536 if current_raw >= 32768 else current_raw
        current_a = round(raw_current_signed / 100.0, 2)
        capacity_ah = round(rem_cap_raw / 100.0, 2)

        telemetry = {
            "voltage_V": voltage_v,
            "current_A": current_a,
            "temperature_c": temp_c,
            "state_of_charge_pct": soc_pct,
            "cell_voltages_mV": cells,
            "capacity_ah": capacity_ah,
            "status_flags": f"OK (SOH {soh_pct}%, Drift {drift_mv} mV)",
        }

        domain_data["telemetry"] = telemetry
        return telemetry

    except Exception as err:
        _LOGGER.debug("yBMS Auslese-Hinweis (%s): %r", address, err)
        return domain_data.get("telemetry", {})

    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unloaded and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
