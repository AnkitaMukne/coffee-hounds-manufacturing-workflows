"""
Phase execution logic: start and complete production order phases with visual verification.
"""

from typing import List

import httpx
from arke_client import ArkeClient
from camera_verify import validate_phase_completion_visually
from models import Phase, ProductionOrder
from telegram_bot import send_message


class PhaseExecutor:
    """Drives the physical production loop: starts and completes phases with camera verification."""

    def __init__(self, client: ArkeClient):
        self.client = client

    def execute_phase(self, phase: Phase, po: ProductionOrder) -> bool:
        """
        Execute a single phase with visual verification.

        Phase lifecycle: not_ready → ready → _start → started → _complete → completed

        Returns True if the phase completed successfully, False otherwise.
        """
        print(f"    • {phase.name} ({phase.id})")

        # Start the phase
        self.client.start_phase(phase.id)
        print(f"      ✅ Phase started")

        # Camera/VLM verification
        visually_valid = validate_phase_completion_visually()
        if not visually_valid:
            print(f"      ❌ Phase failed visual verification!")
            print("      Please investigate and resolve manually.")
            send_message(
                f"Phase '{phase.name}' for sales order {po.sales_order.internal_id} "
                f"failed visual verification. Please investigate and resolve."
            )
            return False

        # Complete the phase
        try:
            phase_data = self.client.get_phase(phase.id)
            is_final = phase_data.get("is_final", False)

            completed_qty = po.sales_order.quantity if is_final else None
            if is_final:
                print(
                    f"      ℹ️  Final phase - including completed quantity: {po.sales_order.quantity}"
                )

            self.client.complete_phase(phase.id, completed_qty)
            print(f"      ✅ Phase completed")
        except httpx.HTTPStatusError as e:
            print(f"      ❌ Error completing phase: {e}")
            print("      Please investigate and resolve manually.")
            send_message(
                f"Something went wrong with sales order {po.sales_order.internal_id} "
                f"during phase '{phase.name}'. Error code {e.response.status_code}; "
                f"message {e.response.text}. Please investigate."
            )
            return False

        return True

    def execute_production_order(self, po: ProductionOrder) -> bool:
        """
        Execute all phases for a production order sequentially.

        Returns True if all phases completed successfully, False if any phase failed.
        """
        print(f"\n  {po.sales_order.internal_id} (PO: {po.production_order_id}):")
        for phase in po.phases:
            if not self.execute_phase(phase, po):
                return False
        return True


def execute_all_orders(executor: PhaseExecutor, production_orders: List[ProductionOrder]) -> None:
    """Execute all production orders using the given PhaseExecutor."""
    print("\n[Step 6] Advancing production phases...")
    print("  Camera started...verifying phase completion...")

    for po in production_orders:
        executor.execute_production_order(po)

    send_message("\nAll phases have been advanced (started and completed) 🎉")
