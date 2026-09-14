import sqlite3
from pathlib import Path

import pandas as pd
import requests


BASE_DIR = Path(__file__).resolve().parents[1]

OUTPUT_FILE = BASE_DIR / "data" / "bls_price_history.csv"
DATABASE_FILE = BASE_DIR / "data" / "grocery_prices.db"

BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"

START_YEAR = "2017"
END_YEAR = "2026"


# ---------------------------------------------------------
# BLS series matched to our Kroger categories
# ---------------------------------------------------------

BLS_SERIES = {
    "APU0000701111": {
        "category": "Flour",
        "bls_item_name": "Flour, white, all purpose",
        "standard_unit": "pound",
    },

    "APU0000701312": {
        "category": "Rice",
        "bls_item_name": "Rice, white, long grain, uncooked",
        "standard_unit": "pound",
    },

    "APU0000701322": {
        "category": "Pasta",
        "bls_item_name": "Spaghetti and macaroni",
        "standard_unit": "pound",
    },

    "APU0000702111": {
        "category": "Bread",
        "bls_item_name": "Bread, white, pan",
        "standard_unit": "pound",
    },

    "APU0000FC1101": {
        "category": "Ground Beef",
        "bls_item_name": "All uncooked ground beef",
        "standard_unit": "pound",
    },

    "APU0000FF1101": {
        "category": "Chicken Breast",
        "bls_item_name": "Chicken breast, boneless",
        "standard_unit": "pound",
    },

    "APU0000708111": {
        "category": "Eggs",
        "bls_item_name": "Eggs, Grade A, large",
        "standard_unit": "dozen",
    },

    "APU0000709112": {
        "category": "Milk",
        "bls_item_name": "Milk, fresh, whole, fortified",
        "standard_unit": "gallon",
    },

    "APU0000FS1101": {
        "category": "Butter",
        "bls_item_name": "Butter, in sticks",
        "standard_unit": "pound",
    },

    "APU0000710212": {
        "category": "Cheddar Cheese",
        "bls_item_name": "Cheddar cheese, natural",
        "standard_unit": "pound",
    },

    "APU0000711211": {
        "category": "Bananas",
        "bls_item_name": "Bananas",
        "standard_unit": "pound",
    },

    "APU0000712112": {
        "category": "Potatoes",
        "bls_item_name": "Potatoes, white",
        "standard_unit": "pound",
    },

    "APU0000712311": {
        "category": "Tomatoes",
        "bls_item_name": "Tomatoes, field grown",
        "standard_unit": "pound",
    },

    "APU0000715211": {
        "category": "Sugar",
        "bls_item_name": "Sugar, white, all sizes",
        "standard_unit": "pound",
    },

    "APU0000717311": {
        "category": "Coffee",
        "bls_item_name": "Coffee, 100 percent, ground roast",
        "standard_unit": "pound",
    },

    "APU0000718311": {
        "category": "Potato Chips",
        "bls_item_name": "Potato chips",
        "standard_unit": "pound",
    },
}


def get_bls_data():
    payload = {
        "seriesid": list(BLS_SERIES.keys()),
        "startyear": START_YEAR,
        "endyear": END_YEAR,
    }

    headers = {
        "Content-Type": "application/json",
    }

    response = requests.post(
        BLS_URL,
        json=payload,
        headers=headers,
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(
            f"BLS request failed: {data.get('message')}"
        )

    return data["Results"]["series"]


def transform_bls_data(series_data):
    rows = []

    for series in series_data:
        series_id = series["seriesID"]

        metadata = BLS_SERIES.get(series_id)

        if metadata is None:
            continue

        for observation in series["data"]:
            period = observation.get("period")

            # Only keep monthly records M01 through M12.
            # Skip annual averages such as M13.
            if not period:
                continue

            if not period.startswith("M"):
                continue

            if period == "M13":
                continue

            year = int(observation["year"])
            month = int(period[1:])

            raw_value = observation.get("value")

            # BLS may return "-" when an average price
            # is unavailable for a particular month.
            if raw_value in [None, "", "-"]:
                continue

            try:
                price = float(raw_value)
            except (TypeError, ValueError):
                continue

            observation_date = pd.Timestamp(
                year=year,
                month=month,
                day=1,
            )

            rows.append(
                {
                    "observation_date": (
                        observation_date.strftime("%Y-%m-%d")
                    ),
                    "year": year,
                    "month": month,
                    "series_id": series_id,
                    "category": metadata["category"],
                    "bls_item_name": metadata["bls_item_name"],
                    "standard_unit": metadata["standard_unit"],
                    "bls_price": price,
                    "geography": "U.S. City Average",
                    "source": "BLS",
                }
            )

    history = pd.DataFrame(rows)

    if history.empty:
        raise RuntimeError(
            "BLS returned no usable historical observations."
        )

    history = history.sort_values(
        ["category", "observation_date"]
    ).reset_index(drop=True)

    return history


def save_to_database(history):
    connection = sqlite3.connect(DATABASE_FILE)

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bls_price_history (
            observation_date TEXT NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            series_id TEXT NOT NULL,
            category TEXT NOT NULL,
            bls_item_name TEXT,
            standard_unit TEXT,
            bls_price REAL,
            geography TEXT,
            source TEXT,

            PRIMARY KEY (
                observation_date,
                series_id
            )
        )
        """
    )

    for _, row in history.iterrows():
        cursor.execute(
            """
            INSERT OR REPLACE INTO bls_price_history (
                observation_date,
                year,
                month,
                series_id,
                category,
                bls_item_name,
                standard_unit,
                bls_price,
                geography,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["observation_date"],
                int(row["year"]),
                int(row["month"]),
                row["series_id"],
                row["category"],
                row["bls_item_name"],
                row["standard_unit"],
                float(row["bls_price"]),
                row["geography"],
                row["source"],
            ),
        )

    connection.commit()

    count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM bls_price_history
        """
    ).fetchone()[0]

    connection.close()

    return count


def main():
    print()
    print("BLS HISTORICAL PRICE COLLECTION")
    print("=" * 70)
    print(f"Period: {START_YEAR}-{END_YEAR}")
    print(f"Series requested: {len(BLS_SERIES)}")
    print()

    print("Requesting BLS data...")

    series_data = get_bls_data()

    print(f"Series returned: {len(series_data)}")

    history = transform_bls_data(series_data)

    print(
        f"Historical observations: {len(history)}"
    )

    print(
        f"Categories with data: "
        f"{history['category'].nunique()}"
    )

    history.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    database_count = save_to_database(history)

    print()
    print("=" * 70)
    print("BLS COLLECTION COMPLETE")
    print()
    print(
        f"CSV observations saved: {len(history)}"
    )
    print(
        f"Database observations:   {database_count}"
    )
    print()
    print("CSV saved to:")
    print(OUTPUT_FILE)
    print()
    print("SQLite DB:")
    print(DATABASE_FILE)


if __name__ == "__main__":
    main()