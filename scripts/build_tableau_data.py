import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

DATABASE_FILE = BASE_DIR / "data" / "grocery_prices.db"
TABLEAU_DIR = BASE_DIR / "tableau"

HISTORY_OUTPUT = TABLEAU_DIR / "price_history_long.csv"
COMPARISON_OUTPUT = TABLEAU_DIR / "latest_price_comparison.csv"

KROGER_STORE_NAME = "Kroger On the Rhine"
KROGER_LOCATION = "Cincinnati, OH"
KROGER_LOCATION_ID = "01400513"


def load_data():
    connection = sqlite3.connect(DATABASE_FILE)

    kroger = pd.read_sql_query(
        """
        SELECT
            snapshot_date,
            location_id,
            category,
            product_name,
            product_id,
            package_size,
            standard_unit,
            unit_quantity,
            regular_price,
            promo_price,
            effective_price,
            normalized_price,
            on_sale
        FROM price_history
        ORDER BY snapshot_date, category
        """,
        connection,
    )

    bls = pd.read_sql_query(
        """
        SELECT
            observation_date,
            year,
            month,
            series_id,
            category,
            bls_item_name,
            standard_unit,
            bls_price,
            geography
        FROM bls_price_history
        ORDER BY observation_date, category
        """,
        connection,
    )

    connection.close()

    return kroger, bls


def build_kroger_history(kroger):
    kroger = kroger.copy()

    kroger["date"] = pd.to_datetime(
        kroger["snapshot_date"]
    )

    kroger["source"] = "Kroger"
    kroger["source_detail"] = KROGER_STORE_NAME

    kroger["geography"] = KROGER_LOCATION

    # Comparable price used in Tableau.
    # This uses the sale price when one exists.
    kroger["price"] = kroger["normalized_price"]

    # Normalized regular price.
    kroger["regular_price_normalized"] = (
        kroger["regular_price"]
        / kroger["unit_quantity"]
    )

    # Normalized promotional price.
    kroger["promo_price_normalized"] = (
        kroger["promo_price"]
        / kroger["unit_quantity"]
    )

    kroger["on_sale"] = (
        kroger["on_sale"]
        .fillna(0)
        .astype(int)
        .astype(bool)
    )

    result = pd.DataFrame(
        {
            "date": kroger["date"],
            "category": kroger["category"],
            "source": kroger["source"],
            "source_detail": kroger["source_detail"],
            "geography": kroger["geography"],
            "price": kroger["price"],
            "standard_unit": kroger["standard_unit"],
            "product_name": kroger["product_name"],
            "product_id": kroger["product_id"],
            "package_size": kroger["package_size"],
            "location_id": kroger["location_id"],
            "regular_price": kroger["regular_price"],
            "promo_price": kroger["promo_price"],
            "effective_price": kroger["effective_price"],
            "regular_price_normalized": (
                kroger["regular_price_normalized"]
            ),
            "promo_price_normalized": (
                kroger["promo_price_normalized"]
            ),
            "on_sale": kroger["on_sale"],
        }
    )

    return result


def build_bls_history(bls):
    bls = bls.copy()

    bls["date"] = pd.to_datetime(
        bls["observation_date"]
    )

    result = pd.DataFrame(
        {
            "date": bls["date"],
            "category": bls["category"],
            "source": "BLS",
            "source_detail": "U.S. City Average",
            "geography": bls["geography"],
            "price": bls["bls_price"],
            "standard_unit": bls["standard_unit"],
            "product_name": bls["bls_item_name"],
            "product_id": bls["series_id"],
            "package_size": pd.NA,
            "location_id": pd.NA,
            "regular_price": pd.NA,
            "promo_price": pd.NA,
            "effective_price": pd.NA,
            "regular_price_normalized": pd.NA,
            "promo_price_normalized": pd.NA,
            "on_sale": False,
        }
    )

    return result


def build_long_history(kroger, bls):
    kroger_history = build_kroger_history(kroger)
    bls_history = build_bls_history(bls)

    history = pd.concat(
        [
            bls_history,
            kroger_history,
        ],
        ignore_index=True,
    )

    history["date"] = pd.to_datetime(
        history["date"]
    )

    history = history.sort_values(
        [
            "category",
            "date",
            "source",
        ]
    ).reset_index(drop=True)

    return history


