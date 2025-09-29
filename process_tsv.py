#!/usr/bin/env python3

import sys
import csv

if len(sys.argv) != 2:
    print("Usage: process_tsv.py <tsv_file>")
    sys.exit(1)

tsv_file = sys.argv[1]

try:
    with open(tsv_file, 'r', newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        rows = list(reader)
        print(f"Processed {len(rows)} rows.")
        for i, row in enumerate(rows):
            print(f"Row {i+1}: {row}")
except FileNotFoundError:
    print(f"Error: File '{tsv_file}' not found.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)