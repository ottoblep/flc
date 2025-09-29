# Foxhole Logistics Calculator

This repository contains a small command-line tool for inspecting TSV exports and for calculating required logistics supplies for Colonial stockpiles.

## Prerequisites

This project is packaged as a Nix flake. You can run the tooling without a local Python installation by using the provided flake inputs.

## Usage

### Generate the stockpile requirement report

```bash
nix run
```

- First enter all relevant stockpiles and the number of frontline bases they need to supply into `stockpiles.tsv`.
- Then screenshot all relevant stockpiles and name the files with their location names corresponding to `stockpiles.tsv`. 
- Then use [Foxhole Inventory Report](https://github.com/GICodeWarrior/fir) to parse the screenshots for the content of all stockpiles.
- Put the exported tsv file into `data/current_stock`.
- Run the tool. It tool automatically selects the most recently updated TSV inside `data/current_stock/`, so you only need to keep the latest export in that folder to refresh the numbers. If you want to analyse an older snapshot, temporarily move or rename it so it becomes the newest file before running the report.

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