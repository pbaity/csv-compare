"""
Unit tests for the comparison module.
"""

import unittest
from src.comparison import DataComparator


class TestDataComparator(unittest.TestCase):
    """Test cases for DataComparator class."""
    
    def setUp(self):
        self.comparator = DataComparator({"key_columns": ["ID"]})
        self.multi_key_comparator = DataComparator({"key_columns": ["ID", "Name"]})

    def test_identical_datasets(self):
        data = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "2", "Name": "Bob", "Age": "30"}
        ]
        results, _ = self.comparator.compare(data, data)
        self.assertEqual(len(results), 0)

    def test_added_row(self):
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "2", "Name": "Bob", "Age": "30"}
        ]
        results, _ = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["Status"], "Added")
        self.assertEqual(results[0]["Row Key"], "2")
        self.assertEqual(results[0]["Name (New)"], "Bob")
        self.assertEqual(results[0]["Age (New)"], "30")

    def test_removed_row(self):
        old_data = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "2", "Name": "Bob", "Age": "30"}
        ]
        new_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        results, _ = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["Status"], "Removed")
        self.assertEqual(results[0]["Row Key"], "2")
        self.assertEqual(results[0]["Name (Old)"], "Bob")
        self.assertEqual(results[0]["Age (Old)"], "30")

    def test_changed_row(self):
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [{"ID": "1", "Name": "Alice", "Age": "26"}]
        results, _ = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["Status"], "Changed")
        self.assertEqual(results[0]["Row Key"], "1")
        self.assertIn("Age", results[0]["Changed Columns"])
        self.assertEqual(results[0]["Age (Old)"], "25")
        self.assertEqual(results[0]["Age (New)"], "26")

    def test_multiple_key_columns(self):
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [{"ID": "1", "Name": "Alice", "Age": "26"}]
        results, _ = self.multi_key_comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["Row Key"], "1|Alice")

    def test_data_type_mismatch_comparison(self):
        old_data = [{"ID": "1", "Score": "100"}]
        new_data = [{"ID": "1", "Score": 100}]
        results, _ = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 0)

    def test_missing_key_column_error(self):
        old_data = [{"Name": "Alice", "Age": "25"}]
        new_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        with self.assertRaises(ValueError) as context:
            self.comparator.compare(old_data, new_data)
        self.assertIn("Missing key columns", str(context.exception))

    def test_duplicate_key_error(self):
        data_with_duplicates = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "1", "Name": "Bob", "Age": "30"}
        ]
        with self.assertRaises(ValueError) as context:
            self.comparator.compare(data_with_duplicates, [])
        self.assertIn("Duplicate row key", str(context.exception))

    def test_empty_datasets(self):
        results, _ = self.comparator.compare([], [])
        self.assertEqual(len(results), 0)

    def test_column_added_to_new_dataset(self):
        old_data = [{"ID": "1", "Name": "Alice"}]
        new_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        results, _ = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["Status"], "Changed")
        self.assertIn("Age", results[0]["Changed Columns"])
        self.assertEqual(results[0]["Age (Old)"], "")
        self.assertEqual(results[0]["Age (New)"], "25")

    def test_column_removed_from_new_dataset(self):
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [{"ID": "1", "Name": "Alice"}]
        results, _ = self.comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["Status"], "Changed")
        self.assertIn("Age", results[0]["Changed Columns"])
        self.assertEqual(results[0]["Age (Old)"], "25")
        self.assertEqual(results[0]["Age (New)"], "")

    def test_key_columns_excluded_from_comparison(self):
        old_data = [{"ID": "1", "Name": "Alice", "Age": "25"}]
        new_data = [{"ID": "1", "Name": "Bob", "Age": "25"}]
        name_key_comparator = DataComparator({"key_columns": ["ID", "Name"]})
        results, _ = name_key_comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 2)
        statuses = [result["Status"] for result in results]
        self.assertIn("Removed", statuses)
        self.assertIn("Added", statuses)

    def test_duplicates_collected_when_fail_on_duplicate_keys_false(self):
        comparator = DataComparator({"key_columns": ["ID"], "fail_on_duplicate_keys": False})
        data_with_duplicates = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "1", "Name": "Bob", "Age": "30"}
        ]
        results, duplicates = comparator.compare(data_with_duplicates, [])
        self.assertEqual(len(results), 0)
        self.assertEqual(len(duplicates), 2)
        self.assertEqual(duplicates[0]["Name"], "Alice")
        self.assertEqual(duplicates[1]["Name"], "Bob")

    def test_all_duplicates_collected_multiple(self):
        comparator = DataComparator({"key_columns": ["ID"], "fail_on_duplicate_keys": False})
        data_with_duplicates = [
            {"ID": "1", "Name": "Alice", "Age": "25"},
            {"ID": "1", "Name": "Bob", "Age": "30"},
            {"ID": "1", "Name": "Carol", "Age": "35"}
        ]
        results, duplicates = comparator.compare(data_with_duplicates, [])
        self.assertEqual(len(results), 0)
        self.assertEqual(len(duplicates), 3)
        names = [row["Name"] for row in duplicates]
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)
        self.assertIn("Carol", names)

    def test_duplicates_in_both_old_and_new(self):
        comparator = DataComparator({"key_columns": ["ID"], "fail_on_duplicate_keys": False})
        old_data = [
            {"ID": "1", "Name": "Alice"},
            {"ID": "1", "Name": "Bob"}
        ]
        new_data = [
            {"ID": "2", "Name": "Carol"},
            {"ID": "2", "Name": "Dave"}
        ]
        results, duplicates = comparator.compare(old_data, new_data)
        self.assertEqual(len(results), 0)
        self.assertEqual(len(duplicates), 4)
        old_names = [row["Name"] for row in duplicates if row["ID"] == "1"]
        new_names = [row["Name"] for row in duplicates if row["ID"] == "2"]
        self.assertCountEqual(old_names, ["Alice", "Bob"])
        self.assertCountEqual(new_names, ["Carol", "Dave"])

    def test_no_duplicates_when_all_keys_unique(self):
        comparator = DataComparator({"key_columns": ["ID"], "fail_on_duplicate_keys": False})
        data = [
            {"ID": "1", "Name": "Alice"},
            {"ID": "2", "Name": "Bob"}
        ]
        results, duplicates = comparator.compare(data, [])
        self.assertEqual(len(duplicates), 0)

if __name__ == '__main__':
    unittest.main()