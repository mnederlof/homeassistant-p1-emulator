from __future__ import annotations

import asyncio
import logging
import os
import signal

from aiohttp import web

from .api import create_web_app
from .cache import MeasurementCache
from .config import load_settings
from .discovery import register_service
from .home_assistant import HomeAssistantClient

LOGGER = logging.getLogger(__name__)


def ingress_port_from_environment() -> int:
    raw_port = os.environ.get("INGRESS_PORT", "").strip()
    if not raw_port:
        raise ValueError("Home Assistant did not provide INGRESS_PORT")
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError(f"INGRESS_PORT is not a valid port: {raw_port!r}") from error
    if not 1 <= port <= 65535:
        raise ValueError(f"INGRESS_PORT is outside the valid range: {port}")
    return port


async def run() -> None:
    settings = load_settings()
    ingress_port = ingress_port_from_environment()
    cache = MeasurementCache(settings.sensors)
    ha_client = HomeAssistantClient(settings, cache)
    api_runner = web.AppRunner(
        create_web_app(settings, cache, include_ui=False), access_log=LOGGER
    )
    await api_runner.setup()
    api_site = web.TCPSite(api_runner, "0.0.0.0", settings.port)
    await api_site.start()

    ui_runner = web.AppRunner(
        create_web_app(
            settings,
            cache,
            include_ui=True,
            require_ingress=True,
        ),
        access_log=LOGGER,
    )
    await ui_runner.setup()
    ui_site = web.TCPSite(ui_runner, "0.0.0.0", ingress_port)
    await ui_site.start()
    zeroconf, service_info = await register_service(settings)
    LOGGER.info(
        "Emulating HomeWizard P1 Meter %s on port %d with %d sensor mappings",
        settings.serial,
        settings.port,
        len(settings.sensors),
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signal_name, stop_event.set)
    ha_task = asyncio.create_task(ha_client.run(), name="home-assistant-events")
    try:
        await stop_event.wait()
    finally:
        ha_task.cancel()
        await asyncio.gather(ha_task, return_exceptions=True)
        await zeroconf.async_unregister_service(service_info)
        await zeroconf.async_close()
        await ui_runner.cleanup()
        await api_runner.cleanup()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    try:
        asyncio.run(run())
    except (OSError, ValueError) as error:
        LOGGER.critical("Unable to start P1 Meter Emulator: %s", error)
        raise SystemExit(1) from error
