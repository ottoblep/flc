#!/usr/bin/env python3

import sys
import pandas as pd

if len(sys.argv) != 2:
    print("Usage: process_tsv.py <tsv_file>")
    sys.exit(1)

tsv_file = sys.argv[1]

try:
    df = pd.read_csv(tsv_file, sep='\t')
    print(f"Processed TSV with {df.shape[0]} rows and {df.shape[1]} columns.")
    print("Columns:", list(df.columns))
    print("First 5 rows:")
    print(df.head())
    # Additional processing: if there are numeric columns, compute sum
    numeric_cols = df.select_dtypes(include=['number']).columns
    if not numeric_cols.empty:
        print("Sum of numeric columns:")
        print(df[numeric_cols].sum())
except FileNotFoundError:
    print(f"Error: File '{tsv_file}' not found.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)