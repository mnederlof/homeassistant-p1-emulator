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

`active_power_w` may be mapped directly, which is useful for CT-based sensors
that already report signed net power. Otherwise the app derives it as imported
power minus exported power. It also derives total imported/exported energy by
adding configured tariff sensors.

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

Open the app at `http://<home-assistant-host>:<port>/` (for example
`http://homeassistant.local:80/`) to choose the Home Assistant entities in a
browser. The page lists all available entities and lets you assign the
HomeWizard fields one by one. The selections are stored back to the app's
`/data/options.json`, so they are retained across restarts.

Values exist only in memory and are repopulated from current Home Assistant
states whenever the app starts.

