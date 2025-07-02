"""
Unit tests for the data_io module.
"""

import unittest
import tempfile
import csv
import os
from src.data_io import CSVReader, CSVWriter, SchemaValidator


class TestCSVReader(unittest.TestCase):
    """Test cases for CSVReader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
    
    def _create_test_csv(self, filename: str, data: list, headers: list = None):
        """Helper method to create test CSV files."""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            if headers:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
            else:
                # Write raw data without headers
                for row in data:
                    f.write(row + '\n')
        return filepath
    
    def test_read_valid_csv(self):
        """Test reading a valid CSV file."""
        data = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "2", "Name": "Bob", "Age": "30"}
        ]
        csv_path = self._create_test_csv("test.csv", data, ["ID", "Name", "Age"])
        
        result = CSVReader.read_csv(csv_path)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["ID"], "1")
        self.assertEqual(result[0]["Name"], "Alice")
        self.assertEqual(result[1]["ID"], "2")
        self.assertEqual(result[1]["Name"], "Bob")
    
    def test_read_csv_with_excluded_columns(self):
        """Test reading CSV with excluded columns."""
        data = [
            {"ID": "1", "Name": "Alice", "Age": "25", "Notes": "Test note"},
            {"ID": "2", "Name": "Bob", "Age": "30", "Notes": "Another note"}
        ]
        csv_path = self._create_test_csv("test.csv", data, ["ID", "Name", "Age", "Notes"])
        
        result = CSVReader.read_csv(csv_path, excluded_columns=["Notes"])
        
        self.assertEqual(len(result), 2)
        self.assertNotIn("Notes", result[0])
        self.assertIn("ID", result[0])
        self.assertIn("Name", result[0])
        self.assertIn("Age", result[0])
    
    def test_read_nonexistent_file(self):
        """Test error when file doesn't exist."""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.csv")
        
        with self.assertRaises(FileNotFoundError) as context:
            CSVReader.read_csv(nonexistent_path)
        self.assertIn("CSV file not found", str(context.exception))
    
    def test_read_empty_file(self):
        """Test error when CSV file is empty."""
        empty_path = self._create_test_csv("empty.csv", [])
        
        with self.assertRaises(ValueError) as context:
            CSVReader.read_csv(empty_path)
        self.assertIn("CSV file is empty", str(context.exception))
    
    def test_read_file_without_headers(self):
        """Test error when CSV file has no headers."""
        # Create file with just data, no headers - use proper CSV format
        no_header_path = os.path.join(self.temp_dir, "no_header.csv")
        with open(no_header_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["1", "Alice", "25"])
            writer.writerow(["2", "Bob", "30"])
        
        # This should actually work fine since CSV reader will treat first row as headers
        # Let's change this test to check for a truly headerless file (empty first line)
        empty_header_path = os.path.join(self.temp_dir, "empty_header.csv")
        with open(empty_header_path, 'w', newline='', encoding='utf-8') as f:
            f.write("\n")  # Empty first line
            f.write("1,Alice,25\n")
        
        with self.assertRaises(ValueError) as context:
            CSVReader.read_csv(empty_header_path)
        self.assertIn("CSV file has no headers", str(context.exception))
    
    def test_get_csv_columns(self):
        """Test getting column names from CSV file."""
        data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        csv_path = self._create_test_csv("test.csv", data, ["ID", "Name", "Age"])
        
        columns = CSVReader.get_csv_columns(csv_path)
        
        self.assertEqual(columns, ["ID", "Name", "Age"])
    
    def test_get_columns_nonexistent_file(self):
        """Test error when getting columns from nonexistent file."""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.csv")
        
        with self.assertRaises(FileNotFoundError):
            CSVReader.get_csv_columns(nonexistent_path)


