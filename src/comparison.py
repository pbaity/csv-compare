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
    old_values: Dict[str, str]  # All non-key columns, empty string if not present
    new_values: Dict[str, str]  # All non-key columns, empty string if not present

    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain Python dictionary for serialization."""
        return {
            'row_key': self.row_key,
            'status': self.status.value,
            'changed_columns': self.changed_columns,
            'old_values': self.old_values,
            'new_values': self.new_values,
        }


@dataclass
class ComparisonOutput:
    results: List[ComparisonResult]
    duplicates: List[Dict[str, str]]


class CSVComparator:
    """Handles comparison logic between two CSV datasets."""

    def __init__(self, key_columns: List[str], fail_on_duplicate_keys: bool = True):
        """
        Initialize the comparator.

        Args:
            key_columns: List of column names that uniquely identify rows
        """
        self.key_columns = key_columns
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
        self._validate_key_columns(old_data, new_data)
        old_rows, old_duplicates = self._create_row_lookup(old_data)
        new_rows, new_duplicates = self._create_row_lookup(new_data)

        # Gather all non-key columns from both datasets
        all_columns = set()
        for row in old_data + new_data:
            all_columns.update(row.keys())
        non_key_columns = sorted(all_columns - set(self.key_columns))

        results = []
        all_keys = set(old_rows.keys()) | set(new_rows.keys())

        for row_key in sorted(all_keys):
            old_row = old_rows.get(row_key)
            new_row = new_rows.get(row_key)

            if old_row is None:
                # Added row
                old_values = {col: "" for col in non_key_columns}
                new_values = {col: new_row.get(col, "") for col in non_key_columns}
                results.append(ComparisonResult(
                    row_key=row_key,
                    status=RowStatus.ADDED,
                    changed_columns=[],
                    old_values=old_values,
                    new_values=new_values,
                ))
            elif new_row is None:
                # Removed row
                old_values = {col: old_row.get(col, "") for col in non_key_columns}
                new_values = {col: "" for col in non_key_columns}
                results.append(ComparisonResult(
                    row_key=row_key,
                    status=RowStatus.REMOVED,
                    changed_columns=[],
                    old_values=old_values,
                    new_values=new_values,
                ))
            else:
                # Changed or unchanged row
                changed_columns = []
                old_values = {}
                new_values = {}
                for col in non_key_columns:
                    old_val = old_row.get(col, "")
                    new_val = new_row.get(col, "")
                    old_values[col] = old_val
                    new_values[col] = new_val
                    if str(old_val) != str(new_val):
                        changed_columns.append(col)
                if changed_columns:
                    results.append(ComparisonResult(
                        row_key=row_key,
                        status=RowStatus.CHANGED,
                        changed_columns=changed_columns,
                        old_values=old_values,
                        new_values=new_values,
                    ))

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