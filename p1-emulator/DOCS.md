# P1 Meter Emulator

## Configuration

Map each HomeWizard measurement to a Home Assistant sensor entity. Empty
mappings are ignored. At minimum, map power and energy totals:

```yaml
port: 80
device_name: P1 Meter
serial: 02A1B2C3D4E5
meter_model: Home Assistant
smr_version: 50
sensors:
  active_power_import_w: sensor.electricity_currently_delivered
  active_power_export_w: sensor.electricity_currently_returned
  total_power_import_t1_kwh: sensor.electricity_import_tariff_1
  total_power_import_t2_kwh: sensor.electricity_import_tariff_2
  total_power_export_t1_kwh: sensor.electricity_export_tariff_1
  total_power_export_t2_kwh: sensor.electricity_export_tariff_2
  active_voltage_l1_v: sensor.voltage_l1
  total_gas_m3: sensor.gas_consumption
```

For a fresh installation, the app already maps the standard DSMR entity IDs
such as `sensor.power_consumption`, `sensor.power_production`,
`sensor.energy_consumption_tarif_1`, the per-phase power/current/voltage
sensors, voltage sag/swell counters, and power failure counters.

`active_power_w` may be mapped directly, which is useful for CT-based sensors
that already report signed net power. If it is not mapped, the app sums the
available signed L1, L2, and L3 values. Per-phase signed power is derived from
the separate per-phase consumption and production sensors when needed. If no
phase values are available, total active power falls back to total imported
power minus total exported power. The app also derives total imported/exported
energy by adding configured tariff sensors.

The import/export mapping names are configuration inputs only. They are never
included in `/api/v1/data`. For example, the L1 inputs are combined as:

```text
active_power_l1_w = active_power_import_l1_w - active_power_export_l1_w
```

The API response contains only the HomeWizard field `active_power_l1_w`, which
is negative while L1 is exporting. L2, L3, and total active power follow the
same rule.

`sensor.power_tariff` and `sensor.electricity_meter_timestamp` are not mapped
because the HomeWizard P1 API v1 measurement response has no corresponding
fields.

The app converts common Home Assistant units automatically (for example kW to
W, Wh to kWh, and litres to m³). Unknown, unavailable, and non-numeric states
are logged and do not replace the last valid cached value.

## API

The emulated meter is announced as `_hwenergy._tcp.local.` and provides:

- `GET /api`
- `GET /api/v1` (compatibility alias)
- `GET /api/v1/data`
- `GET /api/v1/telegram`
- `GET` and `PUT /api/v1/system`
- `PUT /api/v1/identify`

The app uses host networking because mDNS multicast must reach the LAN. Port 80
therefore needs to be free on the Home Assistant host. Change `port` if it is
already in use; the mDNS record advertises the configured port.

## Web UI

Open the app from the **P1 Meter Emulator** entry in the Home Assistant
sidebar, or use the app's **Open Web UI** button. The UI is served through
Home Assistant ingress and is not available on the LAN API port. Home
Assistant handles authentication; no additional UI login is required.

The page lists all available entities and lets you assign the HomeWizard fields
one by one. The selections are stored back to the app's `/data/options.json`,
so they are retained across restarts.

The ingress listener combines the UI and API endpoints in the same app. Its
random host-network port accepts only requests forwarded by the Home Assistant
Supervisor. A separate listener on the configured LAN port exposes only the
HomeWizard-compatible API for HomeWizard clients and mDNS discovery; UI routes
return `404` there.

Values exist only in memory and are repopulated from current Home Assistant
states whenever the app starts.
