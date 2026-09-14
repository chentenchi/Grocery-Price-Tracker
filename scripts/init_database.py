import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

DATABASE_FILE = BASE_DIR / "data" / "grocery_prices.db"
PRODUCTS_FILE = BASE_DIR / "data" / "products.csv"
HISTORY_FILE = BASE_DIR / "data" / "price_history.csv"


def main():
    print("\nINITIALIZING GROCERY PRICE DATABASE")
    print("=" * 70)

    # Preserve leading zeroes in IDs.
    products = pd.read_csv(
        PRODUCTS_FILE,
        dtype={
            "product_id": str,
        },
    )

    history = pd.read_csv(
        HISTORY_FILE,
        dtype={
            "product_id": str,
            "location_id": str,
        },
    )

    connection = sqlite3.connect(DATABASE_FILE)

    cursor = connection.cursor()

    # ---------------------------------------------------------
    # Product master table
    # ---------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            product_name TEXT NOT NULL,
            package_size TEXT,
            standard_unit TEXT,
            unit_quantity REAL
        )
        """
    )

    # ---------------------------------------------------------
    # Historical price table
    # ---------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            snapshot_date TEXT NOT NULL,
            location_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            category TEXT,
            product_name TEXT,
            package_size TEXT,
            standard_unit TEXT,
            unit_quantity REAL,
            regular_price REAL,
            promo_price REAL,
            effective_price REAL,
            normalized_price REAL,
            on_sale INTEGER,

            PRIMARY KEY (
                snapshot_date,
                location_id,
                product_id
            ),

            FOREIGN KEY (product_id)
                REFERENCES products(product_id)
        )
        """
    )

    # ---------------------------------------------------------
    # Insert products
    # ---------------------------------------------------------

    for _, row in products.iterrows():
        cursor.execute(
            """
            INSERT OR REPLACE INTO products (
                product_id,
                category,
                product_name,
                package_size,
                standard_unit,
                unit_quantity
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["product_id"],
                row["category"],
                row["product_name"],
                row["package_size"],
                row["standard_unit"],
                row["unit_quantity"],
            ),
        )

    # ---------------------------------------------------------
    # Insert historical prices
    # ---------------------------------------------------------

    for _, row in history.iterrows():
        promo_price = (
            None
            if pd.isna(row["promo_price"])
            else float(row["promo_price"])
        )

        cursor.execute(
            """
            INSERT OR REPLACE INTO price_history (
                snapshot_date,
                location_id,
                product_id,
                category,
                product_name,
                package_size,
                standard_unit,
                unit_quantity,
                regular_price,
                promo_price,
                effective_price,
                normalized_price,
                on_sale
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["snapshot_date"],
                row["location_id"],
                row["product_id"],
                row["category"],
                row["product_name"],
                row["package_size"],
                row["standard_unit"],
                row["unit_quantity"],
                row["regular_price"],
                promo_price,
                row["effective_price"],
                row["normalized_price"],
                int(row["on_sale"]),
            ),
        )

    connection.commit()

    # ---------------------------------------------------------
    # Verify row counts
    # ---------------------------------------------------------

    product_count = cursor.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    price_count = cursor.execute(
        "SELECT COUNT(*) FROM price_history"
    ).fetchone()[0]

    connection.close()

    print(f"Products loaded:      {product_count}")
    print(f"Price records loaded: {price_count}")
    print()
    print("Database created:")
    print(DATABASE_FILE)
    print()
    print("Database initialization complete.")


if __name__ == "__main__":
    main()