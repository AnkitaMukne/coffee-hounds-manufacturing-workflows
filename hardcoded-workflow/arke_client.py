"""
API client wrapper for Arke system.

Provides a clean interface for all Arke API calls.
"""

from typing import Dict, List, Optional

import httpx

from constants import BASE_URL


class ArkeClient:
    """Client wrapper for Arke API calls."""

    def __init__(self, client: httpx.Client, base_url: str = BASE_URL):
        """
        Initialize ArkeClient.

        Args:
            client: httpx.Client instance (must have Authorization header set)
            base_url: Base URL for API (defaults to BASE_URL from constants)
        """
        self.client = client
        self.base_url = base_url

    def get_products(self) -> List[Dict]:
        """
        Get all products.

        Returns:
            List of product dictionaries
        """
        resp = self.client.get(f"{self.base_url}/api/product/product")
        resp.raise_for_status()
        return resp.json()

    def get_product_details(self, product_id: str) -> Dict:
        """
        Get detailed product information including process_lines.

        Args:
            product_id: Product ID

        Returns:
            Product details dictionary
        """
        resp = self.client.get(f"{self.base_url}/api/product/product/{product_id}")
        resp.raise_for_status()
        return resp.json()

    def get_sales_orders(self, status: str = "accepted", limit: int = 1000) -> List[Dict]:
        """
        Get sales orders by status.

        Args:
            status: Order status filter (default: "accepted")
            limit: Maximum number of orders to return

        Returns:
            List of sales order summaries
        """
        resp = self.client.get(
            f"{self.base_url}/api/sales/order", params={"status": status, "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    def get_sales_order_details(self, order_id: str) -> Dict:
        """
        Get detailed sales order information.

        Args:
            order_id: Sales order ID

        Returns:
            Sales order details dictionary
        """
        resp = self.client.get(f"{self.base_url}/api/sales/order/{order_id}")
        resp.raise_for_status()
        return resp.json()

    def create_production_order(
        self, product_id: str, quantity: int, starts_at: str, ends_at: str
    ) -> Dict:
        """
        Create a new production order.

        Args:
            product_id: Product ID to produce
            quantity: Quantity to produce
            starts_at: Start datetime in ISO format
            ends_at: End datetime in ISO format

        Returns:
            Created production order data
        """
        body = {
            "product_id": product_id,
            "quantity": quantity,
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        resp = self.client.put(f"{self.base_url}/api/product/production", json=body)
        resp.raise_for_status()
        return resp.json()

    def schedule_production_order(self, production_order_id: str) -> None:
        """
        Schedule a production order (generates phase sequence from BOM).

        Args:
            production_order_id: Production order ID
        """
        resp = self.client.post(
            f"{self.base_url}/api/product/production/{production_order_id}/_schedule"
        )
        resp.raise_for_status()

    def get_production_order(self, production_order_id: str) -> Dict:
        """
        Get production order details including phases.

        Args:
            production_order_id: Production order ID

        Returns:
            Production order data with phases
        """
        resp = self.client.get(f"{self.base_url}/api/product/production/{production_order_id}")
        resp.raise_for_status()
        return resp.json()

    def update_phase_starting_date(self, phase_id: str, starting_date: str) -> None:
        """
        Update phase starting date.

        Args:
            phase_id: Phase ID
            starting_date: Start datetime in ISO format
        """
        resp = self.client.post(
            f"{self.base_url}/api/product/production-order-phase/{phase_id}/_update_starting_date",
            json={"starting_date": starting_date},
        )
        resp.raise_for_status()

    def update_phase_ending_date(self, phase_id: str, ending_date: str) -> None:
        """
        Update phase ending date.

        Args:
            phase_id: Phase ID
            ending_date: End datetime in ISO format
        """
        resp = self.client.post(
            f"{self.base_url}/api/product/production-order-phase/{phase_id}/_update_ending_date",
            json={"ending_date": ending_date},
        )
        resp.raise_for_status()

    def start_production_order(self, production_order_id: str) -> None:
        """
        Start a production order (moves to in_progress state).

        Args:
            production_order_id: Production order ID
        """
        resp = self.client.post(
            f"{self.base_url}/api/product/production/{production_order_id}/_start"
        )
        resp.raise_for_status()

    def start_phase(self, phase_id: str) -> None:
        """
        Start a production phase.

        Args:
            phase_id: Phase ID
        """
        resp = self.client.post(
            f"{self.base_url}/api/product/production-order-phase/{phase_id}/_start"
        )
        resp.raise_for_status()

    def get_phase_details(self, phase_id: str) -> Dict:
        """
        Get phase details.

        Args:
            phase_id: Phase ID

        Returns:
            Phase details dictionary
        """
        resp = self.client.get(f"{self.base_url}/api/product/production-order-phase/{phase_id}")
        resp.raise_for_status()
        return resp.json()

    def complete_phase(self, phase_id: str, completed_qty: Optional[int] = None) -> None:
        """
        Complete a production phase.

        Args:
            phase_id: Phase ID
            completed_qty: Optional completed quantity (required for final phase)
        """
        body = {"raw_material_inventory": [], "skip_consumption": False}
        if completed_qty is not None:
            body["completed"] = completed_qty
        resp = self.client.post(
            f"{self.base_url}/api/product/production-order-phase/{phase_id}/_complete",
            json=body,
        )
        resp.raise_for_status()
