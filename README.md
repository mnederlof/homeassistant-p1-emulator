# Home Assistant P1 Emulator

This repository contains a Home Assistant app that exposes selected Home
Assistant sensors as a HomeWizard P1 Meter on the local network.

[![P1 Meter Emulator icon](p1-emulator/icon.png)](p1-emulator/)

[![Add repository to my Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fmnederlof%2Fhomeassistant-p1-emulator)

Click the button above to open Home Assistant and add this repository to the
app repository list.
You can also add it manually from **Settings → Apps → App store → ⋮ →
Repositories**.

The app:

- reads an initial snapshot from Home Assistant;
- subscribes to `state_changed` events and keeps only the latest values in
  memory;
- provides a Home Assistant ingress UI to map sensors to each HomeWizard
  measurement without exposing the configuration interface on the LAN;
- implements the HomeWizard API v1 P1 endpoints;
- generates a DSMR telegram from the cached values; and
- advertises `_hwenergy._tcp` over mDNS.

See [the app documentation](p1-emulator/DOCS.md) for installation and sensor
mapping examples.
