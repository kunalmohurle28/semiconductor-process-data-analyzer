
import unittest
import pandas as pd

from analyzer import analyze_readings


def sample_data():
    return pd.DataFrame({
        "lot_id": ["LOT001", "LOT001"],
        "wafer_id": ["W001", "W002"],
        "temperature_c": [24.0, 30.0],
        "pressure_kpa": [100.0, 101.0],
        "defect_count": [1, 2],
    })


class TestProcessAnalyzer(unittest.TestCase):

    def test_valid_data_is_accepted(self):
        result = analyze_readings(sample_data())
        self.assertEqual(len(result), 2)

    def test_out_of_limit_reading_is_flagged(self):
        result = analyze_readings(sample_data())
        self.assertTrue(result.loc[1, "abnormal"])
        self.assertEqual(result.loc[1, "status"], "REVIEW")
        self.assertIn(
            "temperature_c",
            result.loc[1, "abnormal_reasons"],
        )

    def test_missing_column_is_rejected(self):
        df = sample_data().drop(columns=["pressure_kpa"])
        with self.assertRaisesRegex(ValueError, "Missing required"):
            analyze_readings(df)

    def test_missing_measurement_is_rejected(self):
        df = sample_data()
        df.loc[0, "temperature_c"] = float("nan")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            analyze_readings(df)

    def test_negative_defect_count_is_rejected(self):
        df = sample_data()
        df.loc[0, "defect_count"] = -1
        with self.assertRaisesRegex(ValueError, "non-negative"):
            analyze_readings(df)


if __name__ == "__main__":
    unittest.main(verbosity=2)
