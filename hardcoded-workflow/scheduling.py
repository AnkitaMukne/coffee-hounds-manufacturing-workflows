"""
Scheduling algorithms for NovaBoard Electronics Production Scheduling Agent.

Provides planning and scheduling functions.
"""

import math
from datetime import timedelta
from typing import Dict, List

from arke_client import ArkeClient
from data_extraction import extract_phase_durations
from tqdm import tqdm

from constants import BOM_MINS_PER_UNIT, MINS_PER_DAY, TODAY
from models import Phase, ProductionOrder, SalesOrder
from utils import format_utc_datetime


def plan_edf_schedule(sales_orders: List[SalesOrder]) -> List[ProductionOrder]:
    """
    Apply Earliest Deadline First scheduling policy.

    Level 1 (Required): Earliest Deadline First (EDF)
    - One production order per sales order line
    - Sort by expected_shipping_time, nearest first
    - Ties broken by priority (lowest number wins)
    - ends_at = the sales order's shipping date

    Args:
        sales_orders: List of sales orders (should be pre-sorted by deadline, priority)

    Returns:
        List of ProductionOrder with starts_at/ends_at computed
    """
    print("\n[Step 2] Applying Earliest Deadline First (EDF) policy...")

    production_orders: List[ProductionOrder] = []
    cursor = TODAY

    for so in sales_orders:
        mins_per_unit = BOM_MINS_PER_UNIT.get(so.product_code, 60)
        total_mins = mins_per_unit * so.quantity
        days_needed = math.ceil(total_mins / MINS_PER_DAY)

        starts_at = cursor
        ends_at = cursor + timedelta(days=days_needed)
        cursor = ends_at

        po = ProductionOrder(sales_order=so, starts_at=starts_at, ends_at=ends_at)
        production_orders.append(po)

    print(f"\n[Step 2] EDF schedule computed ({len(production_orders)} production orders):")
    for po in production_orders:
        so = po.sales_order
        flag = "OK" if po.on_time else "LATE"
        print(
            f"  {so.internal_id}; {so.product_id}: {po.starts_at.date()} -> {po.ends_at.date()} "
            f"(deadline {so.deadline.date()}) [{flag}]"
        )

    return production_orders


def create_production_orders(
    arke_client: ArkeClient, production_plan: List[ProductionOrder]
) -> List[ProductionOrder]:
    """
    Create production orders in Arke.

    Args:
        arke_client: ArkeClient instance
        production_plan: List of planned ProductionOrder objects

    Returns:
        Updated list of ProductionOrder objects with production_order_id set
    """
    print("\n[Step 3] Creating production orders in Arke...")

    updated: List[ProductionOrder] = []
    for po in tqdm(production_plan, desc="Creating production orders"):
        prod_order_data = arke_client.create_production_order(
            product_id=po.sales_order.product_id,
            quantity=po.sales_order.quantity,
            starts_at=format_utc_datetime(po.starts_at),
            ends_at=format_utc_datetime(po.ends_at),
        )
        production_order_id = prod_order_data["id"]
        updated.append(po.model_copy(update={"production_order_id": production_order_id}))

    print(f"[Step 3] Created {len(updated)} production orders")
    return updated


