import unittest
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
            sensors={"active_power_w": "sensor.power"},
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

    async def test_web_ui_is_served_and_config_can_be_saved(self) -> None:
        async with self.session.get(f"{self.base_url}/") as response:
            self.assertEqual(response.status, 200)
            self.assertIn("P1 Meter Emulator", await response.text())

        async with self.session.get(f"{self.base_url}/api/ui/config") as response:
            payload = await response.json()
        self.assertEqual(payload["selected"], {"active_power_w": "sensor.power"})

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
