import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_FILE = BASE_DIR / "data" / "grocery_prices.db"


def main():
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    print()
    print("BLS DATABASE CHECK")
    print("=" * 75)

    total = cursor.execute(
        """
        SELECT COUNT(*)
        FROM bls_price_history
        """
    ).fetchone()[0]

    categories = cursor.execute(
        """
        SELECT COUNT(DISTINCT category)
        FROM bls_price_history
        """
    ).fetchone()[0]

    print(f"Total observations: {total}")
    print(f"Categories:         {categories}")

    print()
    print("DATE COVERAGE")
    print("=" * 75)

    coverage = cursor.execute(
        """
        SELECT
            category,
            MIN(observation_date),
            MAX(observation_date),
            COUNT(*)
        FROM bls_price_history
        GROUP BY category
        ORDER BY category
        """
    ).fetchall()

    for category, first_date, last_date, count in coverage:
        print(
            f"{category:<20} "
            f"{first_date} to {last_date} "
            f"({count} observations)"
        )

    print()
    print("LATEST BLS PRICES")
    print("=" * 75)

    latest = cursor.execute(
        """
        SELECT
            b.category,
            b.observation_date,
            b.bls_price,
            b.standard_unit
        FROM bls_price_history b
        INNER JOIN (
            SELECT
                category,
                MAX(observation_date) AS latest_date
            FROM bls_price_history
            GROUP BY category
        ) latest_dates
            ON b.category = latest_dates.category
            AND b.observation_date = latest_dates.latest_date
        ORDER BY b.category
        """
    ).fetchall()

    for category, observation_date, price, unit in latest:
        print(
            f"{category:<20} "
            f"{observation_date}   "
            f"${price:.2f} per {unit}"
        )

    connection.close()


if __name__ == "__main__":
    main()