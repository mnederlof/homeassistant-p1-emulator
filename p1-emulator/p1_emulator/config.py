from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    port: int
    device_name: str
    serial: str
    meter_model: str
    smr_version: int
    sensors: dict[str, Any]
    ha_rest_url: str
    ha_websocket_url: str
    ha_token: str


def load_settings(path: str | Path | None = None) -> Settings:
    options_path = Path(path or os.environ.get("OPTIONS_PATH", "/data/options.json"))
    options: dict[str, Any] = {}
    if options_path.exists():
        with options_path.open(encoding="utf-8") as options_file:
            options = json.load(options_file)

    token = os.environ.get("HA_TOKEN") or os.environ.get("SUPERVISOR_TOKEN", "")
    rest_url = os.environ.get("HA_REST_URL", "http://supervisor/core/api")
    websocket_url = os.environ.get(
        "HA_WEBSOCKET_URL", "ws://supervisor/core/websocket"
    )
    serial = str(options.get("serial", "02A1B2C3D4E5")).upper()
    if len(serial) != 12 or any(character not in "0123456789ABCDEF" for character in serial):
        raise ValueError("serial must contain exactly 12 hexadecimal characters")
    if not token:
        raise ValueError("SUPERVISOR_TOKEN or HA_TOKEN is required")

    return Settings(
        port=int(options.get("port", 80)),
        device_name=str(options.get("device_name", "P1 Meter")),
        serial=serial,
        meter_model=str(options.get("meter_model", "Home Assistant")),
        smr_version=int(options.get("smr_version", 50)),
        sensors={
            key: value
            for key, value in options.get("sensors", {}).items()
            if value and (not isinstance(value, str) or value.strip())
        },
        ha_rest_url=rest_url.rstrip("/"),
        ha_websocket_url=websocket_url,
        ha_token=token,
    )

