#!/usr/bin/env python3
"""
Main CLI orchestrator for CSV comparison tool.

This module coordinates the workflow: loads settings, parses CLI arguments,
and invokes the Data I/O and Comparison modules.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from src.config import ConfigLoader, ComparisonConfig
from src.data_io import CSVReader, CSVWriter, SchemaValidator
from src.comparison import CSVComparator


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Compare two CSV files and identify differences",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s file1.csv file2.csv -o differences.csv -c config.json
  %(prog)s old_data.csv new_data.csv --output results.csv --config settings.json
        """
    )
    
    parser.add_argument(
        "file1",
        nargs='?',
        help="Path to the first CSV file"
    )
    
    parser.add_argument(
        "file2",
        nargs='?', 
        help="Path to the second CSV file"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Path for the output CSV file with comparison results"
    )
    
    parser.add_argument(
        "-c", "--config",
        help="Path to the JSON configuration file"
    )
    
    parser.add_argument(
        "--create-example-config",
        metavar="PATH",
        help="Create an example configuration file at the specified path and exit"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="CSV Comparison Tool 1.0.0"
    )
    
    return parser


def validate_file_paths(file1: str, file2: str, output: str) -> None:
    """
    Validate input and output file paths.
    
    Args:
        file1: Path to first CSV file
        file2: Path to second CSV file
        output: Path to output file
        
    Raises:
        SystemExit: If validation fails
    """
    # Check input files exist
    for filepath, name in [(file1, "First CSV file"), (file2, "Second CSV file")]:
        if not Path(filepath).exists():
            print(f"Error: {name} not found: {filepath}", file=sys.stderr)
            sys.exit(1)
    
    # Check if output directory exists
    output_path = Path(output)
    if not output_path.parent.exists():
        print(f"Error: Output directory does not exist: {output_path.parent}", file=sys.stderr)
        sys.exit(1)
    
    # Warn if output file already exists
    if output_path.exists():
        print(f"Warning: Output file already exists and will be overwritten: {output}")


def load_configuration(config_path: str) -> ComparisonConfig:
    """
    Load and validate configuration.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        ComparisonConfig object
        
    Raises:
        SystemExit: If configuration loading fails
    """
    try:
        return ConfigLoader.load_config(config_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: Invalid configuration - {e}", file=sys.stderr)
        sys.exit(1)


def load_csv_data(file1: str, file2: str, config: ComparisonConfig) -> tuple:
    """
    Load CSV data from both files.
    
    Args:
        file1: Path to first CSV file
        file2: Path to second CSV file
        config: Configuration object
        
    Returns:
        Tuple of (data1, data2) where each is a list of dictionaries
        
    Raises:
        SystemExit: If data loading fails
    """
    try:
        # Validate schemas first
        SchemaValidator.validate_schemas(
            file1, file2, 
            config.key_columns, 
            config.excluded_columns,
            config.schema_mismatch_behavior
        )
        
        # Load the data
        data1 = CSVReader.read_csv(file1, config.excluded_columns)
        data2 = CSVReader.read_csv(file2, config.excluded_columns)
        
        return data1, data2
        
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading CSV data: {e}", file=sys.stderr)
        sys.exit(1)


def perform_comparison(data1: list, data2: list, config: ComparisonConfig):
    """
    Perform the CSV comparison.
    
    Args:
        data1: First dataset
        data2: Second dataset
        config: Configuration object
        
    Returns:
        ComparisonOutput object (results and duplicates)
        
    Raises:
        SystemExit: If comparison fails
    """
    try:
        comparator = CSVComparator(
            key_columns=config.key_columns,
            include_unchanged_columns=config.include_unchanged_columns,
            fail_on_duplicate_keys=config.fail_on_duplicate_keys
        )
        return comparator.compare(data1, data2)
    except ValueError as e:
        print(f"Error during comparison: {e}", file=sys.stderr)
        sys.exit(1)


def write_results(results: list, output_path: str) -> None:
    """
    Write comparison results to output file.
    
    Args:
        results: List of ComparisonResult objects
        output_path: Path to output CSV file
        
    Raises:
        SystemExit: If writing fails
    """
    try:
        # Serialize ComparisonResult objects to plain dictionaries
        results_data = [result.to_dict() for result in results]
        CSVWriter.write_comparison_results(results_data, output_path)
        
    except ValueError as e:
        print(f"Error writing results: {e}", file=sys.stderr)
        sys.exit(1)


def write_duplicates(duplicates: list, output_path: str) -> None:
    """
    Write duplicate rows to a CSV file.
    
    Args:
        duplicates: List of duplicate row dicts
        output_path: Path to output CSV file
        
    Raises:
        SystemExit: If writing fails
    """
    if not duplicates:
        print(f"No duplicate rows found. No duplicates file created.")
        return
    try:
        CSVWriter.write_duplicates(duplicates, output_path)
        print(f"Duplicate rows written to: {output_path}")
    except Exception as e:
        print(f"Error writing duplicates: {e}", file=sys.stderr)
        sys.exit(1)


def print_summary(results: list, output_path: str, duplicates: list = None, duplicates_path: str = None) -> None:
    """Print a summary of the comparison results and duplicates."""
    if not results:
        print("No differences found between the CSV files.")
        print(f"Empty results file created: {output_path}")
        return
    
    # Count different types of changes
    added_count = sum(1 for r in results if r.status.value == "Added")
    removed_count = sum(1 for r in results if r.status.value == "Removed")
    changed_count = sum(1 for r in results if r.status.value == "Changed")
    
    print(f"Comparison completed successfully!")
    print(f"Results written to: {output_path}")
    print(f"Summary:")
    print(f"  - {added_count} rows added")
    print(f"  - {removed_count} rows removed") 
    print(f"  - {changed_count} rows changed")
    print(f"  - {len(results)} total differences")
    if duplicates is not None and duplicates_path is not None:
        print(f"  - {len(duplicates)} duplicate rows written to: {duplicates_path}")


def main() -> None:
    """Main entry point for the CLI application."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle create example config option
    if args.create_example_config:
        try:
            ConfigLoader.create_example_config(args.create_example_config)
            print(f"Example configuration created: {args.create_example_config}")
            sys.exit(0)
        except IOError as e:
            print(f"Error creating example config: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Validate required arguments are present
    if not all([args.file1, args.file2, args.output, args.config]):
        parser.print_help()
        sys.exit(1)
    
    # Validate file paths
    validate_file_paths(args.file1, args.file2, args.output)
    
    # Load configuration
    config = load_configuration(args.config)
    
    # Load CSV data
    data1, data2 = load_csv_data(args.file1, args.file2, config)
    
    # Perform comparison
    comparison_output = perform_comparison(data1, data2, config)
    results = comparison_output.results
    duplicates = comparison_output.duplicates
    
    # Write results
    write_results(results, args.output)
    
    # Write duplicates to a separate file (default: output file with _duplicates.csv)
    duplicates_output_path = str(Path(args.output).with_name(Path(args.output).stem + "_duplicates.csv"))
    write_duplicates(duplicates, duplicates_output_path)
    
    # Print summary
    print_summary(results, args.output, duplicates, duplicates_output_path)


if __name__ == "__main__":
    main()