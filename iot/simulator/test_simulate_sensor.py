import unittest
from datetime import datetime

from simulate_sensor import SimulatorConfig, generate_readings


class SimulatorReadingTests(unittest.TestCase):
    def test_generated_readings_are_labelled_and_schema_compatible(self) -> None:
        readings = list(
            generate_readings(
                SimulatorConfig(
                    station_id="MAUBIN-01",
                    count=2,
                    interval_seconds=0.01,
                    baseline_water_level_cm=100,
                    rainfall_mm=2.5,
                    water_level_trend_cm=1.0,
                    noise_cm=0,
                    soil_moisture_percent=60,
                    battery_percent=90,
                    seed=7,
                )
            )
        )

        self.assertEqual(len(readings), 2)
        self.assertEqual(readings[0]["stationId"], "MAUBIN-01")
        self.assertEqual(readings[0]["source"], "simulator")
        self.assertEqual(readings[0]["waterLevelCm"], 100)
        self.assertEqual(readings[1]["waterLevelCm"], 101)
        self.assertEqual(readings[0]["rainfallMm"], 2.5)
        self.assertIsNotNone(
            datetime.fromisoformat(str(readings[0]["timestamp"])).utcoffset()
        )

    def test_zero_count_is_an_unbounded_stream(self) -> None:
        stream = generate_readings(
            SimulatorConfig(
                station_id="MAUBIN-01",
                count=0,
                interval_seconds=1,
                baseline_water_level_cm=100,
                rainfall_mm=0,
                water_level_trend_cm=0,
                noise_cm=0,
                soil_moisture_percent=50,
                battery_percent=100,
                seed=1,
            )
        )

        self.assertEqual(next(stream)["stationId"], "MAUBIN-01")
        self.assertEqual(next(stream)["stationId"], "MAUBIN-01")


if __name__ == "__main__":
    unittest.main()