def build_latest_comparison(kroger, bls):
    kroger = kroger.copy()
    bls = bls.copy()

    kroger["snapshot_date"] = pd.to_datetime(
        kroger["snapshot_date"]
    )

    bls["observation_date"] = pd.to_datetime(
        bls["observation_date"]
    )

    # Get latest Kroger observation for each category.
    latest_kroger = (
        kroger.sort_values("snapshot_date")
        .groupby("category", as_index=False)
        .tail(1)
        .copy()
    )

    latest_kroger = latest_kroger[
        [
            "category",
            "snapshot_date",
            "product_name",
            "standard_unit",
            "regular_price",
            "promo_price",
            "effective_price",
            "normalized_price",
            "on_sale",
        ]
    ]

    latest_kroger = latest_kroger.rename(
        columns={
            "snapshot_date": "kroger_date",
            "product_name": "kroger_product",
            "normalized_price": "kroger_price",
        }
    )

    # Get latest BLS observation for each category.
    latest_bls = (
        bls.sort_values("observation_date")
        .groupby("category", as_index=False)
        .tail(1)
        .copy()
    )

    latest_bls = latest_bls[
        [
            "category",
            "observation_date",
            "bls_item_name",
            "standard_unit",
            "bls_price",
        ]
    ]

    latest_bls = latest_bls.rename(
        columns={
            "observation_date": "bls_date",
            "bls_item_name": "bls_item",
            "standard_unit": "bls_standard_unit",
        }
    )

    comparison = latest_kroger.merge(
        latest_bls,
        on="category",
        how="inner",
    )

    # Confirm both sources use the same standardized unit.
    comparison["units_match"] = (
        comparison["standard_unit"]
        == comparison["bls_standard_unit"]
    )

    comparison["price_difference"] = (
        comparison["kroger_price"]
        - comparison["bls_price"]
    )

    comparison["price_difference_pct"] = (
        (
            comparison["kroger_price"]
            / comparison["bls_price"]
        )
        - 1
    ) * 100

    comparison["kroger_vs_bls"] = comparison[
        "price_difference_pct"
    ].apply(
        lambda x: (
            "Above BLS"
            if x > 0
            else "Below BLS"
            if x < 0
            else "Equal to BLS"
        )
    )

    comparison = comparison.sort_values(
        "price_difference_pct",
        ascending=False,
    ).reset_index(drop=True)

    return comparison


def print_summary(history, comparison):
    print()
    print("TABLEAU DATA BUILD")
    print("=" * 70)

    print(f"Historical rows: {len(history)}")
    print(
        f"Categories:      "
        f"{history['category'].nunique()}"
    )

    print()
    print("Rows by source:")

    source_counts = history["source"].value_counts()

    for source, count in source_counts.items():
        print(f"  {source:<10} {count}")

    print()
    print(
        f"Kroger/BLS comparable categories: "
        f"{len(comparison)}"
    )

    print()
    print("Latest Kroger vs BLS comparison:")
    print("-" * 70)

    for _, row in comparison.iterrows():
        print(
            f"{row['category']:<20} "
            f"Kroger ${row['kroger_price']:.2f} | "
            f"BLS ${row['bls_price']:.2f} | "
            f"{row['price_difference_pct']:+.1f}%"
        )


def main():
    TABLEAU_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    kroger, bls = load_data()

    history = build_long_history(
        kroger,
        bls,
    )

    comparison = build_latest_comparison(
        kroger,
        bls,
    )

    history.to_csv(
        HISTORY_OUTPUT,
        index=False,
        date_format="%Y-%m-%d",
    )

    comparison.to_csv(
        COMPARISON_OUTPUT,
        index=False,
        date_format="%Y-%m-%d",
    )

    print_summary(
        history,
        comparison,
    )

    print()
    print("=" * 70)
    print("TABLEAU FILES CREATED")
    print()
    print("Historical dataset:")
    print(HISTORY_OUTPUT)
    print()
    print("Latest comparison:")
    print(COMPARISON_OUTPUT)


if __name__ == "__main__":
    main()