# Changelog

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
