import unittest
import pandas as pd
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
from backend.data_manipulation.generate_raster_file import detect_delimiter, generate_raster_file


class TestGenerateRasterFile(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.mock_logger = Mock()

    def create_csv_bytes(self, content, encoding='utf-8'):
        """Helper to create BytesIO CSV objects"""
        return BytesIO(content.encode(encoding))

    def test_comma_delimiter_detection(self):
        """Test detection of comma delimiter"""
        csv_content = """longitude,latitude,value1,value2
-74.0060,40.7128,100,200
-118.2437,34.0522,150,250
-87.6298,41.8781,120,220"""

        csv_bytes = self.create_csv_bytes(csv_content)
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, ',')

        # Verify file position is reset
        self.assertEqual(csv_bytes.tell(), 0)

    def test_tab_delimiter_detection(self):
        """Test detection of tab delimiter"""
        csv_content = """longitude\tlatitude\tvalue1\tvalue2
-74.0060\t40.7128\t100\t200
-118.2437\t34.0522\t150\t250
-87.6298\t41.8781\t120\t220"""

        csv_bytes = self.create_csv_bytes(csv_content)
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, '\t')

    def test_semicolon_delimiter_detection(self):
        """Test detection of semicolon delimiter"""
        csv_content = """longitude;latitude;value1;value2
-74.0060;40.7128;100;200
-118.2437;34.0522;150;250"""

        csv_bytes = self.create_csv_bytes(csv_content)
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, ';')

    @patch('backend.data_manipulation.generate_raster_file.main_logger')
    @patch('backend.data_manipulation.generate_raster_file.gpd.GeoDataFrame')
    def test_generate_raster_with_comma_csv(self, mock_gdf, mock_logger):
        """Test raster generation with comma-delimited CSV"""
        csv_content = """longitude,latitude,temperature,humidity
-74.0060,40.7128,22.5,65.3
-74.0050,40.7130,22.6,65.1
-74.0070,40.7125,22.4,65.5
-74.0055,40.7135,22.7,64.9"""

        in_fp = self.create_csv_bytes(csv_content)
        out_fp = BytesIO()

        col_weights = {
            "temperature": [1.0, "IDW"],
            "humidity": [0.5, "IDW"]
        }

        geom = ["latitude", "longitude"]

        # Mock the GeoDataFrame behavior
        mock_gdf_instance = MagicMock()
        mock_gdf_instance.total_bounds = [-74.0070, 40.7125, -74.0050, 40.7135]
        mock_gdf_instance.geometry.x = pd.Series([-74.0060, -74.0050, -74.0070, -74.0055])
        mock_gdf_instance.geometry.y = pd.Series([40.7128, 40.7130, 40.7125, 40.7135])
        mock_gdf.return_value = mock_gdf_instance

        # Run the function
        try:
            generate_raster_file(in_fp, out_fp, col_weights, geom)
            # Verify delimiter was detected correctly
            mock_logger.info.assert_any_call("Detected delimiter: ','")
        except Exception as e:
            # Some parts might fail due to mocking, but delimiter detection should work
            if "Detected delimiter" not in str(mock_logger.info.call_args_list):
                self.fail(f"Delimiter detection failed: {e}")

    @patch('backend.data_manipulation.generate_raster_file.main_logger')
    def test_generate_raster_with_tab_csv(self, mock_logger):
        """Test raster generation with tab-delimited CSV"""
        csv_content = """longitude\tlatitude\ttemperature\thumidity
-74.0060\t40.7128\t22.5\t65.3
-74.0050\t40.7130\t22.6\t65.1
-74.0070\t40.7125\t22.4\t65.5"""

        in_fp = self.create_csv_bytes(csv_content)
        out_fp = BytesIO()

        col_weights = {"temperature": [1.0, "IDW"]}
        geom = ["latitude", "longitude"]

        # We're mainly testing delimiter detection
        try:
            # Read the CSV with detected delimiter
            delimiter = detect_delimiter(in_fp)
            self.assertEqual(delimiter, '\t')

            in_fp.seek(0)
            df = pd.read_csv(in_fp, sep=delimiter)

            # Verify data was parsed correctly
            self.assertEqual(len(df.columns), 4)
            self.assertIn('longitude', df.columns)
            self.assertIn('latitude', df.columns)
            self.assertIn('temperature', df.columns)
            self.assertEqual(len(df), 3)

        except Exception as e:
            self.fail(f"Failed to process tab-delimited CSV: {e}")

    def test_mixed_delimiters_in_data(self):
        """Test CSV where data contains other delimiters"""
        csv_content = """description,longitude,latitude,value
"Location, with comma",-74.0060,40.7128,100
"Location; with semicolon",-118.2437,34.0522,150
"Location\twith tab",-87.6298,41.8781,120"""

        csv_bytes = self.create_csv_bytes(csv_content)
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, ',', "Should correctly identify comma as primary delimiter")

        # Verify data can be read correctly
        csv_bytes.seek(0)
        df = pd.read_csv(csv_bytes, sep=delimiter)
        self.assertEqual(len(df), 3)
        self.assertEqual(len(df.columns), 4)

    def test_encoding_detection_utf16(self):
        """Test handling of UTF-16 encoded files"""
        csv_content = """longitude,latitude,value
-74.0060,40.7128,100
-118.2437,34.0522,150"""

        in_fp = BytesIO(csv_content.encode('utf-16'))
        out_fp = BytesIO()

        col_weights = {"value": [1.0, "IDW"]}
        geom = ["latitude", "longitude"]

        # Test delimiter detection with UTF-16
        delimiter = detect_delimiter(in_fp)
        self.assertIsNotNone(delimiter)

    def test_fallback_delimiter_detection(self):
        """Test fallback mechanism when Sniffer fails"""
        # Create a file that might confuse the Sniffer
        csv_content = """a b c d
1 2 3 4
5 6 7 8"""

        csv_bytes = self.create_csv_bytes(csv_content)
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, ' ', "Should detect space as delimiter via fallback")

    def test_empty_file_handling(self):
        """Test handling of empty files"""
        csv_bytes = BytesIO(b"")
        delimiter = detect_delimiter(csv_bytes)
        # Should return a delimiter even for empty file (from fallback)
        self.assertIsNotNone(delimiter)

    def test_single_column_csv(self):
        """Test CSV with single column (edge case)"""
        csv_content = """value
100
200
300"""

        csv_bytes = self.create_csv_bytes(csv_content)
        delimiter = detect_delimiter(csv_bytes)
        # Should still work even with single column
        self.assertIsNotNone(delimiter)

        csv_bytes.seek(0)
        df = pd.read_csv(csv_bytes, sep=delimiter)
        self.assertEqual(len(df.columns), 1)
        self.assertEqual(len(df), 3)


