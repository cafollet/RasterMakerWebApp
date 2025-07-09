import unittest
from io import BytesIO
import tempfile
import os
from backend.data_manipulation.provide_columns import provide_columns, detect_delimiter


class TestProvideColumns(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.temp_files = []

    def tearDown(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def create_temp_file(self, content, encoding='utf-8'):
        """Helper to create temporary files"""
        temp = tempfile.NamedTemporaryFile(mode='w', encoding=encoding, delete=False, suffix='.csv')
        temp.write(content)
        temp.close()
        self.temp_files.append(temp.name)
        return temp.name

    def test_comma_delimiter_detection(self):
        """Test CSV with comma delimiter"""
        csv_content = """name,age,salary,latitude,longitude
        John Doe,30,50000.50,40.7128,-74.0060
Jane Smith,25,60000.75,34.0522,-118.2437
Bob Johnson,35,55000.00,41.8781,-87.6298"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, ',', "Should detect comma as delimiter")

        columns = provide_columns(csv_bytes)
        self.assertIn('age', columns)
        self.assertIn('salary', columns)
        self.assertIn('latitude', columns)
        self.assertIn('longitude', columns)
        self.assertNotIn('name', columns, "String column should not be included")

    def test_tab_delimiter_detection(self):
        """Test CSV with tab delimiter"""
        csv_content = """name\tage\tsalary\tlatitude\tlongitude
John Doe\t30\t50000.50\t40.7128\t-74.0060
Jane Smith\t25\t60000.75\t34.0522\t-118.2437
Bob Johnson\t35\t55000.00\t41.8781\t-87.6298"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, '\t', "Should detect tab as delimiter")

        columns = provide_columns(csv_bytes)
        self.assertIn('age', columns)
        self.assertIn('salary', columns)
        self.assertIn('latitude', columns)
        self.assertIn('longitude', columns)

    def test_semicolon_delimiter_detection(self):
        """Test CSV with semicolon delimiter"""
        csv_content = """name;age;salary;latitude;longitude
John Doe;30;50000.50;40.7128;-74.0060
Jane Smith;25;60000.75;34.0522;-118.2437"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, ';', "Should detect semicolon as delimiter")

        columns = provide_columns(csv_bytes)
        self.assertEqual(len(columns), 4, "Should find 4 numeric columns")

    def test_pipe_delimiter_detection(self):
        """Test CSV with pipe delimiter"""
        csv_content = """name|age|salary|latitude|longitude
John Doe|30|50000.50|40.7128|-74.0060
Jane Smith|25|60000.75|34.0522|-118.2437"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        delimiter = detect_delimiter(csv_bytes)
        self.assertEqual(delimiter, '|', "Should detect pipe as delimiter")

        columns = provide_columns(csv_bytes)
        self.assertEqual(len(columns), 4, "Should find 4 numeric columns")

    def test_mixed_content_with_commas(self):
        """Test CSV with commas in data and comma delimiter"""
        csv_content = """description,value,latitude,longitude
"Item with, comma",100.50,40.7128,-74.0060
"Another, item, here",200.75,34.0522,-118.2437
"Simple item",300.00,41.8781,-87.6298"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        columns = provide_columns(csv_bytes)
        self.assertIn('value', columns)
        self.assertIn('latitude', columns)
        self.assertIn('longitude', columns)
        self.assertEqual(len(columns), 3)

    def test_utf16_encoding(self):
        """Test CSV with UTF-16 encoding"""
        csv_content = """name,age,salary,latitude,longitude
John Doe,30,50000.50,40.7128,-74.0060
Jane Smith,25,60000.75,34.0522,-118.2437"""

        csv_bytes = BytesIO(csv_content.encode('utf-16'))
        columns = provide_columns(csv_bytes)
        self.assertIn('age', columns)
        self.assertIn('salary', columns)
        self.assertEqual(len(columns), 4)

    def test_latin1_encoding(self):
        """Test CSV with Latin-1 encoding and special characters"""
        csv_content = """name,age,salary,latitude,longitude
José García,30,50000.50,40.7128,-74.0060
François Müller,25,60000.75,34.0522,-118.2437"""

        csv_bytes = BytesIO(csv_content.encode('latin-1'))
        columns = provide_columns(csv_bytes)
        self.assertIn('age', columns)
        self.assertIn('salary', columns)
        self.assertEqual(len(columns), 4)

    def test_empty_file(self):
        """Test handling of empty file"""
        csv_bytes = BytesIO(b"")
        with self.assertRaises(ValueError):
            provide_columns(csv_bytes)

    def test_no_numeric_columns(self):
        """Test CSV with no numeric columns"""
        csv_content = """name,city,country
John Doe,New York,USA
Jane Smith,Los Angeles,USA"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        columns = provide_columns(csv_bytes)
        self.assertEqual(len(columns), 0, "Should return empty list for no numeric columns")

    def test_mixed_delimiters_in_data(self):
        """Test CSV where data contains other potential delimiters"""
        csv_content = """description,code,value,latitude,longitude
"Tab\there",ABC,100.50,40.7128,-74.0060
"Semicolon;here",DEF,200.75,34.0522,-118.2437
"Pipe|here",GHI,300.00,41.8781,-87.6298"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        columns = provide_columns(csv_bytes)
        self.assertIn('value', columns)
        self.assertIn('latitude', columns)
        self.assertIn('longitude', columns)
        self.assertNotIn('code', columns)

    def test_real_world_csv_with_headers(self):
        """Test realistic CSV with various data types"""
        csv_content = """ID,Name,Date,Temperature,Humidity,Pressure,Location_Lat,Location_Lon,Status
1,Station Alpha,2024-01-01,22.5,65.3,1013.25,40.7128,-74.0060,Active
2,Station Beta,2024-01-02,23.1,62.7,1012.80,34.0522,-118.2437,Active
3,Station Gamma,2024-01-03,21.9,68.2,1014.10,41.8781,-87.6298,Inactive"""

        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        columns = provide_columns(csv_bytes)

        expected_columns = ['ID', 'Temperature', 'Humidity', 'Pressure', 'Location_Lat', 'Location_Lon']
        for col in expected_columns:
            self.assertIn(col, columns, f"Should include numeric column {col}")

        self.assertNotIn('Name', columns)
        self.assertNotIn('Date', columns)
        self.assertNotIn('Status', columns)


if __name__ == '__main__':
    unittest.main(verbosity=2)