import requests
import pandas as pd

from kroger_auth import get_access_token


PRODUCTS_URL = "https://api.kroger.com/v1/products"

# Kroger On the Rhine
LOCATION_ID = "01400513"


def search_products(search_term, limit=20):
    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    params = {
        "filter.term": search_term,
        "filter.locationId": LOCATION_ID,
        "filter.limit": limit,
    }

    response = requests.get(
        PRODUCTS_URL,
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json().get("data", [])


def format_products(products):
    rows = []

    for number, product in enumerate(products, start=1):
        items = product.get("items", [])

        if items:
            item = items[0]

            size = item.get("size", "N/A")
            price = item.get("price", {})

            regular_price = price.get("regular")
            promo_price = price.get("promo")

        else:
            size = "N/A"
            regular_price = None
            promo_price = None

        rows.append(
            {
                "#": number,
                "Product": product.get("description", "N/A"),
                "Brand": product.get("brand", "N/A"),
                "Product ID": product.get("productId", "N/A"),
                "Size": size,
                "Regular": regular_price,
                "Promo": promo_price,
            }
        )

    return pd.DataFrame(rows)


def main():
    print("\nKROGER PRODUCT SEARCH")
    print("=" * 70)
    print("Store: Kroger On the Rhine")
    print(f"Location ID: {LOCATION_ID}")
    print("\nType a grocery item to search.")
    print("Examples: eggs, milk, bread, butter")
    print("Type 'q' to quit.\n")

    while True:
        search_term = input("Search: ").strip()

        if search_term.lower() in ["q", "quit", "exit"]:
            print("\nExiting product search.")
            break

        if not search_term:
            continue

        try:
            products = search_products(search_term)

            if not products:
                print(f"\nNo products found for '{search_term}'.\n")
                continue

            df = format_products(products)

            print(f"\nResults for: {search_term}\n")

            print(
                df.to_string(
                    index=False,
                    formatters={
                        "Regular": lambda x: (
                            f"${x:.2f}" if pd.notna(x) else "-"
                        ),
                        "Promo": lambda x: (
                            f"${x:.2f}" if pd.notna(x) else "-"
                        ),
                    },
                )
            )

            print()

        except requests.exceptions.HTTPError as error:
            print(f"\nKroger API error: {error}\n")

        except requests.exceptions.RequestException as error:
            print(f"\nConnection error: {error}\n")


if __name__ == "__main__":
    main()