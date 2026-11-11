from __future__ import annotations

from datetime import datetime
from typing import Mapping


def _crc16(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def _value(values: Mapping[str, int | float], key: str) -> float:
    return float(values.get(key, 0))


def generate_telegram(
    values: Mapping[str, int | float],
    unique_id: str,
    meter_model: str,
    smr_version: int,
    now: datetime | None = None,
) -> str:
    current_time = now or datetime.now().astimezone()
    season = "S" if current_time.dst() else "W"
    timestamp = current_time.strftime("%y%m%d%H%M%S") + season
    ascii_meter_model = meter_model.encode("ascii", errors="replace").decode("ascii")
    active_power = _value(values, "active_power_w")
    delivered_kw = max(active_power, 0) / 1000
    returned_kw = max(-active_power, 0) / 1000
    lines = [
        f"/HA5\\{ascii_meter_model}",
        "",
        f"3:0.2.8({smr_version:02d})",
        f"0-0:1.0.0({timestamp})",
        f"0-0:96.1.1({unique_id})",
        f"1-0:1.8.1({_value(values, 'total_power_import_t1_kwh'):010.3f}*kWh)",
        f"1-0:1.8.2({_value(values, 'total_power_import_t2_kwh'):010.3f}*kWh)",
        f"1-0:2.8.1({_value(values, 'total_power_export_t1_kwh'):010.3f}*kWh)",
        f"1-0:2.8.2({_value(values, 'total_power_export_t2_kwh'):010.3f}*kWh)",
        f"1-0:1.7.0({delivered_kw:06.3f}*kW)",
        f"1-0:2.7.0({returned_kw:06.3f}*kW)",
    ]
    for phase, obis_prefix in ((1, 32), (2, 52), (3, 72)):
        voltage_key = f"active_voltage_l{phase}_v"
        if voltage_key in values:
            lines.append(f"1-0:{obis_prefix}.7.0({_value(values, voltage_key):05.1f}*V)")
    for phase, obis_prefix in ((1, 31), (2, 51), (3, 71)):
        current_key = f"active_current_l{phase}_a"
        if current_key in values:
            lines.append(f"1-0:{obis_prefix}.7.0({_value(values, current_key):03.0f}*A)")
    if "total_gas_m3" in values:
        lines.extend(
            [
                "0-1:24.1.0(003)",
                f"0-1:24.2.1({timestamp})({_value(values, 'total_gas_m3'):09.3f}*m3)",
            ]
        )
    body = "\r\n".join(lines) + "\r\n!"
    checksum = _crc16(body.encode("ascii"))
    return f"{body}{checksum:04X}\r\n"
