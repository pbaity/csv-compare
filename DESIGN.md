# CSV Comparison Tool — Design Document

---

## 1. Overview

This tool is designed to help users efficiently compare two CSV files and identify discrepancies between them. It highlights rows that have been added, removed, or changed, focusing on differences in values across user-specified key columns that uniquely identify each row.

The primary use case is to support users who want to quickly understand how datasets have evolved between versions — such as tracking changes in records, spotting data entry errors, or verifying exports.

To ensure robustness and ease of testing, the project will be developed in phases, starting with a command-line interface (CLI) tool before adding a graphical user interface (GUI).

---

## 2. Supported Features

### Basic Comparison

The tool accepts two CSV files as input. Users define which columns serve as unique keys for identifying rows. For example, a combination of “ID” and “Name” columns might uniquely identify a record.

The comparison results classify each row as one of:

* **Changed**: The row exists in both files, but at least one non-key column’s value differs.
* **Added**: The row exists only in the second file.
* **Removed**: The row exists only in the first file.

### Column Exclusion

Users can specify a list of columns to exclude from both the comparison process and the final output. These columns are removed before comparison, simplifying the dataset and focusing on relevant data.

### Output CSV File

The output is a CSV summarizing differences:

* A "Row Key" field concatenates the values of key columns for easy identification.
* A "Status" field indicates whether the row was changed, added, or removed.
* A "Changed Columns" field lists the names of columns that have different values between the two files.
* For each changed column, two new columns show the old and new values, labeled with suffixes like "(Old)" and "(New)".

### Handling Unchanged Columns

By default, unchanged columns are **excluded** from the output to produce a concise summary focused on actual changes. A configurable setting allows users to include unchanged columns if desired.

---

## 3. Settings (JSON Schema)

Configuration is stored in a JSON file for flexibility and future extensibility. Example:

```json
{
  "key_columns": ["ID", "Name"],
  "excluded_columns": ["Last Login", "Notes"],
  "schema_mismatch_behavior": "warn",
  "include_unchanged_columns": false
}
```

* `key_columns`: Array of column names to identify unique rows.
* `excluded_columns`: Array of columns to exclude from comparison and output.
* `schema_mismatch_behavior`: Controls how column schema mismatches are handled — options are `"fail"`, `"warn"`, or `"ignore"`. Defaults to `"warn"`.
* `include_unchanged_columns`: Boolean flag controlling whether unchanged columns appear in the output. Defaults to `false`.

---

## 4. Architecture and Modules

### Data I/O Module

This module is responsible for all file interactions:

* Reading input CSV files into an internal in-memory data structure, applying column exclusions upfront.
* Writing the final comparison results back to a CSV file.

It encapsulates CSV parsing and generation, isolating file-format concerns from the core comparison logic.

### Comparison Logic Module

Receives the preprocessed data structures from the Data I/O Module and performs the core comparison:

* Matches rows using the defined key columns.
* Detects added, removed, and changed rows.
* Identifies which columns have changed values.
* Generates a comprehensive result data structure including status and old/new values.

This module operates entirely on in-memory data structures, independent of CSV or file I/O concerns.

### Main Orchestrator Module

Coordinates the workflow:

* Loads user settings from the JSON file.
* Parses CLI arguments.
* Invokes Data I/O and Comparison modules in order.
* Handles errors and outputs status messages.

---

## 5. Phases of Development

### Phase 1: CLI Tool

Focuses on implementing a robust command-line interface:

* Core CSV comparison logic.
* Reading/writing CSV files.
* Handling basic user-configured settings.
* Command-line arguments to specify input/output files and settings path.

This phase allows thorough testing and iterative improvement of comparison features before adding complexity.

### Phase 2: GUI (Future)

Building a cross-platform graphical interface that:

* Allows users to select input/output files via dialogs.
* Provides an interactive UI for configuring settings with checkboxes, dropdowns, and text inputs.
* Displays results in an intuitive tabular format.
* Leverages the same comparison logic as the CLI.

---

## 6. Future Enhancements

* Advanced include/exclude rules supporting conditional logic on rows and columns.
* Schema diff reports showing added or removed columns explicitly.
* Additional output formats such as HTML reports.
* Performance improvements for large datasets.
* Integration with the GUI for an improved user experience.

---

## 7. Risks and Considerations

* **Duplicate keys:** Input CSVs with duplicate rows for the same key combination should trigger warnings or errors.
* **Schema mismatches:** Differences in column sets between input files can cause confusion; the tool defaults to warnings.
* **Large files:** Scalability may require optimization or chunked processing in future versions.

---

## 8. Testing and Validation

* Unit tests on in-memory data comparison logic.
* Integration tests covering end-to-end CSV input/output.
* Tests verifying different configuration settings and error handling.

---

# Summary

This tool aims to offer users a simple yet powerful means of comparing CSV datasets, starting with a command-line prototype and evolving into a full-featured application with GUI support. Configurability and clear, focused output are priorities to make it adaptable to diverse use cases.
