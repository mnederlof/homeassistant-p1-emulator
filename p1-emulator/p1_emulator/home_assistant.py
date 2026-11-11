from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .cache import MeasurementCache
from .config import Settings

LOGGER = logging.getLogger(__name__)


class HomeAssistantClient:
    def __init__(self, settings: Settings, cache: MeasurementCache) -> None:
        self._settings = settings
        self._cache = cache
        self._session: aiohttp.ClientSession | None = None

    async def run(self) -> None:
        headers = {"Authorization": f"Bearer {self._settings.ha_token}"}
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            self._session = session
            delay = 1
            while True:
                try:
                    await self._load_initial_states()
                    await self._listen_for_state_changes()
                    delay = 1
                except asyncio.CancelledError:
                    raise
                except (
                    aiohttp.ClientError,
                    asyncio.TimeoutError,
                    RuntimeError,
                    ValueError,
                ) as error:
                    LOGGER.error(
                        "Home Assistant event connection failed: %s; retrying in %ss",
                        error,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 30)

    async def _load_initial_states(self) -> None:
        assert self._session is not None
        async with self._session.get(f"{self._settings.ha_rest_url}/states") as response:
            response.raise_for_status()
            states: list[dict[str, Any]] = await response.json()
        found_entities = set()
        for state in states:
            if state.get("entity_id") in self._cache.entity_ids:
                found_entities.add(state["entity_id"])
                self._cache.update_state(state)
        missing = self._cache.entity_ids - found_entities
        if missing:
            LOGGER.warning("Configured entities not found: %s", ", ".join(sorted(missing)))
        LOGGER.info("Loaded %d configured Home Assistant states", len(found_entities))

    async def _listen_for_state_changes(self) -> None:
        assert self._session is not None
        async with self._session.ws_connect(
            self._settings.ha_websocket_url, heartbeat=30
        ) as websocket:
            auth_required = await websocket.receive_json()
            if auth_required.get("type") != "auth_required":
                raise RuntimeError("unexpected Home Assistant websocket greeting")
            await websocket.send_json(
                {"type": "auth", "access_token": self._settings.ha_token}
            )
            auth_result = await websocket.receive_json()
            if auth_result.get("type") != "auth_ok":
                raise RuntimeError(
                    f"Home Assistant websocket authentication failed: {auth_result}"
                )
            await websocket.send_json(
                {"id": 1, "type": "subscribe_events", "event_type": "state_changed"}
            )
            subscription_result = await websocket.receive_json()
            if not subscription_result.get("success"):
                raise RuntimeError(
                    f"state_changed subscription failed: {subscription_result}"
                )
            LOGGER.info("Listening for Home Assistant state_changed events")
            async for message in websocket:
                if message.type == aiohttp.WSMsgType.ERROR:
                    raise RuntimeError(str(websocket.exception()))
                if message.type != aiohttp.WSMsgType.TEXT:
                    continue
                payload = message.json()
                if payload.get("type") != "event":
                    continue
                state = payload.get("event", {}).get("data", {}).get("new_state")
                if state and state.get("entity_id") in self._cache.entity_ids:
                    self._cache.update_state(state)
