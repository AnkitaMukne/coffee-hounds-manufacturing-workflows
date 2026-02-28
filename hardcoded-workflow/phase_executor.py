"""
Phase execution logic for NovaBoard Electronics Production Scheduling Agent.

Handles the physical integration loop for production phases.
"""

from typing import List

import httpx
from arke_client import ArkeClient
from camera_verify import validate_phase_completion_visually
from telegram_bot import send_message

from models import ProductionOrder


class PhaseExecutor:
    """Executor for production phases with verification."""

    def __init__(self, arke_client: ArkeClient):
        """
        Initialize PhaseExecutor.

        Args:
            arke_client: ArkeClient instance
        """
        self.arke_client = arke_client

    def execute_phase(
        self, phase_id: str, phase_name: str, quantity: int, sales_order_internal_id: str
    ) -> bool:
        """
        Execute a single phase with verification.

        Args:
            phase_id: Phase ID
            phase_name: Phase name for display
            quantity: Production quantity
            sales_order_internal_id: Sales order internal ID for error reporting

        Returns:
            True if phase completed successfully, False otherwise
        """
        print(f"    • {phase_name} ({phase_id})")

        # Start the phase
        self.arke_client.start_phase(phase_id)
        print(f"      ✅ Phase started")

        # Physical monitoring - camera/VLM verification
        visually_valid = validate_phase_completion_visually()

        if not visually_valid:
            print(f"      ❌ Phase failed visual verification!")
            print("      Please investigate and resolve manually.")
            send_message(
                f"Phase '{phase_name}' for sales order {sales_order_internal_id} failed visual verification. Please investigate and resolve."
            )
            return False

        # Complete the phase
        try:
            # Fetch phase details to check if it's the final phase
            phase_data = self.arke_client.get_phase_details(phase_id)

            try:
                is_final = phase_data["is_final"]
            except KeyError:
                print(f"      ⚠️ Warning: Phase {phase_id} missing 'is_final', assuming False")
                is_final = False

            # Complete phase with quantity if final
            if is_final:
                self.arke_client.complete_phase(phase_id, completed_qty=quantity)
                print(f"      ℹ️  Final phase - including completed quantity: {quantity}")
            else:
                self.arke_client.complete_phase(phase_id)

            print(f"      ✅ Phase completed")
            return True

        except httpx.HTTPStatusError as e:
            print(f"      ❌ Error completing phase: {e}")
            print("      Please investigate and resolve manually.")
            send_message(
                f"Something went wrong with sales order {sales_order_internal_id} during phase '{phase_name}'. Error code {e.response.status_code}; message {e.response.text}. Please investigate."
            )
            return False

    def execute_production_order(self, po: ProductionOrder) -> bool:
        """
        Execute all phases for a production order.

        Args:
            po: ProductionOrder object

        Returns:
            True if all phases completed successfully, False otherwise
        """
        print(f"\n  {po.sales_order.internal_id} (PO: {po.production_order_id}):")
        for phase in po.phases:
            if not self.execute_phase(
                phase.id, phase.name, po.sales_order.quantity, po.sales_order.internal_id
            ):
                return False
        return True


def execute_all_orders(executor: PhaseExecutor, production_orders: List[ProductionOrder]) -> None:
    """
    Execute all production orders using PhaseExecutor.

    Args:
        executor: PhaseExecutor instance
        production_orders: List of ProductionOrder objects
    """
    print("\n[Step 6] Advancing production phases...")
    print("  Camera started...verifying phase completion...")

    for po in production_orders:
        executor.execute_production_order(po)

    send_message("\nAll phases have been advanced (started and completed) 🎉")
