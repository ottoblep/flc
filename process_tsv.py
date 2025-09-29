#!/usr/bin/env python3

"""Utilities for exploring TSV exports and generating stockpile reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

def normalise_stockpile_name(series: pd.Series) -> pd.Series:
    """Normalise stockpile names from inventory exports."""

    cleaned = series.fillna("").astype(str).str.strip()
    cleaned = cleaned.str.replace(".png", "", regex=False)
    return cleaned


def summarise_item_breakdown(items: Sequence[tuple[str, int]], limit: int | None = 3) -> str:
    if not items:
        return ""

    display = items if limit is None else items[:limit]
    parts = [f"{code}: {qty}" for code, qty in display]
    if limit is not None and len(items) > limit:
        parts.append(f"+{len(items) - limit} more")
    return ", ".join(parts)


def load_stockpiles(stockpiles_path: Path) -> pd.DataFrame:
    stockpiles = pd.read_csv(stockpiles_path, sep=r"\s{2,}", engine="python")
    stockpiles.columns = [col.strip() for col in stockpiles.columns]
    stockpiles.rename(columns={"StockpileName": "StockpileNameRaw"}, inplace=True)
    stockpiles["StockpileNameRaw"] = stockpiles["StockpileNameRaw"].astype(str).str.strip()
    stockpiles["BasesToSupply"] = pd.to_numeric(stockpiles["BasesToSupply"], errors="coerce").fillna(0).astype(int)
    stockpiles.rename(columns={"StockpileNameRaw": "StockpileName"}, inplace=True)
    return stockpiles


def load_base_requirements(requirements_path: Path) -> pd.DataFrame:
    requirements = pd.read_csv(requirements_path, sep=r"\s{2,}", engine="python")
    requirements.columns = [col.strip() for col in requirements.columns]
    requirements.rename(columns={"Quantity": "QuantityPerBase"}, inplace=True)
    requirements["CodeName"] = requirements["CodeName"].astype(str).str.strip()
    requirements["QuantityPerBase"] = pd.to_numeric(
        requirements["QuantityPerBase"], errors="coerce"
    ).fillna(0)
    requirements["QuantityPerBase"] = requirements["QuantityPerBase"].astype(int)
    return requirements


def load_current_stock(tsv_files: Iterable[Path]) -> pd.DataFrame:
    frames = []
    for file_path in tsv_files:
        df = pd.read_csv(file_path, sep="\t")
        df["StockpileName"] = normalise_stockpile_name(df.get("Stockpile Name"))

        title_fallback = normalise_stockpile_name(df.get("Stockpile Title"))
        mask_missing = df["StockpileName"].eq("")
        if mask_missing.any():
            df.loc[mask_missing, "StockpileName"] = title_fallback[mask_missing]

        df["StockpileName"] = df["StockpileName"].replace("", pd.NA)

        df["CodeName"] = df["CodeName"].astype(str).str.strip()
        df["Total"] = pd.to_numeric(df.get("Total"), errors="coerce").fillna(0)
        frames.append(df)

    if not frames:
        return pd.DataFrame(columns=["StockpileName", "CodeName", "Total"])

    combined = pd.concat(frames, ignore_index=True)
    combined.dropna(subset=["StockpileName"], inplace=True)
    return combined


def guess_data_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    candidate_paths = [script_dir / "data", Path.cwd() / "data"]
    for candidate in candidate_paths:
        if candidate.exists():
            return candidate
    raise SystemExit(
        "Could not locate data directory automatically. "
        "Pass --data-root /path/to/data explicitly."
    )


def build_requirement_report(data_root: Path, output_path: Path | None = None) -> pd.DataFrame:
    stockpiles_path = data_root / "stockpiles.tsv"
    requirements_path = data_root / "base_requirements" / "collie.tsv"
    current_stock_dir = data_root / "current_stock"

    if not stockpiles_path.exists():
        raise SystemExit(f"Missing stockpiles file: {stockpiles_path}")
    if not requirements_path.exists():
        raise SystemExit(f"Missing base requirements file: {requirements_path}")
    if not current_stock_dir.exists():
        raise SystemExit(f"Missing current stock directory: {current_stock_dir}")

    stockpiles = load_stockpiles(stockpiles_path)
    requirements = load_base_requirements(requirements_path)
    current_stock_files = sorted(current_stock_dir.glob("*.tsv"))

    if not current_stock_files:
        raise SystemExit(f"No TSV files found in {current_stock_dir}")

    newest_file = max(
        current_stock_files,
        key=lambda path: (path.stat().st_mtime, path.name),
    )

    current_stock = load_current_stock([newest_file])

    relevant_stock = current_stock[current_stock["CodeName"].isin(requirements["CodeName"])]
    actuals = (
        relevant_stock.groupby(["StockpileName", "CodeName"], as_index=False)["Total"].sum()
    )

    cross = stockpiles.assign(key=1).merge(requirements.assign(key=1), on="key").drop("key", axis=1)
    cross["IdealQuantity"] = cross["BasesToSupply"] * cross["QuantityPerBase"]

    report = cross.merge(actuals, on=["StockpileName", "CodeName"], how="left")
    report["CurrentQuantity"] = report["Total"].fillna(0)
    report.drop(columns=["Total"], inplace=True)
    report["DeficitSurplus"] = report["IdealQuantity"] - report["CurrentQuantity"]

    report["IdealQuantity"] = report["IdealQuantity"].astype(int)
    report["CurrentQuantity"] = report["CurrentQuantity"].astype(int)
    report["DeficitSurplus"] = report["DeficitSurplus"].astype(int)

    report.sort_values(["StockpileName", "CodeName"], inplace=True)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output_path, sep="\t", index=False)

    return report


def print_report(report: pd.DataFrame) -> None:
    display_cols = [
        "StockpileName",
        "CodeName",
        "BasesToSupply",
        "QuantityPerBase",
        "IdealQuantity",
        "CurrentQuantity",
        "DeficitSurplus",
    ]

    printable = report[display_cols].copy()
    printable.sort_values(
        by="DeficitSurplus",
        key=lambda col: col.abs(),
        ascending=False,
        inplace=True,
    )
    print("\nPer-item deficit (ideal - current):")
    print(printable.to_string(index=False))

    base_summary = (
        report.groupby("StockpileName")[["IdealQuantity", "CurrentQuantity", "DeficitSurplus"]]
        .sum()
        .reset_index()
        .sort_values("DeficitSurplus", ascending=False)
    )

    print("\nPer-base totals:")
    print(base_summary.to_string(index=False))


def calculate_potential_trips(report: pd.DataFrame) -> pd.DataFrame:
    """Return potential resource transfer trips sorted by transferable quantity."""

    surpluses = report[report["DeficitSurplus"] < 0].copy()
    deficits = report[report["DeficitSurplus"] > 0].copy()

    if surpluses.empty or deficits.empty:
        return pd.DataFrame(
            columns=["Source", "Destination", "TotalPotential", "DistinctItems", "TopItems"]
        )

    surpluses["AvailableQuantity"] = surpluses["DeficitSurplus"].abs()
    deficits["NeededQuantity"] = deficits["DeficitSurplus"].astype(int)

    pairwise = surpluses.merge(
        deficits,
        on="CodeName",
        suffixes=("_source", "_destination"),
    )

    pairwise = pairwise[pairwise["StockpileName_source"] != pairwise["StockpileName_destination"]]
    if pairwise.empty:
        return pd.DataFrame(
            columns=["Source", "Destination", "TotalPotential", "DistinctItems", "TopItems"]
        )

    pairwise["TransferQuantity"] = pairwise[["AvailableQuantity", "NeededQuantity"]].min(axis=1)
    pairwise = pairwise[pairwise["TransferQuantity"] > 0]

    if pairwise.empty:
        return pd.DataFrame(
            columns=["Source", "Destination", "TotalPotential", "DistinctItems", "TopItems"]
        )

    pairwise["TransferQuantity"] = pairwise["TransferQuantity"].round().astype(int)

    grouped = pairwise.groupby(["StockpileName_source", "StockpileName_destination"])

    totals = grouped["TransferQuantity"].sum().astype(int).rename("TotalPotential")
    distinct = grouped["CodeName"].nunique().astype(int).rename("DistinctItems")

    aggregated = (
        pd.concat([totals, distinct], axis=1)
        .reset_index()
        .rename(
            columns={
                "StockpileName_source": "Source",
                "StockpileName_destination": "Destination",
            }
        )
    )

    def collect_breakdown(group: pd.DataFrame) -> list[tuple[str, int]]:
        ordered = group.sort_values("TransferQuantity", ascending=False)[
            ["CodeName", "TransferQuantity"]
        ]
        return [(code, int(qty)) for code, qty in ordered.itertuples(index=False)]

    breakdown_lookup = {
        (source, destination): collect_breakdown(group)
        for (source, destination), group in grouped
    }

    aggregated["ItemBreakdown"] = [
        breakdown_lookup[(row.Source, row.Destination)]
        for row in aggregated.itertuples(index=False)
    ]

    aggregated["TopItems"] = aggregated["ItemBreakdown"].apply(summarise_item_breakdown)

    aggregated.sort_values("TotalPotential", ascending=False, inplace=True)
    aggregated.reset_index(drop=True, inplace=True)
    return aggregated


def print_trips(
    trips: pd.DataFrame,
    limit: int | None = None,
    show_all_items: bool = False,
) -> None:
    if trips.empty:
        print("\nNo potential trips found.")
        return

    printable = trips.copy()
    if limit is not None and limit > 0:
        printable = printable.head(limit)

    print("\nPotential trips by transferable items:")
    for row in printable.itertuples(index=False):
        print(
            f"{row.Source} -> {row.Destination}: "
            f"{row.TotalPotential} items across {row.DistinctItems} types"
        )
        if show_all_items and hasattr(row, "ItemBreakdown"):
            items_text = summarise_item_breakdown(row.ItemBreakdown, limit=None)
            label = "All items"
        else:
            items_text = getattr(row, "TopItems", "")
            label = "Top items"
        if items_text:
            print(f"  {label}: {items_text}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    report_parser = subparsers.add_parser("report", help="Generate stockpile requirement report")
    report_parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Directory containing stockpiles.tsv, base_requirements/, and current_stock/",
    )
    report_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the detailed report as TSV",
    )

    trips_parser = subparsers.add_parser(
        "trips", help="List potential supply trips sorted by transferable quantity"
    )
    trips_parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Directory containing stockpiles.tsv, base_requirements/, and current_stock/",
    )
    trips_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional number of top trips to display (default: all)",
    )
    trips_parser.add_argument(
        "--all-items",
        action="store_true",
        help="Show the full item list for each trip instead of the top three",
    )

    if (
        argv is None
        and len(sys.argv) == 2
        and not sys.argv[1].startswith("-")
        and Path(sys.argv[1]).exists()
    ):
        argv = ["describe", sys.argv[1]]

    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    if args.command == "report":
        data_root = args.data_root or guess_data_root()
        report = build_requirement_report(data_root, args.output)
        print_report(report)
    elif args.command == "trips":
        data_root = args.data_root or guess_data_root()
        report = build_requirement_report(data_root)
        trips = calculate_potential_trips(report)
        print_trips(trips, args.limit, args.all_items)
    else:
        # Default to report when no arguments are provided.
        report = build_requirement_report(guess_data_root())
        print_report(report)


if __name__ == "__main__":
    main()