"""
NovaBoard Electronics — Production Scheduling Agent
6-Step Production Workflow

API base: https://hackathon33.arke.so
  sales-api:   /api/sales/...
  product-api: /api/product/...
"""

import httpx
from arke_client import ArkeClient
from data_loaders import (
    build_product_details_cache,
    build_product_mapping,
    load_sales_orders,
    login,
)
from phase_executor import PhaseExecutor, execute_all_orders
from scheduling import (
    confirm_production_orders,
    create_production_orders,
    get_human_approval,
    plan_edf_schedule,
    schedule_phases,
)

from constants import TODAY

# -------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("NovaBoard Electronics — Production Scheduling Agent")
    print(f"Date: {TODAY.date()}")
    print("=" * 60)

    with httpx.Client(timeout=30) as http_client:
        # Auth
        token = login(http_client)
        http_client.headers["Authorization"] = f"Bearer {token}"

        # Setup ArkeClient
        arke_client = ArkeClient(http_client)

        # Load data
        product_mapping = build_product_mapping(arke_client)
        product_details_cache = build_product_details_cache(arke_client, product_mapping)
        sales_orders = load_sales_orders(arke_client, product_mapping)

        # Plan
        production_plan = plan_edf_schedule(sales_orders)

        # Create in system
        production_orders = create_production_orders(arke_client, production_plan)
        production_orders = schedule_phases(arke_client, production_orders, product_details_cache)

        # Approve
        approved = get_human_approval(production_orders)
        if not approved:
            print("\n[abort] Operator did not approve. Exiting.")
            return

        confirm_production_orders(arke_client, production_orders)

        # Execute
        executor = PhaseExecutor(arke_client)
        execute_all_orders(executor, production_orders)

    print("\n[done] Scheduling complete.")


if __name__ == "__main__":
    main()
