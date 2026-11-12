import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from aiohttp import ClientSession, web

from p1_emulator.api import create_web_app
from p1_emulator.cache import MeasurementCache
from p1_emulator.config import Settings


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.options_path = Path(self.temp_directory.name) / "options.json"
        settings = Settings(
            port=0,
            device_name="Test meter",
            serial="02A1B2C3D4E5",
            meter_model="Test model",
            smr_version=50,
            sensors={
                "active_power_w": "sensor.power",
                "active_power_import_l1_w": "sensor.power_import_l1",
                "active_power_export_l1_w": "sensor.power_export_l1",
            },
            ha_rest_url="http://homeassistant/api",
            ha_websocket_url="ws://homeassistant/api/websocket",
            ha_token="test",
        )
        cache = MeasurementCache(settings.sensors)
        cache.update_state(
            {
                "entity_id": "sensor.power",
                "state": "123",
                "attributes": {"unit_of_measurement": "W"},
            }
        )
        cache.update_state(
            {
                "entity_id": "sensor.power_import_l1",
                "state": "100",
                "attributes": {"unit_of_measurement": "W"},
            }
        )
        cache.update_state(
            {
                "entity_id": "sensor.power_export_l1",
                "state": "250",
                "attributes": {"unit_of_measurement": "W"},
            }
        )
        self.settings = settings
        self.cache = cache
        self.runner = web.AppRunner(
            create_web_app(settings, cache, options_path=self.options_path)
        )
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await self.site.start()
        server = self.site._server
        assert server is not None
        port = server.sockets[0].getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}"
        self.session = ClientSession()

    async def asyncTearDown(self) -> None:
        await self.session.close()
        await self.runner.cleanup()
        self.temp_directory.cleanup()

    async def test_device_and_measurement_endpoints(self) -> None:
        async with self.session.get(f"{self.base_url}/api") as response:
            self.assertEqual(response.status, 200)
            device = await response.json()
        self.assertEqual(device["product_type"], "HWE-P1")
        self.assertEqual(device["serial"], "02a1b2c3d4e5")

        async with self.session.get(f"{self.base_url}/api/v1/data") as response:
            measurement = await response.json()
        self.assertEqual(measurement["unique_id"], "02A1B2C3D4E5")
        self.assertEqual(measurement["active_power_w"], 123)
        self.assertEqual(measurement["active_power_l1_w"], -150)
        self.assertNotIn("active_power_import_l1_w", measurement)
        self.assertNotIn("active_power_export_l1_w", measurement)

    async def test_web_ui_is_served_and_config_can_be_saved(self) -> None:
        async with self.session.get(f"{self.base_url}/") as response:
            self.assertEqual(response.status, 200)
            page = await response.text()
            self.assertIn("P1 Meter Emulator", page)
            self.assertIn("fetch('./api/ui/config'", page)
            self.assertNotIn("fetch('/api/ui/config'", page)

        async with self.session.get(f"{self.base_url}/api/ui/config") as response:
            payload = await response.json()
        self.assertEqual(payload["selected"]["active_power_w"], "sensor.power")

        async with self.session.post(
            f"{self.base_url}/api/ui/config",
            json={
                "mappings": {
                    "active_power_w": "sensor.other_power",
                    "total_power_import_t1_kwh": "sensor.daily_energy",
                }
            },
        ) as response:
            body = await response.json()
        self.assertEqual(body["ok"], True)
        self.assertEqual(body["selected"]["active_power_w"], "sensor.other_power")
        self.assertTrue(self.options_path.exists())

    async def test_ingress_rejects_direct_access_and_combines_ui_with_api(self) -> None:
        guarded_runner = web.AppRunner(
            create_web_app(
                self.settings,
                self.cache,
                options_path=self.options_path,
                require_ingress=True,
            )
        )
        await guarded_runner.setup()
        guarded_site = web.TCPSite(guarded_runner, "127.0.0.1", 0)
        await guarded_site.start()
        guarded_port = guarded_site._server.sockets[0].getsockname()[1]
        try:
            async with self.session.get(
                f"http://127.0.0.1:{guarded_port}/"
            ) as response:
                self.assertEqual(response.status, 403)
            async with self.session.get(
                f"http://127.0.0.1:{guarded_port}/api/v1/data"
            ) as response:
                self.assertEqual(response.status, 403)
        finally:
            await guarded_runner.cleanup()

        ingress_runner = web.AppRunner(
            create_web_app(
                self.settings,
                self.cache,
                options_path=self.options_path,
                require_ingress=True,
                trusted_ingress_remote="127.0.0.1",
            )
        )
        await ingress_runner.setup()
        ingress_site = web.TCPSite(ingress_runner, "127.0.0.1", 0)
        await ingress_site.start()
        ingress_port = ingress_site._server.sockets[0].getsockname()[1]
        try:
            async with self.session.get(
                f"http://127.0.0.1:{ingress_port}/"
            ) as response:
                self.assertEqual(response.status, 200)
            async with self.session.get(
                f"http://127.0.0.1:{ingress_port}/api/v1/data"
            ) as response:
                self.assertEqual(response.status, 200)
        finally:
            await ingress_runner.cleanup()

    async def test_ui_state_request_authenticates_to_home_assistant(self) -> None:
        received_authorization = None

        async def states(request: web.Request) -> web.Response:
            nonlocal received_authorization
            received_authorization = request.headers.get("Authorization")
            return web.json_response([])

        home_assistant_app = web.Application()
        home_assistant_app.router.add_get("/states", states)
        home_assistant_runner = web.AppRunner(home_assistant_app)
        await home_assistant_runner.setup()
        home_assistant_site = web.TCPSite(
            home_assistant_runner, "127.0.0.1", 0
        )
        await home_assistant_site.start()
        home_assistant_port = home_assistant_site._server.sockets[0].getsockname()[1]

        settings = replace(
            self.settings,
            ha_rest_url=f"http://127.0.0.1:{home_assistant_port}",
        )
        ui_runner = web.AppRunner(
            create_web_app(
                settings,
                self.cache,
                options_path=self.options_path,
            )
        )
        await ui_runner.setup()
        ui_site = web.TCPSite(ui_runner, "127.0.0.1", 0)
        await ui_site.start()
        ui_port = ui_site._server.sockets[0].getsockname()[1]
        try:
            async with self.session.get(
                f"http://127.0.0.1:{ui_port}/api/states"
            ) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(received_authorization, "Bearer test")
        finally:
            await ui_runner.cleanup()
            await home_assistant_runner.cleanup()

    async def test_api_only_surface_does_not_expose_web_ui(self) -> None:
        settings = Settings(
            port=0,
            device_name="Test meter",
            serial="02A1B2C3D4E5",
            meter_model="Test model",
            smr_version=50,
            sensors={},
            ha_rest_url="http://homeassistant/api",
            ha_websocket_url="ws://homeassistant/api/websocket",
            ha_token="test",
        )
        runner = web.AppRunner(
            create_web_app(settings, MeasurementCache({}), include_ui=False)
        )
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        try:
            async with self.session.get(f"http://127.0.0.1:{port}/") as response:
                self.assertEqual(response.status, 404)
            async with self.session.get(
                f"http://127.0.0.1:{port}/api"
            ) as response:
                self.assertEqual(response.status, 200)
        finally:
            await runner.cleanup()

    async def test_system_state_is_mutable_and_validated(self) -> None:
        async with self.session.put(
            f"{self.base_url}/api/v1/system", json={"cloud_enabled": True}
        ) as response:
            self.assertEqual(await response.json(), {"cloud_enabled": True})

        async with self.session.get(f"{self.base_url}/api/v1/system") as response:
            self.assertEqual(await response.json(), {"cloud_enabled": True})

        async with self.session.put(
            f"{self.base_url}/api/v1/system", json={"cloud_enabled": "yes"}
        ) as response:
            self.assertEqual(response.status, 400)


if __name__ == "__main__":
    unittest.main()
