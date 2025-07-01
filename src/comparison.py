"""
Core comparison logic for CSV comparison tool.

This module handles the in-memory comparison of CSV data structures,
independent of file I/O operations.
"""

from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class RowStatus(Enum):
    """Status of a row in the comparison."""
    ADDED = "Added"
    REMOVED = "Removed"
    CHANGED = "Changed"


@dataclass
class ComparisonResult:
    """Result of comparing two rows."""
    row_key: str
    status: RowStatus
    changed_columns: List[str]
    old_values: Dict[str, str]  # Only changed column values
    new_values: Dict[str, str]  # Only changed column values
    unchanged_values: Dict[str, str]  # Unchanged column values (when included)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain Python dictionary for serialization."""
        return {
            'row_key': self.row_key,
            'status': self.status.value,
            'changed_columns': self.changed_columns,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'unchanged_values': self.unchanged_values
        }


@dataclass
class ComparisonOutput:
    results: List[ComparisonResult]
    duplicates: List[Dict[str, str]]


class CSVComparator:
    """Handles comparison logic between two CSV datasets."""
    
    def __init__(self, key_columns: List[str], include_unchanged_columns: bool = False, fail_on_duplicate_keys: bool = True):
        """
        Initialize the comparator.
        
        Args:
            key_columns: List of column names that uniquely identify rows
            include_unchanged_columns: Whether to include unchanged columns in output
        """
        self.key_columns = key_columns
        self.include_unchanged_columns = include_unchanged_columns
        self.fail_on_duplicate_keys = fail_on_duplicate_keys
    
    def compare(self, old_data: List[Dict[str, str]], new_data: List[Dict[str, str]]) -> ComparisonOutput:
        """
        Compare two datasets and return comparison results and duplicates.
        
        Args:
            old_data: List of dictionaries representing rows from first CSV
            new_data: List of dictionaries representing rows from second CSV
            
        Returns:
            ComparisonOutput: Contains list of ComparisonResult objects and all duplicate rows from both datasets.
            
        Raises:
            ValueError: If key columns are missing from data
        """
        # Validate key columns exist in both datasets
        self._validate_key_columns(old_data, new_data)
        
        # Create lookup dictionaries keyed by row key
        old_rows, old_duplicates = self._create_row_lookup(old_data)
        new_rows, new_duplicates = self._create_row_lookup(new_data)
        
        results = []
        
        # Find all unique row keys
        all_keys = set(old_rows.keys()) | set(new_rows.keys())
        
        for row_key in sorted(all_keys):
            old_row = old_rows.get(row_key)
            new_row = new_rows.get(row_key)
            
            if old_row is None:
                # Row was added - show new values as "new" data
                filtered_row = {k: v for k, v in new_row.items() if k not in self.key_columns}
                results.append(ComparisonResult(
                    row_key=row_key,
                    status=RowStatus.ADDED,
                    changed_columns=[],
                    old_values={},
                    new_values=filtered_row,
                    unchanged_values={}
                ))
            elif new_row is None:
                # Row was removed - show old values as "old" data  
                filtered_row = {k: v for k, v in old_row.items() if k not in self.key_columns}
                results.append(ComparisonResult(
                    row_key=row_key,
                    status=RowStatus.REMOVED,
                    changed_columns=[],
                    old_values=filtered_row,
                    new_values={},
                    unchanged_values={}
                ))
            else:
                # Row exists in both, check for changes
                changed_columns, old_values, new_values, unchanged_values = self._compare_rows(old_row, new_row)
                if changed_columns:
                    results.append(ComparisonResult(
                        row_key=row_key,
                        status=RowStatus.CHANGED,
                        changed_columns=changed_columns,
                        old_values=old_values,
                        new_values=new_values,
                        unchanged_values=unchanged_values
                    ))

        # Combine duplicates from both datasets
        all_duplicates = old_duplicates + new_duplicates
        return ComparisonOutput(results=results, duplicates=all_duplicates)
    
    def _validate_key_columns(self, old_data: List[Dict[str, str]], new_data: List[Dict[str, str]]) -> None:
        """Validate that key columns exist in both datasets."""
        if not old_data and not new_data:
            return
            
        # Check first row of each dataset for key columns
        for dataset, name in [(old_data, "first"), (new_data, "second")]:
            if dataset:
                missing_keys = [key for key in self.key_columns if key not in dataset[0]]
                if missing_keys:
                    raise ValueError(f"Missing key columns in {name} dataset: {missing_keys}")
    
    def _create_row_lookup(self, data: List[Dict[str, str]]) -> Tuple[Dict[str, Dict[str, str]], List[Dict[str, str]]]:
        """
        Create a lookup dictionary keyed by concatenated key column values.

        Args:
            data: List of dictionaries representing CSV rows.

        Returns:
            A tuple (lookup_dict, duplicates_list), where:
                - lookup_dict: dict mapping row keys to rows (only the first occurrence of each unique key)
                - duplicates_list: list of all rows with duplicate keys (including the original and all subsequent duplicates)

        Notes:
            - If fail_on_duplicate_keys is True, raises ValueError on the first duplicate key encountered.
            - If fail_on_duplicate_keys is False, all rows with duplicate keys (including the original) are collected in duplicates_list and excluded from lookup_dict.
            - Once a key is detected as a duplicate, all further rows with that key are always treated as duplicates and never added to lookup_dict.
        """
        lookup = {}
        duplicates = []
        duplicate_keys = set()

        for row in data:
            row_key = self._generate_row_key(row)

            if row_key in duplicate_keys:
                # Already known duplicate, just add to duplicates
                duplicates.append(row)
                continue

            if row_key in lookup:
                if self.fail_on_duplicate_keys:
                    raise ValueError(f"Duplicate row key found: {row_key}")
                # Move the original to duplicates, mark key as duplicate
                duplicates.append(lookup.pop(row_key))
                duplicates.append(row)
                duplicate_keys.add(row_key)
                continue

            lookup[row_key] = row

        return lookup, duplicates
    
    def _generate_row_key(self, row: Dict[str, str]) -> str:
        """Generate a unique key for a row by concatenating key column values."""
        key_values = []
        for key_col in self.key_columns:
            if key_col not in row:
                raise ValueError(f"Key column '{key_col}' not found in row")
            key_values.append(str(row[key_col]))
        return "|".join(key_values)
    
    def _compare_rows(self, old_row: Dict[str, str], new_row: Dict[str, str]) -> Tuple[List[str], Dict[str, str], Dict[str, str], Dict[str, str]]:
        """
        Compare two rows and return changed columns and their values.
        
        Returns:
            Tuple of (changed_columns, old_values, new_values, unchanged_values)
        """
        changed_columns = []
        old_values = {}
        new_values = {}
        unchanged_values = {}
        
        # Get all columns from both rows, excluding key columns
        all_columns = set(old_row.keys()) | set(new_row.keys())
        non_key_columns = all_columns - set(self.key_columns)
        
        for column in sorted(non_key_columns):
            old_value = old_row.get(column, "")
            new_value = new_row.get(column, "")
            
            # Compare as strings to handle type mismatches
            if str(old_value) != str(new_value):
                changed_columns.append(column)
                old_values[column] = str(old_value)
                new_values[column] = str(new_value)
            elif self.include_unchanged_columns:
                # For unchanged columns, we use the common value (old_value == new_value)
                unchanged_values[column] = str(old_value)
        
        return changed_columns, old_values, new_values, unchanged_values