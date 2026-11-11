# Home Assistant P1 Emulator

This repository contains a Home Assistant app that exposes selected Home
Assistant sensors as a HomeWizard P1 Meter on the local network.

The app:

- reads an initial snapshot from Home Assistant;
- subscribes to `state_changed` events and keeps only the latest values in
  memory;
- provides a browser-based selector UI at `/` to map Home Assistant sensors to
  each HomeWizard measurement;
- implements the HomeWizard API v1 P1 endpoints;
- generates a DSMR telegram from the cached values; and
- advertises `_hwenergy._tcp` over mDNS.

See [the app documentation](p1-emulator/DOCS.md) for installation and sensor
mapping examples.

