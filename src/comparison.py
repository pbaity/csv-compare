"""
Core comparison logic for CSV comparison tool.

This module handles the in-memory comparison of CSV data structures,
independent of file I/O operations.
"""

from typing import Dict, List, Any, Set, Tuple, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
import json
import hashlib


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


class DataComparator:
    """Handles comparison logic between two datasets."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the comparator.

        Args:
            config: Dictionary containing configuration settings
        """
        self.key_columns: List[str] = config.get("key_columns", [])
        self.fail_on_duplicate_keys = config.get("fail_on_duplicate_keys", True)


    def compare(self, old_data: Iterable[Mapping[str, str]], new_data: Iterable[Mapping[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Compare two datasets and return comparison results and duplicates.

        Args:
            old_data: List of dictionaries representing rows from first dataset
            new_data: List of dictionaries representing rows from second dataset

        Returns:
            Tuple containing:
                - List of dictionaries representing the comparison results
                - List of dictionaries representing all duplicate rows from both datasets
        """
        self._validate_key_columns(old_data, new_data)
        old_rows, old_columns, old_duplicates = self._create_row_lookup(old_data)
        new_rows, new_columns, new_duplicates = self._create_row_lookup(new_data)

        all_duplicates = old_duplicates + new_duplicates
        
        # If there are no rows in either dataset, return empty results
        if not old_rows and not new_rows:
            return [], all_duplicates

        all_row_keys = set(old_rows.keys()) | set(new_rows.keys())
        all_columns = old_columns | new_columns
        non_key_columns = sorted(all_columns - set(self.key_columns))
        
        results = []

        for row_key in sorted(all_row_keys):
            old_row_dict = old_rows.get(row_key)
            new_row_dict = new_rows.get(row_key)
            old_row = old_row_dict.get("row_data") if old_row_dict else None
            new_row = new_row_dict.get("row_data") if new_row_dict else None

            if old_row is None:
                # Added row
                old_values = {col: "" for col in non_key_columns}
                new_values = {col: new_row.get(col, "") for col in non_key_columns}
                results.append(self._format_compared_row(
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
                results.append(self._format_compared_row(
                    row_key=row_key,
                    status=RowStatus.REMOVED,
                    changed_columns=[],
                    old_values=old_values,
                    new_values=new_values,
                ))
            else:
                # Changed or unchanged row
                # Use row_digest for fast equality check
                old_digest = old_row_dict.get("row_digest") if old_row_dict else None
                new_digest = new_row_dict.get("row_digest") if new_row_dict else None
                if old_digest == new_digest:
                    # Rows are identical, skip output (unchanged)
                    pass
                else:
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
                        results.append(self._format_compared_row(
                            row_key=row_key,
                            status=RowStatus.CHANGED,
                            changed_columns=changed_columns,
                            old_values=old_values,
                            new_values=new_values,
                        ))

        return results, all_duplicates

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

    def _create_row_lookup(self, data: List[Dict[str, str]]) -> Tuple[Dict[str, Dict[str, str]], Set[str], List[Dict[str, str]]]:
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
        columns = set()
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
                duplicate_row = lookup.pop(row_key)["row_data"]
                duplicates.append(duplicate_row)
                duplicates.append(row)
                duplicate_keys.add(row_key)
                continue

            row_digest = self._generate_row_digest(row)
            columns.update(row.keys())

            lookup[row_key] = {
                "row_digest": row_digest,
                "row_data": row
            }

        return lookup, columns, duplicates

    def _generate_row_key(self, row: Dict[str, str]) -> str:
        """Generate a unique key for a row by concatenating key column values."""
        key_values = []
        for key_col in self.key_columns:
            if key_col not in row:
                raise ValueError(f"Key column '{key_col}' not found in row")
            key_values.append(str(row[key_col]))
        return "|".join(key_values)
    
    def _generate_row_digest(self, row: Dict[str, str]) -> str:
        """Generate a SHA-256 digest for a row based on its content."""
        # Convert to a JSON string with sorted keys to ensure consistent order
        dict_str = json.dumps(row, sort_keys=True)
        return hashlib.sha256(dict_str.encode('utf-8')).hexdigest()
    
    def _format_compared_row(
        self, row_key: str, status: RowStatus, changed_columns: List[str],
        old_values: Dict[str, str], new_values: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Format a compared row into a dictionary for output.

        Args:
            row_key: Unique key for the row
            status: Status of the row (added, removed, changed)
            changed_columns: List of columns that changed
            old_values: Dictionary of old values for non-key columns
            new_values: Dictionary of new values for non-key columns

        Returns:
            Formatted dictionary representing the compared row. It will contain:
            - 'Row Key': Unique key for the row
            - 'Status': Status of the row
            - 'Changed Columns': String of changed columns, space-separated
            - A variable number of additional keys for each column, with suffixes "(Old)" and "(New)" for old and new values respectively.
        """
        # Union of all columns present in old_values or new_values
        all_columns = set(old_values.keys()) | set(new_values.keys())
        sorted_columns = sorted(all_columns)

        row_data = {
            "Row Key": row_key,
            "Status": status.value,
            "Changed Columns": ", ".join(changed_columns)
        }
        for column in sorted_columns:
            row_data[f"{column} (Old)"] = old_values.get(column, "")
            row_data[f"{column} (New)"] = new_values.get(column, "")
        return row_data
