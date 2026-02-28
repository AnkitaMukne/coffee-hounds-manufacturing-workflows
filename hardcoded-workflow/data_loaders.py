"""
Data loading functions: fetch and parse products, sales orders, and production orders from Arke.
"""

from typing import Dict, List

from arke_client import ArkeClient
from data_extraction import safe_extract
from models import ProductionOrder, SalesOrder
from tqdm import tqdm
from utils import format_utc_datetime, infer_product_code, parse_deadline


def load_product_mapping(client: ArkeClient) -> Dict[str, str]:
    """
    Fetch all products and build a mapping from name/internal_id to product_id.

    GET /api/product/product

    Returns: Dict with both name and internal_id as keys pointing to product_id
    """
    print("\n[Setup] Building product mapping...")
    products = client.get_products()

    mapping: Dict[str, str] = {}
    for p in products:
        product_id = p.get("id")
        name = p.get("name")
        internal_id = p.get("internal_id")

        if name and product_id:
            mapping[name] = product_id
        if internal_id and product_id:
            mapping[internal_id] = product_id

    print(f"[Setup] Mapped {len(products)} products to {len(mapping)} lookup keys")
    return mapping


def load_sales_orders(client: ArkeClient, product_mapping: Dict[str, str]) -> List[SalesOrder]:
    """
    Step 1: Load and parse all accepted sales orders, sorted by urgency (EDF + priority).

    GET /api/sales/order?status=accepted
    GET /api/sales/order/{id}
    """
    summaries: List[Dict] = client.get_sales_orders(status="accepted", limit=1000)

    orders: List[SalesOrder] = []
    for s in tqdm(summaries, desc="[Step 1] Fetching order details"):
        d: Dict = client.get_sales_order(s["id"])

        deadline = parse_deadline(d["expected_shipping_time"])
        priority = safe_extract(d, "priority", 3, int)
        customer_name = safe_extract(d.get("customer_attr") or {}, "name", "Unknown")

        for line in d.get("products", []):
            product_name = safe_extract(line, "name", "")
            product_id = (
                product_mapping.get(safe_extract(line, "extra_id", ""))
                or product_mapping.get(product_name)
                or line.get("extra_id")
            )

            orders.append(
                SalesOrder(
                    id=s["id"],
                    internal_id=safe_extract(d, "internal_id", s["id"]),
                    customer_name=customer_name,
                    product_id=product_id,
                    product_name=product_name,
                    product_code=infer_product_code(product_name),
                    quantity=safe_extract(line, "quantity", 1, int),
                    deadline=deadline,
                    priority=priority,
                )
            )
            if not orders[-1].product_id or orders[-1].product_id not in product_mapping.values():
                print(
                    f"⚠️ Warning: Could not resolve product_id for '{product_name}'"
                    f" (got: {product_id})"
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


def create_production_orders(
    client: ArkeClient,
    production_plan: List[ProductionOrder],
) -> List[ProductionOrder]:
    """
    Step 3: Create production orders in Arke for each item in the plan.

    PUT /api/product/production
    """
    print("\n[Step 3] Creating production orders in Arke...")

    updated: List[ProductionOrder] = []
    for po in tqdm(production_plan, desc="Creating production orders"):
        body = {
            "product_id": po.sales_order.product_id,
            "quantity": po.sales_order.quantity,
            "starts_at": format_utc_datetime(po.starts_at),
            "ends_at": format_utc_datetime(po.ends_at),
        }
        prod_order_data = client.create_production_order(body)
        production_order_id = prod_order_data["id"]
        updated.append(po.model_copy(update={"production_order_id": production_order_id}))

    print(f"[Step 3] Created {len(updated)} production orders")
    return updated
