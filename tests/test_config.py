"""
Unit tests for the config module.
"""

import unittest
import tempfile
import json
import os
from src.config import ConfigLoader, ComparisonConfig


class TestComparisonConfig(unittest.TestCase):
    """Test cases for ComparisonConfig class."""
    
    def test_valid_config_creation(self):
        """Test creating a valid configuration."""
        config = ComparisonConfig(
            key_columns=["ID"],
            excluded_columns=["Notes"],
            schema_mismatch_behavior="warn",
            include_unchanged_columns=False
        )
        
        self.assertEqual(config.key_columns, ["ID"])
        self.assertEqual(config.excluded_columns, ["Notes"])
        self.assertEqual(config.schema_mismatch_behavior, "warn")
        self.assertFalse(config.include_unchanged_columns)
    
    def test_empty_key_columns_error(self):
        """Test error when key_columns is empty."""
        with self.assertRaises(ValueError) as context:
            ComparisonConfig(
                key_columns=[],
                excluded_columns=[],
                schema_mismatch_behavior="warn",
                include_unchanged_columns=False
            )
        self.assertIn("key_columns cannot be empty", str(context.exception))
    
    def test_invalid_schema_behavior_error(self):
        """Test error when schema_mismatch_behavior is invalid."""
        with self.assertRaises(ValueError) as context:
            ComparisonConfig(
                key_columns=["ID"],
                excluded_columns=[],
                schema_mismatch_behavior="invalid",
                include_unchanged_columns=False
            )
        self.assertIn("schema_mismatch_behavior must be one of", str(context.exception))
    
    def test_invalid_key_columns_type_error(self):
        """Test error when key_columns is not a list."""
        with self.assertRaises(ValueError) as context:
            ComparisonConfig(
                key_columns="ID",  # Should be a list
                excluded_columns=[],
                schema_mismatch_behavior="warn",
                include_unchanged_columns=False
            )
        self.assertIn("key_columns must be a list", str(context.exception))


class TestConfigLoader(unittest.TestCase):
    """Test cases for ConfigLoader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
    
    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_data = {
            "key_columns": ["ID", "Name"],
            "excluded_columns": ["Notes"],
            "schema_mismatch_behavior": "fail",
            "include_unchanged_columns": True
        }
        
        config_path = os.path.join(self.temp_dir, "test_config.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        config = ConfigLoader.load_config(config_path)
        
        self.assertEqual(config.key_columns, ["ID", "Name"])
        self.assertEqual(config.excluded_columns, ["Notes"])
        self.assertEqual(config.schema_mismatch_behavior, "fail")
        self.assertTrue(config.include_unchanged_columns)
    
    def test_load_config_with_defaults(self):
        """Test loading configuration with default values."""
        config_data = {
            "key_columns": ["ID"]
            # Other fields should use defaults
        }
        
        config_path = os.path.join(self.temp_dir, "minimal_config.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        config = ConfigLoader.load_config(config_path)
        
        self.assertEqual(config.key_columns, ["ID"])
        self.assertEqual(config.excluded_columns, [])  # Default
        self.assertEqual(config.schema_mismatch_behavior, "warn")  # Default
        self.assertFalse(config.include_unchanged_columns)  # Default
    
    def test_missing_file_error(self):
        """Test error when configuration file doesn't exist."""
        non_existent_path = os.path.join(self.temp_dir, "nonexistent.json")
        
        with self.assertRaises(FileNotFoundError) as context:
            ConfigLoader.load_config(non_existent_path)
        self.assertIn("Configuration file not found", str(context.exception))
    
    def test_invalid_json_error(self):
        """Test error when JSON is malformed."""
        config_path = os.path.join(self.temp_dir, "invalid.json")
        with open(config_path, 'w') as f:
            f.write("{ invalid json }")
        
        with self.assertRaises(ValueError) as context:
            ConfigLoader.load_config(config_path)
        self.assertIn("Invalid JSON", str(context.exception))
    
    def test_missing_required_field_error(self):
        """Test error when required field is missing."""
        config_data = {
            "excluded_columns": ["Notes"]
            # Missing required key_columns
        }
        
        config_path = os.path.join(self.temp_dir, "incomplete_config.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        with self.assertRaises(ValueError) as context:
            ConfigLoader.load_config(config_path)
        self.assertIn("Required field 'key_columns' missing", str(context.exception))
    
    def test_unknown_field_error(self):
        """Test error when unknown fields are present."""
        config_data = {
            "key_columns": ["ID"],
            "unknown_field": "value"
        }
        
        config_path = os.path.join(self.temp_dir, "unknown_field_config.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        with self.assertRaises(ValueError) as context:
            ConfigLoader.load_config(config_path)
        self.assertIn("Unknown configuration fields", str(context.exception))
    
    def test_create_example_config(self):
        """Test creating an example configuration file."""
        example_path = os.path.join(self.temp_dir, "example_config.json")
        
        ConfigLoader.create_example_config(example_path)
        
        # Verify file was created and is valid
        self.assertTrue(os.path.exists(example_path))
        
        # Load and verify the example config
        config = ConfigLoader.load_config(example_path)
        self.assertEqual(config.key_columns, ["ID", "Name"])
        self.assertEqual(config.excluded_columns, ["Last Login", "Notes"])
        self.assertEqual(config.schema_mismatch_behavior, "warn")
        self.assertFalse(config.include_unchanged_columns)


if __name__ == '__main__':
    unittest.main()