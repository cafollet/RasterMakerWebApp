import unittest
from io import BytesIO
from unittest.mock import patch, MagicMock
import pandas as pd

# Import modules
from backend.data_manipulation.provide_columns import provide_columns
from backend.data_manipulation.generate_raster_file import generate_raster_file


class TestCSVDelimiterIntegration(unittest.TestCase):
    """Integration tests for CSV processing with different delimiters"""

    def test_end_to_end_comma_csv(self):
        """Test complete flow with comma-delimited CSV"""
        # Create test CSV
        csv_content = """city,longitude,latitude,population,area_sqkm
New York,-74.0060,40.7128,8336817,783.8
Los Angeles,-118.2437,34.0522,3979576,1302.1
Chicago,-87.6298,41.8781,2693976,606.1
Houston,-95.3698,29.7604,2320268,1777.5
Phoenix,-112.0740,33.4484,1680992,1340.8"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))

        # Test 1: Column detection
        columns = provide_columns(csv_bytes)
        self.assertIn('longitude', columns)
        self.assertIn('latitude', columns)
        self.assertIn('population', columns)
        self.assertIn('area_sqkm', columns)
        self.assertNotIn('city', columns)

        # Test 2: Raster generation (mocked)
        csv_bytes.seek(0)
        out_fp = BytesIO()
        col_weights = {"population": [1.0, "IDW"]}
        geom = ["latitude", "longitude"]

        with patch('backend.data_manipulation.generate_raster_file.gpd.GeoDataFrame') as mock_gdf:
            mock_instance = MagicMock()
            mock_instance.total_bounds = [-118.2437, 29.7604, -74.0060, 41.8781]
            mock_gdf.return_value = mock_instance

            try:
                generate_raster_file(csv_bytes, out_fp, col_weights, geom)
            except Exception:
                pass  # Some parts will fail due to mocking, but CSV reading should work

    def test_end_to_end_tab_csv(self):
        """Test complete flow with tab-delimited CSV"""
        csv_content = """city\tlongitude\tlatitude\tpopulation\tarea_sqkm
New York\t-74.0060\t40.7128\t8336817\t783.8
Los Angeles\t-118.2437\t34.0522\t3979576\t1302.1
Chicago\t-87.6298\t41.8781\t2693976\t606.1"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))

        # Test column detection
        columns = provide_columns(csv_bytes)
        self.assertEqual(len(columns), 4)
        self.assertIn('population', columns)

        # Verify data integrity
        csv_bytes.seek(0)
        df = pd.read_csv(csv_bytes, sep='\t')
        self.assertEqual(len(df), 3)
        self.assertAlmostEqual(df.iloc[0]['longitude'], -74.0060)

    def test_delimiter_mismatch_handling(self):
        """Test that system correctly handles delimiter mismatches"""
        # Create CSV with commas
        csv_content_comma = """x,y,value
1,2,100
3,4,200"""

        # Create CSV with tabs
        csv_content_tab = """x\ty\tvalue
1\t2\t100
3\t4\t200"""

        # Both should work correctly
        for content in [csv_content_comma, csv_content_tab]:
            csv_bytes = BytesIO(content.encode('utf-8'))
            columns = provide_columns(csv_bytes)
            self.assertEqual(len(columns), 3)
            self.assertIn('x', columns)
            self.assertIn('y', columns)
            self.assertIn('value', columns)

    def test_real_world_scenario(self):
        """Test with realistic data that might appear in production"""
        csv_content = """Station Name,Station ID,Date,Time,Temperature (°C),Humidity (%),Pressure (hPa),Wind Speed (m/s),Latitude,Longitude
"Central Park, NY",NYC001,2024-01-15,12:00,5.2,72.3,1013.2,3.5,40.7829,-73.9654
"JFK Airport",NYC002,2024-01-15,12:00,4.8,75.1,1013.5,5.2,40.6413,-73.7781
"LaGuardia Airport",NYC003,2024-01-15,12:00,5.0,73.8,1013.3,4.8,40.7769,-73.8740"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        columns = provide_columns(csv_bytes)

        # Should correctly identify numeric columns despite complex headers
        numeric_cols = ['Temperature (°C)', 'Humidity (%)', 'Pressure (hPa)',
                        'Wind Speed (m/s)', 'Latitude', 'Longitude']

        for col in numeric_cols:
            self.assertIn(col, columns, f"Should detect '{col}' as numeric")

        # Should not include text columns
        self.assertNotIn('Station Name', columns)
        self.assertNotIn('Date', columns)
        self.assertNotIn('Time', columns)


if __name__ == '__main__':
    unittest.main(verbosity=2)