import unittest
from datetime import datetime, timezone

from p1_emulator.telegram import _crc16, generate_telegram


class TelegramTest(unittest.TestCase):
    def test_generates_valid_checksum_and_export_power(self) -> None:
        telegram = generate_telegram(
            {
                "active_power_w": -500,
                "total_power_import_t1_kwh": 1.25,
                "total_power_import_t2_kwh": 2.5,
                "active_voltage_l1_v": 230.1,
                "total_gas_m3": 12.345,
            },
            "02A1B2C3D4E5",
            "Home Assistant",
            50,
            datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

        body, checksum = telegram.rstrip("\r\n").rsplit("!", 1)
        body = body + "!"
        self.assertEqual(_crc16(body.encode("ascii")), int(checksum, 16))
        self.assertIn("1-0:1.7.0(00.000*kW)", telegram)
        self.assertIn("1-0:2.7.0(00.500*kW)", telegram)
        self.assertIn("0-1:24.2.1(260102030405W)(00012.345*m3)", telegram)


if __name__ == "__main__":
    unittest.main()