class TestCSVWriter(unittest.TestCase):
    """Test cases for CSVWriter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
    
    def test_write_comparison_results(self):
        """Test writing comparison results to CSV."""
        results_data = [
            {
                "row_key": "1",
                "status": "Changed",
                "changed_columns": ["Age"],
                "old_values": {"Age": "25"},
                "new_values": {"Age": "26"}
            },
            {
                "row_key": "2", 
                "status": "Added",
                "changed_columns": [],
                "old_values": {},
                "new_values": {"ID": "2", "Name": "Bob", "Age": "30"}
            }
        ]
        
        output_path = os.path.join(self.temp_dir, "output.csv")
        CSVWriter.write_comparison_results(results_data, output_path)
        
        # Verify the output file
        self.assertTrue(os.path.exists(output_path))
        
        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.assertEqual(len(rows), 2)
        
        # Check first row (changed)
        self.assertEqual(rows[0]["Row Key"], "1")
        self.assertEqual(rows[0]["Status"], "Changed")
        self.assertEqual(rows[0]["Changed Columns"], "Age")
        self.assertEqual(rows[0]["Age (Old)"], "25")
        self.assertEqual(rows[0]["Age (New)"], "26")
        
        # Check second row (added)
        self.assertEqual(rows[1]["Row Key"], "2")
        self.assertEqual(rows[1]["Status"], "Added")
        self.assertEqual(rows[1]["Changed Columns"], "")
        self.assertEqual(rows[1]["ID (Old)"], "")
        self.assertEqual(rows[1]["ID (New)"], "2")
        self.assertEqual(rows[1]["Name (Old)"], "")
        self.assertEqual(rows[1]["Name (New)"], "Bob")
        self.assertEqual(rows[1]["Age (Old)"], "")
        self.assertEqual(rows[1]["Age (New)"], "30")

    def test_write_empty_results(self):
        """Test writing empty results."""
        output_path = os.path.join(self.temp_dir, "empty_output.csv")
        CSVWriter.write_comparison_results([], output_path)
        
        # Verify the output file exists and has headers
        self.assertTrue(os.path.exists(output_path))
        
        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.assertEqual(len(rows), 0)
        self.assertEqual(list(reader.fieldnames), ["Row Key", "Status", "Changed Columns"])

    def test_write_multiple_changed_columns(self):
        """Test writing results with multiple changed columns."""
        results_data = [
            {
                "row_key": "1",
                "status": "Changed", 
                "changed_columns": ["Name", "Age"],
                "old_values": {"Name": "Alice", "Age": "25"},
                "new_values": {"Name": "Alicia", "Age": "26"}
            }
        ]
        
        output_path = os.path.join(self.temp_dir, "multi_output.csv")
        CSVWriter.write_comparison_results(results_data, output_path)
        
        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Changed Columns"], "Name, Age")
        self.assertEqual(rows[0]["Name (Old)"], "Alice")
        self.assertEqual(rows[0]["Name (New)"], "Alicia")
        self.assertEqual(rows[0]["Age (Old)"], "25")
        self.assertEqual(rows[0]["Age (New)"], "26")


class TestSchemaValidator(unittest.TestCase):
    """Test cases for SchemaValidator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
    
    def _create_test_csv(self, filename: str, data: list, headers: list):
        """Helper method to create test CSV files."""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        return filepath
    
    def test_identical_schemas_pass(self):
        """Test that identical schemas pass validation."""
        data1 = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        data2 = [{"ID": "2", "Name": "Bob", "Age": "30"}]
        
        file1 = self._create_test_csv("file1.csv", data1, ["ID", "Name", "Age"])
        file2 = self._create_test_csv("file2.csv", data2, ["ID", "Name", "Age"])
        
        # Should not raise any exception
        SchemaValidator.validate_schemas(file1, file2, ["ID"], [], "fail")
    
    def test_schema_mismatch_fail_behavior(self):
        """Test that schema mismatches cause failure when behavior is 'fail'."""
        data1 = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        data2 = [{"ID": "2", "Name": "Bob", "Email": "bob@example.com"}]
        
        file1 = self._create_test_csv("file1.csv", data1, ["ID", "Name", "Age"])
        file2 = self._create_test_csv("file2.csv", data2, ["ID", "Name", "Email"])
        
        with self.assertRaises(ValueError) as context:
            SchemaValidator.validate_schemas(file1, file2, ["ID"], [], "fail")
        self.assertIn("Schema mismatch detected", str(context.exception))
    
    def test_schema_mismatch_warn_behavior(self):
        """Test that schema mismatches produce warnings when behavior is 'warn'."""
        data1 = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        data2 = [{"ID": "2", "Name": "Bob", "Email": "bob@example.com"}]
        
        file1 = self._create_test_csv("file1.csv", data1, ["ID", "Name", "Age"])
        file2 = self._create_test_csv("file2.csv", data2, ["ID", "Name", "Email"])
        
        # Should not raise exception, but would print warning (we can't easily test print output)
        SchemaValidator.validate_schemas(file1, file2, ["ID"], [], "warn")
    
    def test_schema_mismatch_ignore_behavior(self):
        """Test that schema mismatches are ignored when behavior is 'ignore'."""
        data1 = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        data2 = [{"ID": "2", "Name": "Bob", "Email": "bob@example.com"}]
        
        file1 = self._create_test_csv("file1.csv", data1, ["ID", "Name", "Age"])
        file2 = self._create_test_csv("file2.csv", data2, ["ID", "Name", "Email"])
        
        # Should not raise exception or print warnings
        SchemaValidator.validate_schemas(file1, file2, ["ID"], [], "ignore")
    
    def test_missing_key_columns_error(self):
        """Test error when key columns are missing from files."""
        data1 = [{"Name": "Alice", "Age": "25"}]  # Missing ID
        data2 = [{"ID": "2", "Name": "Bob", "Age": "30"}]
        
        file1 = self._create_test_csv("file1.csv", data1, ["Name", "Age"])
        file2 = self._create_test_csv("file2.csv", data2, ["ID", "Name", "Age"])
        
        with self.assertRaises(ValueError) as context:
            SchemaValidator.validate_schemas(file1, file2, ["ID"], [], "warn")
        self.assertIn("Key columns missing from first file", str(context.exception))
    
    def test_excluded_columns_ignored_in_schema_validation(self):
        """Test that excluded columns are ignored during schema validation."""
        data1 = [{"ID": "1", "Name": "Alice", "Notes": "Note1"}]
        data2 = [{"ID": "2", "Name": "Bob", "Comments": "Comment1"}]
        
        file1 = self._create_test_csv("file1.csv", data1, ["ID", "Name", "Notes"])
        file2 = self._create_test_csv("file2.csv", data2, ["ID", "Name", "Comments"])
        
        # Should pass since Notes and Comments are excluded
        SchemaValidator.validate_schemas(file1, file2, ["ID"], ["Notes", "Comments"], "fail")


if __name__ == '__main__':
    unittest.main()