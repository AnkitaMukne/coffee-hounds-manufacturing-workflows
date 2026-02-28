"""
Data loading functions for NovaBoard Electronics Production Scheduling Agent.

Provides functions for loading and caching product and sales order data.
"""

from typing import Dict, List

from arke_client import ArkeClient
from tqdm import tqdm

from constants import BASE_URL, PASSWORD, USERNAME
from models import SalesOrder
from utils import infer_product_code, parse_deadline


def login(client) -> str:
    """
    Authenticate with Arke API.

    Args:
        client: httpx.Client instance

    Returns:
        Bearer token
    """
    resp = client.post(f"{BASE_URL}/api/login", json={"username": USERNAME, "password": PASSWORD})
    resp.raise_for_status()
    token: str = resp.json()["accessToken"]
    print(f"[auth] OK — token: {token[:30]}...")
    return token


def build_product_mapping(arke_client: ArkeClient) -> Dict[str, str]:
    """
    Build product name/internal_id -> product_id mapping.

    Args:
        arke_client: ArkeClient instance

    Returns:
        Dictionary mapping product names and internal_ids to product_ids
    """
    print("\n[Setup] Building product mapping...")
    products = arke_client.get_products()

    mapping = {}
    for p in products:
        try:
            product_id = p["id"]
            try:
                name = p["name"]
                mapping[name] = product_id
            except KeyError:
                print(f"⚠️ Warning: Product {product_id} missing 'name' field")

            try:
                internal_id = p["internal_id"]
                mapping[internal_id] = product_id
            except KeyError:
                print(f"⚠️ Warning: Product {product_id} missing 'internal_id' field")
        except KeyError:
            print(f"⚠️ Warning: Product entry missing 'id' field: {p}")
            continue

    print(f"[Setup] Mapped {len(products)} products to {len(mapping)} lookup keys")
    return mapping


def build_product_details_cache(
    arke_client: ArkeClient, product_mapping: Dict[str, str]
) -> Dict[str, Dict]:
    """
    Fetch and cache product details with process_lines.

    Args:
        arke_client: ArkeClient instance
        product_mapping: Product mapping dictionary

    Returns:
        Dictionary mapping product_id to product details
    """
    print("\n[Setup] Caching product details with process_lines...")
    cache = {}
    unique_product_ids = set(product_mapping.values())

    for product_id in tqdm(unique_product_ids, desc="Fetching product details"):
        try:
            cache[product_id] = arke_client.get_product_details(product_id)
        except Exception as e:
            print(f"⚠️ Warning: Could not fetch details for product {product_id}: {e}")
            cache[product_id] = {"process_lines": []}

    print(f"[Setup] Cached details for {len(cache)} products")
    return cache


def load_sales_orders(arke_client: ArkeClient, product_mapping: Dict[str, str]) -> List[SalesOrder]:
    """
    Load and parse all accepted sales orders.

    Args:
        arke_client: ArkeClient instance
        product_mapping: Product mapping dictionary

    Returns:
        List of SalesOrder objects sorted by urgency (deadline, then priority)
    """
    summaries = arke_client.get_sales_orders(status="accepted", limit=1000)

    orders: List[SalesOrder] = []
    for s in tqdm(summaries, desc="[Step 1] Fetching order details"):
        d = arke_client.get_sales_order_details(s["id"])

        try:
            deadline = parse_deadline(d["expected_shipping_time"])
        except KeyError:
            print(f"⚠️ Warning: Order {s['id']} missing 'expected_shipping_time', skipping")
            continue

        try:
            priority = int(d["priority"])
        except KeyError:
            print(f"⚠️ Warning: Order {s['id']} missing 'priority', defaulting to 3")
            priority = 3

        try:
            customer_name = d["customer_attr"]["name"]
        except KeyError:
            print(f"⚠️ Warning: Order {s['id']} missing customer name, using 'Unknown'")
            customer_name = "Unknown"

        try:
            products_list = d["products"]
        except KeyError:
            print(f"⚠️ Warning: Order {s['id']} missing 'products' field, skipping")
            continue

        for line in products_list:
            try:
                product_name = line["name"]
            except KeyError:
                print(f"⚠️ Warning: Product line in order {s['id']} missing 'name', skipping")
                continue

            # Try to resolve product_id from mapping
            product_id = None
            try:
                extra_id = line["extra_id"]
                product_id = product_mapping.get(extra_id)
            except KeyError:
                pass

            if not product_id:
                product_id = product_mapping.get(product_name)

            if not product_id:
                try:
                    product_id = line["extra_id"]
                except KeyError:
                    print(f"⚠️ Warning: Could not resolve product_id for '{product_name}'")
                    product_id = None

            try:
                quantity = int(line["quantity"])
            except KeyError:
                print(
                    f"⚠️ Warning: Product line '{product_name}' missing 'quantity', defaulting to 1"
                )
                quantity = 1

            try:
                internal_id = d["internal_id"]
            except KeyError:
                internal_id = s["id"]

            orders.append(
                SalesOrder(
                    id=s["id"],
                    internal_id=internal_id,
                    customer_name=customer_name,
                    product_id=product_id,
                    product_name=product_name,
                    product_code=infer_product_code(product_name),
                    quantity=quantity,
                    deadline=deadline,
                    priority=priority,
                )
            )
            if not orders[-1].product_id or orders[-1].product_id not in product_mapping.values():
                print(
                    f"⚠️ Warning: Could not resolve product_id for '{product_name}' (got: {product_id})"
                )

    # EDF: nearest deadline first, ties broken by priority (lower = more urgent)
    orders.sort(key=lambda o: (o.deadline, o.priority))

    print(f"\n[Step 1] {len(orders)} sales order lines (sorted by urgency):")
    for o in orders:
        print(
            f"  {o.internal_id} | {o.customer_name} | {o.product_name} x{o.quantity} "
            f"| deadline {o.deadline.date()} | P{o.priority}"
        )

    return orders
