from datetime import date
from pathlib import Path
import sqlite3
import time

import pandas as pd
import requests

from kroger_auth import get_access_token


BASE_DIR = Path(__file__).resolve().parents[1]

PRODUCTS_FILE = BASE_DIR / "data" / "products.csv"
RAW_DIR = BASE_DIR / "data" / "raw"
HISTORY_FILE = BASE_DIR / "data" / "price_history.csv"
DATABASE_FILE = BASE_DIR / "data" / "grocery_prices.db"

PRODUCTS_URL = "https://api.kroger.com/v1/products"

# Kroger On the Rhine
LOCATION_ID = "01400513"


def get_product(product_id, token, max_retries=3):
    url = f"{PRODUCTS_URL}/{product_id}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    params = {
        "filter.locationId": LOCATION_ID,
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30,
            )

            if response.status_code in [429, 500, 502, 503, 504]:
                print(
                    f"  Temporary API error "
                    f"({response.status_code}). "
                    f"Retry {attempt}/{max_retries}..."
                )

                time.sleep(attempt * 2)
                continue

            response.raise_for_status()

            return response.json().get("data")

        except requests.exceptions.RequestException as error:
            if attempt == max_retries:
                print(f"  Request failed: {error}")
                return None

            time.sleep(attempt * 2)

    return None


def extract_price(product):
    if not product:
        return None, None

    items = product.get("items", [])

    if not items:
        return None, None

    price = items[0].get("price", {})

    regular_price = price.get("regular")
    promo_price = price.get("promo")

    return regular_price, promo_price


def save_to_database(snapshot):
    connection = sqlite3.connect(DATABASE_FILE)

    connection.execute("PRAGMA foreign_keys = ON")

    cursor = connection.cursor()

    for _, row in snapshot.iterrows():
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
    connection.close()


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    products = pd.read_csv(
        PRODUCTS_FILE,
        dtype={"product_id": str},
    )

    print()
    print("KROGER PRICE COLLECTION")
    print("=" * 70)
    print(f"Store Location ID: {LOCATION_ID}")
    print(f"Products to collect: {len(products)}")
    print()

    token = get_access_token()

    snapshot_date = date.today().isoformat()

    rows = []

    for number, (_, product_row) in enumerate(
        products.iterrows(),
        start=1,
    ):
        product_id = product_row["product_id"]
        category = product_row["category"]

        print(
            f"[{number:02d}/{len(products)}] "
            f"{category}: {product_id}"
        )

        api_product = get_product(
            product_id=product_id,
            token=token,
        )

        regular_price, promo_price = extract_price(api_product)

        if promo_price is not None and promo_price > 0:
            effective_price = promo_price
            on_sale = True
        else:
            effective_price = regular_price
            on_sale = False

        unit_quantity = float(product_row["unit_quantity"])

        if effective_price is not None and unit_quantity > 0:
            normalized_price = effective_price / unit_quantity
        else:
            normalized_price = None

        if regular_price is not None:
            print(f"   Regular: ${regular_price:.2f}")

        if promo_price is not None:
            print(f"   Promo:   ${promo_price:.2f}")

        if normalized_price is not None:
            print(
                f"   Normalized: "
                f"${normalized_price:.2f} "
                f"per {product_row['standard_unit']}"
            )

        if regular_price is None:
            print("   WARNING: No price returned")

        rows.append(
            {
                "snapshot_date": snapshot_date,
                "location_id": LOCATION_ID,
                "category": category,
                "product_name": product_row["product_name"],
                "product_id": product_id,
                "package_size": product_row["package_size"],
                "standard_unit": product_row["standard_unit"],
                "unit_quantity": unit_quantity,
                "regular_price": regular_price,
                "promo_price": promo_price,
                "effective_price": effective_price,
                "normalized_price": normalized_price,
                "on_sale": on_sale,
            }
        )

        time.sleep(0.2)

    snapshot = pd.DataFrame(rows)

    # ---------------------------------------------------------
    # Save daily raw snapshot
    # ---------------------------------------------------------

    snapshot_file = (
        RAW_DIR / f"kroger_prices_{snapshot_date}.csv"
    )

    snapshot.to_csv(
        snapshot_file,
        index=False,
    )

    # ---------------------------------------------------------
    # Maintain combined CSV history
    # ---------------------------------------------------------

    if HISTORY_FILE.exists():
        history = pd.read_csv(
            HISTORY_FILE,
            dtype={
                "product_id": str,
                "location_id": str,
            },
        )

        # Remove existing records for this same store/date.
        duplicate_mask = (
            (history["snapshot_date"].astype(str) == snapshot_date)
            & (history["location_id"].astype(str) == LOCATION_ID)
        )

        history = history[~duplicate_mask]

        history = pd.concat(
            [history, snapshot],
            ignore_index=True,
        )

    else:
        history = snapshot

    history.to_csv(
        HISTORY_FILE,
        index=False,
    )

    # ---------------------------------------------------------
    # Save directly into SQLite
    # ---------------------------------------------------------

    save_to_database(snapshot)

    successful = snapshot["regular_price"].notna().sum()
    failed = len(snapshot) - successful

    print()
    print("=" * 70)
    print("COLLECTION COMPLETE")
    print(f"Date: {snapshot_date}")
    print(f"Successful: {successful}")
    print(f"Missing price: {failed}")
    print()
    print("Saved to:")
    print(f"1. Raw snapshot: {snapshot_file}")
    print(f"2. CSV history:  {HISTORY_FILE}")
    print(f"3. SQLite DB:    {DATABASE_FILE}")


if __name__ == "__main__":
    main()