import unittest

from p1_emulator.cache import MeasurementCache


def state(entity_id: str, value: str, unit: str) -> dict:
    return {
        "entity_id": entity_id,
        "state": value,
        "attributes": {"unit_of_measurement": unit},
    }


class MeasurementCacheTest(unittest.TestCase):
    def test_converts_units_and_derives_homewizard_values(self) -> None:
        cache = MeasurementCache(
            {
                "active_power_import_w": "sensor.import_power",
                "active_power_export_w": "sensor.export_power",
                "active_power_import_l1_w": "sensor.import_power_l1",
                "active_power_export_l1_w": "sensor.export_power_l1",
                "total_power_import_t1_kwh": "sensor.import_t1",
                "total_power_import_t2_kwh": "sensor.import_t2",
                "total_gas_m3": "sensor.gas",
            }
        )

        cache.update_state(state("sensor.import_power", "1.25", "kW"))
        cache.update_state(state("sensor.export_power", "50", "W"))
        cache.update_state(state("sensor.import_power_l1", "400", "W"))
        cache.update_state(state("sensor.export_power_l1", "25", "W"))
        cache.update_state(state("sensor.import_t1", "12000", "Wh"))
        cache.update_state(state("sensor.import_t2", "3", "kWh"))
        cache.update_state(state("sensor.gas", "2500", "L"))

        self.assertEqual(
            cache.snapshot(),
            {
                "active_power_w": 1200,
                "active_power_l1_w": 375,
                "total_power_import_t1_kwh": 12,
                "total_power_import_t2_kwh": 3,
                "total_power_import_kwh": 15,
                "total_gas_m3": 2.5,
            },
        )

    def test_invalid_state_does_not_replace_last_value(self) -> None:
        cache = MeasurementCache({"active_power_w": "sensor.power"})
        cache.update_state(state("sensor.power", "100", "W"))
        cache.update_state(state("sensor.power", "unavailable", "W"))
        self.assertEqual(cache.snapshot()["active_power_w"], 100)

    def test_advanced_mapping_supports_attribute_scale_and_offset(self) -> None:
        cache = MeasurementCache(
            {
                "active_power_w": {
                    "entity_id": "sensor.ct",
                    "attribute": "channel_1",
                    "scale": -1,
                    "offset": 5,
                }
            }
        )
        cache.update_state(
            {
                "entity_id": "sensor.ct",
                "state": "ignored",
                "attributes": {"channel_1": 10, "unit_of_measurement": "W"},
            }
        )
        self.assertEqual(cache.snapshot()["active_power_w"], -5)


if __name__ == "__main__":
    unittest.main()
