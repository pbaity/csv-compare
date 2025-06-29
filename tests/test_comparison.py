"""
Unit tests for the comparison module.
"""

import unittest
from src.comparison import CSVComparator, RowStatus, ComparisonResult


class TestCSVComparator(unittest.TestCase):
    """Test cases for CSVComparator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.comparator = CSVComparator(key_columns=["ID"])
        self.multi_key_comparator = CSVComparator(key_columns=["ID", "Name"])
    
    def test_identical_datasets(self):
        """Test comparison of identical datasets."""
        data = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "2", "Name": "Bob", "Age": "30"}
        ]
        
        results = self.comparator.compare(data, data)
        self.assertEqual(len(results), 0)
    
    def test_added_row(self):
        """Test detection of added rows."""
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "2", "Name": "Bob", "Age": "30"}
        ]
        
        results = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, RowStatus.ADDED)
        self.assertEqual(results[0].row_key, "2")
        self.assertEqual(results[0].new_values, {"Name": "Bob", "Age": "30"})
    
    def test_removed_row(self):
        """Test detection of removed rows."""
        old_data = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "2", "Name": "Bob", "Age": "30"}
        ]
        new_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        
        results = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, RowStatus.REMOVED)
        self.assertEqual(results[0].row_key, "2")
        self.assertEqual(results[0].old_values, {"Name": "Bob", "Age": "30"})
    
    def test_changed_row(self):
        """Test detection of changed rows."""
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [{"ID": "1", "Name": "Alice", "Age": "26"}]
        
        results = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, RowStatus.CHANGED)
        self.assertEqual(results[0].row_key, "1")
        self.assertEqual(results[0].changed_columns, ["Age"])
        self.assertEqual(results[0].old_values, {"Age": "25"})
        self.assertEqual(results[0].new_values, {"Age": "26"})
    
    def test_multiple_key_columns(self):
        """Test comparison with multiple key columns."""
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [{"ID": "1", "Name": "Alice", "Age": "26"}]
        
        results = self.multi_key_comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].row_key, "1|Alice")
    
    def test_data_type_mismatch_comparison(self):
        """Test that different data types are compared as strings."""
        old_data = [{"ID": "1", "Score": "100"}]
        new_data = [{"ID": "1", "Score": 100}]  # Integer instead of string
        
        results = self.comparator.compare(old_data, new_data)
        # Should be no changes since "100" == str(100)
        self.assertEqual(len(results), 0)
    
    def test_missing_key_column_error(self):
        """Test error when key column is missing."""
        old_data = [{"Name": "Alice", "Age": "25"}]  # Missing ID column
        new_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        
        with self.assertRaises(ValueError) as context:
            self.comparator.compare(old_data, new_data)
        self.assertIn("Missing key columns", str(context.exception))
    
    def test_duplicate_key_error(self):
        """Test error when duplicate keys exist."""
        data_with_duplicates = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "1", "Name": "Bob", "Age": "30"}  # Duplicate ID
        ]
        
        with self.assertRaises(ValueError) as context:
            self.comparator.compare(data_with_duplicates, [])
        self.assertIn("Duplicate row key", str(context.exception))
    
    def test_empty_datasets(self):
        """Test comparison of empty datasets."""
        results = self.comparator.compare([], [])
        self.assertEqual(len(results), 0)
    
    def test_include_unchanged_columns(self):
        """Test including unchanged columns in output."""
        comparator_with_unchanged = CSVComparator(key_columns=["ID"], include_unchanged_columns=True)
        
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [{"ID": "1", "Name": "Alice", "Age": "26"}]
        
        results = comparator_with_unchanged.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].changed_columns, ["Age"])
        
        # Changed columns should be in old/new values
        self.assertIn("Age", results[0].old_values)
        self.assertIn("Age", results[0].new_values)
        self.assertEqual(results[0].old_values["Age"], "25")
        self.assertEqual(results[0].new_values["Age"], "26")
        
        # Unchanged columns should be in unchanged_values
        self.assertIn("Name", results[0].unchanged_values)
        self.assertEqual(results[0].unchanged_values["Name"], "Alice")
    
    def test_column_added_to_new_dataset(self):
        """Test handling when new dataset has additional columns."""
        old_data = [{"ID": "1", "Name": "Alice"}]
        new_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        
        results = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, RowStatus.CHANGED)
        self.assertEqual(results[0].changed_columns, ["Age"])
        self.assertEqual(results[0].old_values, {"Age": ""})  # Missing value becomes empty string
        self.assertEqual(results[0].new_values, {"Age": "25"})
    
    def test_column_removed_from_new_dataset(self):
        """Test handling when new dataset is missing columns."""
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [{"ID": "1", "Name": "Alice"}]
        
        results = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, RowStatus.CHANGED)
        self.assertEqual(results[0].changed_columns, ["Age"])
        self.assertEqual(results[0].old_values, {"Age": "25"})
        self.assertEqual(results[0].new_values, {"Age": ""})  # Missing value becomes empty string
    
    def test_key_columns_excluded_from_comparison(self):
        """Test that key columns are not included in change detection."""
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [{"ID": "1", "Name": "Bob", "Age": "25"}]  # Name changed but it's a key column
        
        # Make Name a key column
        name_key_comparator = CSVComparator(key_columns=["ID", "Name"])
        
        # This should be treated as different rows (one removed, one added)
        results = name_key_comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 2)
        
        # Check that we have one removed and one added
        statuses = [result.status for result in results]
        self.assertIn(RowStatus.REMOVED, statuses)
        self.assertIn(RowStatus.ADDED, statuses)


if __name__ == '__main__':
    unittest.main()