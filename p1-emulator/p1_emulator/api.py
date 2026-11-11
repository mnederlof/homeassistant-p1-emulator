from __future__ import annotations

import json
import logging
from pathlib import Path

import aiohttp
from aiohttp import web

from . import __version__
from .cache import MeasurementCache
from .config import Settings
from .telegram import generate_telegram

LOGGER = logging.getLogger(__name__)

FIELD_ORDER = [
    "active_power_w",
    "active_power_import_w",
    "active_power_export_w",
    "active_power_import_l1_w",
    "active_power_export_l1_w",
    "active_power_import_l2_w",
    "active_power_export_l2_w",
    "active_power_import_l3_w",
    "active_power_export_l3_w",
    "total_power_import_kwh",
    "total_power_import_t1_kwh",
    "total_power_import_t2_kwh",
    "total_power_import_t3_kwh",
    "total_power_import_t4_kwh",
    "total_power_export_kwh",
    "total_power_export_t1_kwh",
    "total_power_export_t2_kwh",
    "total_power_export_t3_kwh",
    "total_power_export_t4_kwh",
    "active_power_l1_w",
    "active_power_l2_w",
    "active_power_l3_w",
    "active_voltage_l1_v",
    "active_voltage_l2_v",
    "active_voltage_l3_v",
    "active_current_l1_a",
    "active_current_l2_a",
    "active_current_l3_a",
    "active_frequency_hz",
    "voltage_sag_l1_count",
    "voltage_sag_l2_count",
    "voltage_sag_l3_count",
    "voltage_swell_l1_count",
    "voltage_swell_l2_count",
    "voltage_swell_l3_count",
    "any_power_fail_count",
    "long_power_fail_count",
    "active_power_average_w",
    "montly_power_peak_w",
    "total_gas_m3",
]


def _friendly_label(field: str) -> str:
    return field.replace("_", " ").replace("kwh", "kWh").replace("w", "W").replace("v", "V").replace("a", "A").replace("hz", "Hz").title()