def schedule_phases(
    arke_client: ArkeClient,
    production_orders: List[ProductionOrder],
    product_details_cache: Dict[str, Dict],
) -> List[ProductionOrder]:
    """
    Schedule phases with concrete start/end dates.

    1. Call _schedule on each production order → Arke generates phase sequence from BOM
    2. GET production order to read phases with phase names
    3. Look up duration from product's process_lines
    4. Assign concrete start/end dates to each phase (sequential)
    5. Update each phase with start/end dates

    Args:
        arke_client: ArkeClient instance
        production_orders: List of ProductionOrder objects
        product_details_cache: Dictionary mapping product_id to product details

    Returns:
        Updated list of ProductionOrder objects with phases populated
    """
    print("\n[Step 4] Scheduling phases...")

    updated: List[ProductionOrder] = []
    for po in tqdm(production_orders, desc="Scheduling phases"):
        # 1. Generate phase sequence from BOM
        arke_client.schedule_production_order(po.production_order_id)

        # 2. Get phases with phase names
        prod_data = arke_client.get_production_order(po.production_order_id)

        try:
            phases_data = prod_data["phases"]
        except KeyError:
            print(
                f"⚠️ Warning: Production order {po.production_order_id} missing 'phases', skipping"
            )
            continue

        # Get product details for duration lookup
        try:
            product_details = product_details_cache[po.sales_order.product_id]
        except KeyError:
            print(f"⚠️ Warning: No cached details for product {po.sales_order.product_id}")
            product_details = {"process_lines": []}

        try:
            process_lines = product_details["process_lines"]
        except KeyError:
            print(f"⚠️ Warning: Product {po.sales_order.product_id} missing 'process_lines'")
            process_lines = []

        # Build phase name -> duration mapping
        phase_durations = extract_phase_durations(process_lines)

        # 3. Compute and set start/end for each phase (sequential)
        phase_cursor = po.starts_at
        phases: List[Phase] = []

        for phase_data in phases_data:
            try:
                phase_id = phase_data["id"]
            except KeyError:
                print(f"⚠️ Warning: Phase data missing 'id', skipping")
                continue

            # Parse actual phase name from nested structure
            try:
                phase_name = phase_data["phase"]["name"]
            except KeyError:
                print(f"⚠️ Warning: Phase {phase_id} missing nested name, using 'Unknown Phase'")
                phase_name = "Unknown Phase"

            # Look up duration from product's process_lines
            duration_per_unit = phase_durations.get(phase_name, 60)

            total_mins = duration_per_unit * po.sales_order.quantity
            phase_days = math.ceil(total_mins / MINS_PER_DAY)

            phase_start = phase_cursor
            phase_end = phase_cursor + timedelta(days=phase_days)
            phase_cursor = phase_end

            arke_client.update_phase_starting_date(phase_id, format_utc_datetime(phase_start))
            arke_client.update_phase_ending_date(phase_id, format_utc_datetime(phase_end))

            phases.append(
                Phase(
                    id=phase_id,
                    name=phase_name,
                    starts_at=phase_start,
                    ends_at=phase_end,
                )
            )

        updated.append(po.model_copy(update={"phases": phases}))

    print(f"[Step 4] Scheduled phases for {len(updated)} production orders")
    return updated


def get_human_approval(production_orders: List[ProductionOrder]) -> bool:
    """
    Present schedule to production planner and get approval.

    Args:
        production_orders: List of ProductionOrder objects

    Returns:
        True if approved, False otherwise
    """
    from telegram_bot import send_message_and_wait_for_approval

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

    # Send via Telegram
    print("\n[Telegram] Sending message to operator...")
    print("-" * 60)
    print(message)
    print("-" * 60)

    # Wait for operator response
    print("\n[Step 5] Waiting for operator approval...")

    approved = send_message_and_wait_for_approval(message)

    if approved:
        print("[Step 5] ✅ Schedule approved by operator")
    else:
        print("[Step 5] ❌ Schedule rejected by operator")

    return approved


def confirm_production_orders(
    arke_client: ArkeClient, production_orders: List[ProductionOrder]
) -> None:
    """
    Confirm production orders in Arke after human approval.

    Moves orders from scheduled to in_progress; first phase becomes ready_to_start.

    Args:
        arke_client: ArkeClient instance
        production_orders: List of ProductionOrder objects
    """
    print("\n[Arke] Starting production orders...")
    for po in tqdm(production_orders, desc="Starting orders"):
        arke_client.start_production_order(po.production_order_id)
        print(f"  ✅ {po.sales_order.internal_id} → in_progress")
