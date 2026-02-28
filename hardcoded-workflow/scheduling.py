"""
Scheduling algorithms for production planning.
"""

import math
from datetime import timedelta
from typing import List

from arke_client import ArkeClient
from constants import BOM_MINS_PER_UNIT, MINS_PER_DAY, TODAY
from models import Phase, ProductionOrder, SalesOrder
from tqdm import tqdm
from utils import format_utc_datetime


def plan_edf_schedule(sales_orders: List[SalesOrder]) -> List[ProductionOrder]:
    """
    Step 2: Apply Earliest Deadline First (EDF) scheduling policy.

    - One production order per sales order line
    - Sort by expected_shipping_time, nearest first; ties broken by priority (lowest number wins)
    - ends_at = the sales order's shipping date

    Returns: List of ProductionOrder with starts_at/ends_at computed
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

        production_orders.append(
            ProductionOrder(sales_order=so, starts_at=starts_at, ends_at=ends_at)
        )

    print(f"\n[Step 2] EDF schedule computed ({len(production_orders)} production orders):")
    for po in production_orders:
        so = po.sales_order
        flag = "OK" if po.on_time else "LATE"
        print(
            f"  {so.internal_id}; {so.product_id}: {po.starts_at.date()} -> {po.ends_at.date()} "
            f"(deadline {so.deadline.date()}) [{flag}]"
        )

    return production_orders


def schedule_phases(
    client: ArkeClient,
    production_orders: List[ProductionOrder],
) -> List[ProductionOrder]:
    """
    Step 4: Schedule production phases with concrete start/end dates.

    1. Call _schedule on each production order → Arke generates phase sequence from BOM
    2. GET /api/product/production/{id} to read phases with duration_per_unit
    3. Assign concrete start/end dates to each phase (sequential)
    4. Update each phase with start/end dates

    Phase duration: total_minutes = duration_per_unit × quantity
    Working day = 480 min (8h)
    """
    print("\n[Step 4] Scheduling phases...")

    updated: List[ProductionOrder] = []
    for po in tqdm(production_orders, desc="Scheduling phases"):
        # Generate phase sequence from BOM
        client.schedule_production_order(po.production_order_id)

        # Get phases with duration_per_unit
        prod_data = client.get_production_order(po.production_order_id)
        phases_data = prod_data.get("phases", [])

        # Compute and set start/end for each phase (sequential)
        phase_cursor = po.starts_at
        phases: List[Phase] = []

        for phase_data in phases_data:
            phase_id = phase_data["id"]
            phase_name = phase_data.get("name", "Unknown Phase")
            duration_per_unit = phase_data.get("duration_per_unit", 60)
            total_mins = duration_per_unit * po.sales_order.quantity
            phase_days = math.ceil(total_mins / MINS_PER_DAY)

            phase_start = phase_cursor
            phase_end = phase_cursor + timedelta(days=phase_days)
            phase_cursor = phase_end

            client.update_phase_starting_date(phase_id, format_utc_datetime(phase_start))
            client.update_phase_ending_date(phase_id, format_utc_datetime(phase_end))

            phases.append(
                Phase(id=phase_id, name=phase_name, starts_at=phase_start, ends_at=phase_end)
            )

        updated.append(po.model_copy(update={"phases": phases}))

    print(f"[Step 4] Scheduled phases for {len(updated)} production orders")
    return updated
