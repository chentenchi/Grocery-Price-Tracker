import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_FILE = BASE_DIR / "data" / "grocery_prices.db"


def main():
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    product_count = cursor.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    price_count = cursor.execute(
        "SELECT COUNT(*) FROM price_history"
    ).fetchone()[0]

    print("\nDATABASE CHECK")
    print("=" * 60)
    print(f"Products:      {product_count}")
    print(f"Price records: {price_count}")

    print("\nRecords by date:")

    dates = cursor.execute(
        """
        SELECT
            snapshot_date,
            COUNT(*)
        FROM price_history
        GROUP BY snapshot_date
        ORDER BY snapshot_date
        """
    ).fetchall()

    for snapshot_date, count in dates:
        print(f"{snapshot_date}: {count} records")

    print("\nSample records:")

    rows = cursor.execute(
        """
        SELECT
            category,
            regular_price,
            promo_price,
            effective_price,
            normalized_price,
            on_sale
        FROM price_history
        ORDER BY category
        LIMIT 10
        """
    ).fetchall()

    for row in rows:
        print(row)

    connection.close()


if __name__ == "__main__":
    main()