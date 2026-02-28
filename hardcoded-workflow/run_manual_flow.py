"""
NovaBoard Electronics — Production Scheduling Agent
6-Step Production Workflow

API base: https://hackathon33.arke.so
  sales-api:   /api/sales/...
  product-api: /api/product/...
"""

from typing import List

import httpx
from arke_client import ArkeClient
from constants import BASE_URL, PASSWORD, TODAY, USERNAME
from data_loaders import create_production_orders, load_product_mapping, load_sales_orders
from models import ProductionOrder
from phase_executor import PhaseExecutor, execute_all_orders
from scheduling import plan_edf_schedule, schedule_phases
from telegram_bot import send_message_and_wait_for_approval
from tqdm import tqdm

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
        client = ArkeClient(http_client, BASE_URL)

        # Load data
        product_mapping = load_product_mapping(client)

        # Step 1: Read open orders — show what needs to be produced
        sales_orders = load_sales_orders(client, product_mapping)

        # Step 2: Choose a planning policy (pure reasoning, no API calls)
        production_plan = plan_edf_schedule(sales_orders)

        # Step 3: Create production orders in Arke
        production_orders = create_production_orders(client, production_plan)

        # Step 4: Schedule phases with concrete start/end dates
        production_orders = schedule_phases(client, production_orders)

        # Step 5: Human-in-the-loop — present schedule and get approval
        approved = get_human_approval(production_orders)
        if not approved:
            print("\n[abort] Operator did not approve. Exiting.")
            return

        # Confirm orders in Arke (moves to in_progress, first phase ready_to_start)
        confirm_production_orders(client, production_orders)

        # Step 6: Physical integration — advance production with real-time signals
        executor = PhaseExecutor(client)
        execute_all_orders(executor, production_orders)

    print("\n[done] Scheduling complete.")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def login(client: httpx.Client) -> str:
    """POST /api/login -> Bearer token."""
    resp = client.post(f"{BASE_URL}/api/login", json={"username": USERNAME, "password": PASSWORD})
    resp.raise_for_status()
    token: str = resp.json()["accessToken"]
    print(f"[auth] OK — token: {token[:30]}...")
    return token


# ---------------------------------------------------------------------------
# Step 5 — Human-in-the-loop approval
# ---------------------------------------------------------------------------


def get_human_approval(production_orders: List[ProductionOrder]) -> bool:
    """
    Step 5: Present the proposed schedule to the production planner via Telegram.

    Returns True if the operator approves.
    """
    print("\n[Step 5] Preparing schedule for human approval...")

    lines = ["📋 NovaBoard Production Schedule — Feb 28 2026\n"]
    for po in production_orders:
        so = po.sales_order
        flag = "✅ OK" if po.on_time else "⚠️ LATE"
        lines.append(
            f"• {so.internal_id} ({so.customer_name}) — {so.product_name} x{so.quantity}\n"
            f"  📅 {po.starts_at.strftime('%b %d')} → {po.ends_at.strftime('%b %d')} "
            f"| deadline {so.deadline.strftime('%b %d')} | P{so.priority} {flag}"
        )

    lines.append("\n✉️ Reply /approve to confirm, or /disapprove to defer.")
    message = "\n".join(lines)

    print("\n[Telegram] Sending message to operator...")
    print("-" * 60)
    print(message)
    print("-" * 60)

    print("\n[Step 5] Waiting for operator approval...")
    approved = send_message_and_wait_for_approval(message)

    if approved:
        print("[Step 5] ✅ Schedule approved by operator")
    else:
        print("[Step 5] ❌ Schedule rejected by operator")

    return approved


# ---------------------------------------------------------------------------
# Confirm production orders (after approval)
# ---------------------------------------------------------------------------


def confirm_production_orders(
    client: ArkeClient,
    production_orders: List[ProductionOrder],
) -> None:
    """
    Confirm production orders in Arke after human approval.

    POST /api/product/production/{id}/_start

    Moves order from scheduled to in_progress; first phase becomes ready_to_start.
    """
    print("\n[Arke] Starting production orders...")
    for po in tqdm(production_orders, desc="Starting orders"):
        client.start_production_order(po.production_order_id)
        print(f"  ✅ {po.sales_order.internal_id} → in_progress")


if __name__ == "__main__":
    main()
