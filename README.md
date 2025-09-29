# Foxhole Logistics Calculator

This repository contains a small command-line tool for inspecting TSV exports and for calculating required logistics supplies for Colonial stockpiles.

## Prerequisites

This project is packaged as a Nix flake. You can run the tooling without a local Python installation by using the provided flake inputs.

## Usage

### Describe a TSV export

Use the helper to print a quick summary of any TSV-like file (works with tab or multi-space separated values):

```bash
nix run .# -- data/stockpiles.tsv
```

### Generate the stockpile requirement report

Run the report command to combine `data/stockpiles.tsv`, `data/base_requirements/collie.tsv`, and the TSV exports inside `data/current_stock/`:

```bash
nix run .# -- report
```

The tool automatically selects the most recently updated TSV inside `data/current_stock/`, so you only need to keep the latest export in that folder to refresh the numbers. If you want to analyse an older snapshot, temporarily move or rename it so it becomes the newest file before running the report.

By default the tool searches for the `data/` directory relative to the current working directory. You can override this by passing a custom root:

```bash
nix run .# -- report --data-root /path/to/another/data
```

Add `--output` to write the detailed report back to disk (as a tab-separated file):

```bash
nix run .# -- report --output /tmp/stockpile_report.tsv
```

### Alternate invocation within a development shell

If you prefer an interactive shell, enter the flake environment and call the script directly:

```bash
nix develop
process_tsv.py report
```

## Output overview

The generated report prints two sections:

- **Per-item deficit (ideal - current)**: one row per stockpile and item, comparing the ideal quantity (bases × base requirement) with the currently stockpiled amount.
- **Per-base totals**: roll-up of totals per stockpile to highlight the biggest shortfalls or surpluses.

Use the `--output` option to redirect the full table into a spreadsheet for filtering or additional analysis.