UI_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>P1 Meter Emulator</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #f3f5f8; color: #1b2430; }
    .container { max-width: 1200px; margin: 0 auto; }
    .panel { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,.06); }
    h1 { margin-top: 0; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
    .field { display: flex; flex-direction: column; gap: 8px; }
    label { font-weight: 600; }
    select { width: 100%; min-height: 42px; border: 1px solid #d5dbe2; border-radius: 8px; padding: 8px 10px; font-size: 14px; }
    button { background: #0d79d0; color: white; border: none; border-radius: 8px; padding: 12px 18px; font-size: 15px; font-weight: 700; cursor: pointer; }
    button:hover { background: #0b67af; }
    .status { margin-top: 18px; font-weight: 600; min-height: 24px; }
    .status.ok { color: #0d7a45; }
    .status.error { color: #b42318; }
    .muted { color: #526074; font-size: 12px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="panel">
      <h1>P1 Meter Emulator</h1>
      <p class="muted">Select the Home Assistant entities to represent each HomeWizard meter value. Empty selections are ignored.</p>
      <form id="config-form">
        <div id="field-grid" class="grid"></div>
        <div style="margin-top: 20px;"><button type="submit">Save selections</button></div>
      </form>
      <div id="status" class="status" aria-live="polite"></div>
    </div>
  </div>
  <script>
    const fieldOrder = __FIELD_ORDER__;
    const entityList = [];
    const emptyOption = '<option value="">(empty)</option>';

    function prettyEntity(entity) {
      const name = (entity.attributes && entity.attributes.friendly_name) || entity.entity_id;
      return `${name} (${entity.entity_id})`;
    }

    function buildOptions(selected) {
      return [emptyOption].concat(entityList.filter((entity) => entity.entity_id).map((entity) => {
        const selectedAttr = entity.entity_id === selected ? ' selected' : '';
        return `<option value="${entity.entity_id}"${selectedAttr}>${prettyEntity(entity)}</option>`;
      })).join('');
    }

    function renderFields(selectedMap) {
      const grid = document.getElementById('field-grid');
      grid.innerHTML = '';
      fieldOrder.forEach((field) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'field';
        wrapper.innerHTML = `
          <label for="field-${field}">${_friendlyLabel(field)}</label>
          <select id="field-${field}" name="${field}">${buildOptions(selectedMap[field] || '')}</select>
        `;
        grid.appendChild(wrapper);
      });
    }

    function _friendlyLabel(field) {
      return field.replace(/[_]/g, ' ').replace(/kwh/gi, 'kWh').replace(/w/gi, 'W').replace(/v/gi, 'V').replace(/a/gi, 'A').replace(/hz/gi, 'Hz').replace(/\b\w/g, (match) => match.toUpperCase());
    }

    async function loadData() {
      const [configResponse, statesResponse] = await Promise.all([
        fetch('/api/ui/config'),
        fetch('/api/states')
      ]);
      const config = await configResponse.json();
      const states = await statesResponse.json();
      entityList.push(...states);
      renderFields(config.selected || {});
    }

    document.getElementById('config-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(event.target);
      const selected = {};
      for (const [key, value] of formData.entries()) {
        if (value) selected[key] = value;
      }
      const status = document.getElementById('status');
      status.textContent = 'Saving...';
      status.className = 'status';
      try {
        const response = await fetch('/api/ui/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mappings: selected })
        });
        if (!response.ok) {
          throw new Error('Failed to save selections');
        }
        status.textContent = 'Saved successfully.';
        status.classList.add('ok');
      } catch (error) {
        status.textContent = error.message || 'Could not save selections.';
        status.classList.add('error');
      }
    });

    loadData().catch((error) => {
      const status = document.getElementById('status');
      status.textContent = 'Unable to load Home Assistant entities.';
      status.classList.add('error');
      console.error(error);
    });
  </script>
</body>
</html>
"""
UI_HTML = UI_HTML.replace("__FIELD_ORDER__", json.dumps(FIELD_ORDER))


def _sanitise_selection(raw: dict[str, object]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in FIELD_ORDER:
        value = raw.get(field)
        if value is None:
            continue
        entity_id = str(value).strip()
        if entity_id:
            result[field] = entity_id
    return result


def create_web_app(
    settings: Settings,
    cache: MeasurementCache,
    options_path: str | Path = "/data/options.json",
) -> web.Application:
    app = web.Application()
    system_state = {"cloud_enabled": False}
    options_file = Path(options_path)

    async def device_info(_: web.Request) -> web.Response:
        return web.json_response(
            {
                "product_type": "HWE-P1",
                "product_name": "P1 Meter",
                "serial": settings.serial.lower(),
                "firmware_version": __version__,
                "api_version": "v1",
            }
        )

    async def measurement(_: web.Request) -> web.Response:
        values = cache.snapshot()
        return web.json_response(
            {
                "unique_id": settings.serial,
                "smr_version": settings.smr_version,
                "meter_model": settings.meter_model,
                **values,
            }
        )

    async def telegram(_: web.Request) -> web.Response:
        content = generate_telegram(
            cache.snapshot(),
            settings.serial,
            settings.meter_model,
            settings.smr_version,
        )
        return web.Response(text=content, content_type="text/plain")

    async def get_system(_: web.Request) -> web.Response:
        return web.json_response(system_state)

    async def put_system(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except (ValueError, web.HTTPBadRequest):
            raise web.HTTPBadRequest(
                text='{"error":{"id":"invalid_request","description":"Invalid JSON"}}',
                content_type="application/json",
            )
        if not isinstance(body, dict) or set(body) != {"cloud_enabled"} or not isinstance(
            body["cloud_enabled"], bool
        ):
            raise web.HTTPBadRequest(
                text='{"error":{"id":"invalid_request","description":"cloud_enabled must be boolean"}}',
                content_type="application/json",
            )
        system_state["cloud_enabled"] = body["cloud_enabled"]
        return web.json_response(system_state)

    async def identify(_: web.Request) -> web.Response:
        LOGGER.info("Identify requested for emulated meter %s", settings.serial)
        return web.json_response({"identify": "ok"})

    async def ui_index(_: web.Request) -> web.Response:
        return web.Response(text=UI_HTML, content_type="text/html")

    async def ui_config_get(_: web.Request) -> web.Response:
        selected = {field: entity_id for field, entity_id in settings.sensors.items() if entity_id}
        return web.json_response({"selected": selected})

    async def ui_config_post(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except (ValueError, web.HTTPBadRequest):
            raise web.HTTPBadRequest(
                text='{"error":{"id":"invalid_request","description":"Invalid JSON"}}',
                content_type="application/json",
            )
        mappings = body.get("mappings", {}) if isinstance(body, dict) else {}
        if not isinstance(mappings, dict):
            raise web.HTTPBadRequest(
                text='{"error":{"id":"invalid_request","description":"mappings must be an object"}}',
                content_type="application/json",
            )
        sanitized = _sanitise_selection(mappings)
        object.__setattr__(settings, "sensors", sanitized)
        cache.set_mappings(sanitized)

        options_file.parent.mkdir(parents=True, exist_ok=True)
        if options_file.exists():
            try:
                with options_file.open("r", encoding="utf-8") as handle:
                    options = json.load(handle)
            except json.JSONDecodeError:
                options = {}
        else:
            options = {}
        options["sensors"] = sanitized
        with options_file.open("w", encoding="utf-8") as handle:
            json.dump(options, handle, indent=2, sort_keys=True)
            handle.write("\n")

        return web.json_response({"ok": True, "selected": sanitized})

    async def ha_states(_: web.Request) -> web.Response:
        headers = {"Authorization": f"Bearer {settings.ha_token}"}
        timeout = aiohttp.ClientTimeout(total=20)
        try:
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(f"{settings.ha_rest_url}/states") as response:
                    response.raise_for_status()
                    states = await response.json()
        except (aiohttp.ClientError, TimeoutError) as error:
            raise web.HTTPServiceUnavailable(text=str(error)) from error

        payload = []
        for state in states:
            entity_id = state.get("entity_id")
            if not entity_id:
                continue
            payload.append(
                {
                    "entity_id": entity_id,
                    "state": state.get("state"),
                    "attributes": state.get("attributes", {}),
                    "friendly_name": state.get("attributes", {}).get("friendly_name", entity_id),
                }
            )
        payload.sort(key=lambda item: item["entity_id"])
        return web.json_response(payload)

    app.router.add_get("/", ui_index)
    app.router.add_get("/ui", ui_index)
    app.router.add_get("/api", device_info)
    app.router.add_get("/api/v1", device_info)
    app.router.add_get("/api/v1/data", measurement)
    app.router.add_get("/api/v1/telegram", telegram)
    app.router.add_get("/api/v1/system", get_system)
    app.router.add_get("/api/states", ha_states)
    app.router.add_get("/api/ui/config", ui_config_get)
    app.router.add_post("/api/ui/config", ui_config_post)
    app.router.add_put("/api/v1/system", put_system)
    app.router.add_put("/api/v1/identify", identify)
    return app
