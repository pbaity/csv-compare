"""
Configuration handling for CSV comparison tool.

This module handles loading and validating JSON configuration files.
"""

import json
from typing import Dict, List, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ComparisonConfig:
    """Configuration settings for CSV comparison."""
    key_columns: List[str]
    excluded_columns: List[str]
    schema_mismatch_behavior: str
    include_unchanged_columns: bool
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration values."""
        if not self.key_columns:
            raise ValueError("key_columns cannot be empty")
        
        if not isinstance(self.key_columns, list):
            raise ValueError("key_columns must be a list")
        
        if not isinstance(self.excluded_columns, list):
            raise ValueError("excluded_columns must be a list")
        
        valid_behaviors = ["fail", "warn", "ignore"]
        if self.schema_mismatch_behavior not in valid_behaviors:
            raise ValueError(f"schema_mismatch_behavior must be one of {valid_behaviors}")
        
        if not isinstance(self.include_unchanged_columns, bool):
            raise ValueError("include_unchanged_columns must be a boolean")


class ConfigLoader:
    """Handles loading configuration from JSON files."""
    
    @staticmethod
    def load_config(config_path: str) -> ComparisonConfig:
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to the JSON configuration file
            
        Returns:
            ComparisonConfig object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
            json.JSONDecodeError: If JSON is malformed
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        
        return ConfigLoader._parse_config(config_data)
    
    @staticmethod
    def _parse_config(config_data: Dict[str, Any]) -> ComparisonConfig:
        """
        Parse configuration data into ComparisonConfig object.
        
        Args:
            config_data: Dictionary with configuration values
            
        Returns:
            ComparisonConfig object
        """
        # Set defaults for optional fields
        defaults = {
            "excluded_columns": [],
            "schema_mismatch_behavior": "warn",
            "include_unchanged_columns": False
        }
        
        # Check for required fields
        if "key_columns" not in config_data:
            raise ValueError("Required field 'key_columns' missing from configuration")
        
        # Merge with defaults
        for key, default_value in defaults.items():
            if key not in config_data:
                config_data[key] = default_value
        
        # Validate that we don't have unknown fields
        known_fields = {"key_columns", "excluded_columns", "schema_mismatch_behavior", "include_unchanged_columns"}
        unknown_fields = set(config_data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown configuration fields: {unknown_fields}")
        
        return ComparisonConfig(
            key_columns=config_data["key_columns"],
            excluded_columns=config_data["excluded_columns"],
            schema_mismatch_behavior=config_data["schema_mismatch_behavior"],
            include_unchanged_columns=config_data["include_unchanged_columns"]
        )
    
    @staticmethod
    def create_example_config(output_path: str) -> None:
        """
        Create an example configuration file.
        
        Args:
            output_path: Path where to create the example config file
        """
        example_config = {
            "key_columns": ["ID", "Name"],
            "excluded_columns": ["Last Login", "Notes"],
            "schema_mismatch_behavior": "warn",
            "include_unchanged_columns": False
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(example_config, f, indent=2)