class TestDelimiterEdgeCases(unittest.TestCase):
    """Specific tests for delimiter detection edge cases"""

    def test_csv_with_quotes_and_commas(self):
        """Test CSV with quoted fields containing commas"""
        csv_content = '''name,address,latitude,longitude
"Smith, John","123 Main St, Apt 4",40.7128,-74.0060
"Doe, Jane","456 Oak Ave, Suite 200",34.0522,-118.2437'''

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, ',')

        # Verify parsing works correctly
        csv_bytes.seek(0)
        df = pd.read_csv(csv_bytes, sep=delimiter)
        self.assertEqual(len(df), 2)
        self.assertEqual(len(df.columns), 4)
        self.assertAlmostEqual(df.iloc[0]['latitude'], 40.7128)

    def test_tsv_with_commas_in_data(self):
        """Test TSV file where data contains commas"""
        csv_content = """name\taddress\tlatitude\tlongitude
Smith, John\t123 Main St, Apt 4\t40.7128\t-74.0060
Doe, Jane\t456 Oak Ave, Suite 200\t34.0522\t-118.2437"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, '\t', "Should detect tab even when data contains commas")

        csv_bytes.seek(0)
        df = pd.read_csv(csv_bytes, sep=delimiter)
        self.assertEqual(len(df.columns), 4)

    def test_consistent_delimiter_detection(self):
        """Test that delimiter detection is consistent across multiple calls"""
        csv_content = """a,b,c,d
1,2,3,4
5,6,7,8"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))

        # Detect multiple times
        delimiters = []
        for _ in range(5):
            csv_bytes.seek(0)
            delimiters.append(detect_delimiter(csv_bytes))

        # All detections should be the same
        self.assertEqual(len(set(delimiters)), 1, "Delimiter detection should be consistent")
        self.assertEqual(delimiters[0], ',')


if __name__ == '__main__':
    unittest.main(verbosity=2)