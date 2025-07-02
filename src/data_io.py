"""
Data I/O module for CSV comparison tool.

This module handles reading CSV files and writing comparison results.
"""

import csv
from typing import List, Dict, Set, Any
from pathlib import Path


class CSVReader:
    """Handles reading CSV files into memory."""
    
    @staticmethod
    def read_csv(file_path: str, excluded_columns: List[str] = None) -> List[Dict[str, str]]:
        """
        Read a CSV file into a list of dictionaries.
        
        Args:
            file_path: Path to the CSV file
            excluded_columns: List of column names to exclude from the data
            
        Returns:
            List of dictionaries representing CSV rows
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV file is empty or has issues
        """
        if excluded_columns is None:
            excluded_columns = []
        
        csv_file = Path(file_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        data = []
        try:
            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                # Peek at first line to check if file is empty
                first_char = f.read(1)
                if not first_char:
                    raise ValueError(f"CSV file is empty: {file_path}")
                f.seek(0)  # Reset to beginning
                
                reader = csv.DictReader(f)
                
                # Check if we have fieldnames
                if not reader.fieldnames:
                    raise ValueError(f"CSV file has no headers: {file_path}")
                
                # Filter out excluded columns from fieldnames
                included_fieldnames = [field for field in reader.fieldnames 
                                     if field not in excluded_columns]
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 since header is row 1
                    # Filter out excluded columns from this row
                    filtered_row = {field: row.get(field, '') for field in included_fieldnames}
                    data.append(filtered_row)
                
        except csv.Error as e:
            raise ValueError(f"Error reading CSV file {file_path}: {e}")
        except UnicodeDecodeError as e:
            raise ValueError(f"Encoding error reading CSV file {file_path}: {e}")
        
        return data
    
    @staticmethod
    def get_csv_columns(file_path: str) -> List[str]:
        """
        Get the column names from a CSV file.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of column names
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV file has issues
        """
        csv_file = Path(file_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError(f"CSV file has no headers: {file_path}")
                return list(reader.fieldnames)
        except csv.Error as e:
            raise ValueError(f"Error reading CSV file {file_path}: {e}")


class CSVWriter:
    """Handles writing comparison results to CSV files."""
    
    @staticmethod
    def write_comparison_results(results_data: List[Dict[str, Any]], output_path: str) -> None:
        """
        Write comparison results to a CSV file.
        
        Args:
            results_data: List of result dictionaries with keys:
                - row_key, status, changed_columns, old_values, new_values
            output_path: Path where to write the output CSV
        """
        if not results_data:
            # Create empty output file with just headers
            CSVWriter._write_empty_results(output_path)
            return
        
        # Determine all unique columns that appear in the results (from old_values and new_values)
        all_columns = set()
        for result in results_data:
            all_columns.update(result.get('old_values', {}).keys())
            all_columns.update(result.get('new_values', {}).keys())
        sorted_columns = sorted(all_columns)
        
        # Build fieldnames for output CSV
        fieldnames = ["Row Key", "Status", "Changed Columns"]
        for column in sorted_columns:
            fieldnames.extend([f"{column} (Old)", f"{column} (New)"])
        
        try:
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in results_data:
                    row_data = {
                        "Row Key": result['row_key'],
                        "Status": result['status'],
                        "Changed Columns": ", ".join(result.get('changed_columns', []))
                    }
                    # Add old and new values for all columns
                    for column in sorted_columns:
                        old_value = result.get('old_values', {}).get(column, "")
                        new_value = result.get('new_values', {}).get(column, "")
                        row_data[f"{column} (Old)"] = old_value
                        row_data[f"{column} (New)"] = new_value
                    writer.writerow(row_data)
        except IOError as e:
            raise ValueError(f"Error writing output CSV file {output_path}: {e}")
    
    @staticmethod
    def _write_empty_results(output_path: str) -> None:
        """Write an empty results file with just headers."""
        fieldnames = ["Row Key", "Status", "Changed Columns"]
        
        try:
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        except IOError as e:
            raise ValueError(f"Error writing output CSV file {output_path}: {e}")
    
    @staticmethod
    def write_duplicates(duplicates: List[Dict[str, Any]], output_path: str) -> None:
        """
        Write duplicate rows to a CSV file. If the list is empty, skip file creation.
        
        Args:
            duplicates: List of duplicate row dicts
            output_path: Path to output CSV file
            
        Raises:
            ValueError: If writing fails
        """
        if not duplicates:
            # No duplicates, skip file creation
            return
        try:
            fieldnames = list(duplicates[0].keys())
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(duplicates)
        except Exception as e:
            raise ValueError(f"Error writing duplicates CSV file {output_path}: {e}")


class SchemaValidator:
    """Validates CSV file schemas and handles mismatches."""
    
    @staticmethod
    def validate_schemas(file1_path: str, file2_path: str, 
                        key_columns: List[str], excluded_columns: List[str],
                        schema_mismatch_behavior: str) -> None:
        """
        Validate that both CSV files have compatible schemas.
        
        Args:
            file1_path: Path to first CSV file
            file2_path: Path to second CSV file  
            key_columns: List of key column names
            excluded_columns: List of columns to exclude
            schema_mismatch_behavior: How to handle mismatches ("fail", "warn", "ignore")
            
        Raises:
            ValueError: If schemas are incompatible and behavior is "fail"
        """
        if schema_mismatch_behavior == "ignore":
            return
        
        try:
            columns1 = set(CSVReader.get_csv_columns(file1_path))
            columns2 = set(CSVReader.get_csv_columns(file2_path))
        except (FileNotFoundError, ValueError) as e:
            # Let the CSVReader handle these errors later
            return
        
        # Remove excluded columns from comparison
        excluded_set = set(excluded_columns)
        columns1 = columns1 - excluded_set
        columns2 = columns2 - excluded_set
        
        # Check for schema differences
        only_in_file1 = columns1 - columns2
        only_in_file2 = columns2 - columns1
        
        if only_in_file1 or only_in_file2:
            message_parts = []
            if only_in_file1:
                message_parts.append(f"Columns only in first file: {sorted(only_in_file1)}")
            if only_in_file2:
                message_parts.append(f"Columns only in second file: {sorted(only_in_file2)}")
            
            message = "Schema mismatch detected. " + ". ".join(message_parts)
            
            if schema_mismatch_behavior == "fail":
                raise ValueError(message)
            elif schema_mismatch_behavior == "warn":
                print(f"WARNING: {message}")
        
        # Validate that key columns exist in both files
        missing_keys_file1 = set(key_columns) - columns1
        missing_keys_file2 = set(key_columns) - columns2
        
        if missing_keys_file1:
            raise ValueError(f"Key columns missing from first file: {sorted(missing_keys_file1)}")
        if missing_keys_file2:
            raise ValueError(f"Key columns missing from second file: {sorted(missing_keys_file2)}")