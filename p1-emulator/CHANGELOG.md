# Changelog

## 0.1.10

- Run the service launcher with the Bashio interpreter so ingress and logging
  helper functions are available.

## 0.1.9

- Read the dynamic ingress port through the compatible Bashio add-on function.
- Fail with a clear startup message when Supervisor does not supply a valid
  ingress port.

## 0.1.8

- Fix relative API requests when the web UI is hosted below Home Assistant's
  dynamic ingress path.
- Restore authenticated Home Assistant state loading for both the emulator and
  ingress UI.
- Verify that the ingress listener rejects requests not forwarded by the
  Supervisor while the LAN listener exposes only the HomeWizard API.

## 0.1.7

- Serve the sensor-selection UI through Home Assistant ingress only.
- Keep the HomeWizard API and mDNS service available on the configured LAN port.

## 0.1.6

- Add Home Assistant app icon and logo assets.

## 0.1.5

- Fix api endpoint

## 0.1.4

- Add simulated wifi coverage.

## 0.1.3

- Enforce the HomeWizard API v1 measurement field set in API responses.
- Keep separate import/export mappings as internal inputs and expose only their
  signed `active_power_w` and `active_power_l1_w`/L2/L3 results.

## 0.1.2

- Derive total active power by summing available L1, L2, and L3 power values
  when no total active-power sensor is configured.

## 0.1.1

- Add default mappings for standard Home Assistant DSMR sensor entity IDs.
- Derive signed per-phase power from separate consumption and production sensors.

## 0.1.0

- Initial HomeWizard P1 API v1 emulator.
- Home Assistant websocket state-event subscription and in-memory cache.
- mDNS discovery and generated DSMR telegram support.
