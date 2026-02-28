"""
API client wrapper for the Arke production management system.
"""

from typing import Dict, Optional

import httpx
from constants import BASE_URL


class ArkeClient:
    """Thin wrapper around the Arke HTTP API."""

    def __init__(self, client: httpx.Client, base_url: str = BASE_URL):
        self.client = client
        self.base_url = base_url

    # -------------------------------------------------------------------------
    # Products
    # -------------------------------------------------------------------------

    def get_products(self) -> list:
        """GET /api/product/product"""
        resp = self.client.get(f"{self.base_url}/api/product/product")
        resp.raise_for_status()
        return resp.json()

    # -------------------------------------------------------------------------
    # Sales orders
    # -------------------------------------------------------------------------

    def get_sales_orders(self, status: str = "accepted", limit: int = 1000) -> list:
        """GET /api/sales/order"""
        resp = self.client.get(
            f"{self.base_url}/api/sales/order", params={"status": status, "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    def get_sales_order(self, so_id: str) -> Dict:
        """GET /api/sales/order/{id}"""
        resp = self.client.get(f"{self.base_url}/api/sales/order/{so_id}")
        resp.raise_for_status()
        return resp.json()

    # -------------------------------------------------------------------------
    # Production orders
    # -------------------------------------------------------------------------

    def create_production_order(self, body: Dict) -> Dict:
        """PUT /api/product/production"""
        resp = self.client.put(f"{self.base_url}/api/product/production", json=body)
        resp.raise_for_status()
        return resp.json()

    def get_production_order(self, po_id: str) -> Dict:
        """GET /api/product/production/{id}"""
        resp = self.client.get(f"{self.base_url}/api/product/production/{po_id}")
        resp.raise_for_status()
        return resp.json()

    def schedule_production_order(self, po_id: str) -> None:
        """POST /api/product/production/{id}/_schedule"""
        resp = self.client.post(f"{self.base_url}/api/product/production/{po_id}/_schedule")
        resp.raise_for_status()

    def start_production_order(self, po_id: str) -> None:
        """POST /api/product/production/{id}/_start"""
        resp = self.client.post(f"{self.base_url}/api/product/production/{po_id}/_start")
        resp.raise_for_status()

    # -------------------------------------------------------------------------
    # Production order phases
    # -------------------------------------------------------------------------

    def get_phase(self, phase_id: str) -> Dict:
        """GET /api/product/production-order-phase/{id}"""
        resp = self.client.get(f"{self.base_url}/api/product/production-order-phase/{phase_id}")
        resp.raise_for_status()
        return resp.json()

    def start_phase(self, phase_id: str) -> None:
        """POST /api/product/production-order-phase/{id}/_start"""
        resp = self.client.post(
            f"{self.base_url}/api/product/production-order-phase/{phase_id}/_start"
        )
        resp.raise_for_status()

    def complete_phase(self, phase_id: str, completed_qty: Optional[int] = None) -> None:
        """POST /api/product/production-order-phase/{id}/_complete"""
        body: Dict = {"raw_material_inventory": [], "skip_consumption": False}
        if completed_qty is not None:
            body["completed"] = completed_qty
        resp = self.client.post(
            f"{self.base_url}/api/product/production-order-phase/{phase_id}/_complete",
            json=body,
        )
        resp.raise_for_status()

    def update_phase_starting_date(self, phase_id: str, starting_date: str) -> None:
        """POST /api/product/production-order-phase/{id}/_update_starting_date"""
        resp = self.client.post(
            f"{self.base_url}/api/product/production-order-phase/{phase_id}/_update_starting_date",
            json={"starting_date": starting_date},
        )
        resp.raise_for_status()

    def update_phase_ending_date(self, phase_id: str, ending_date: str) -> None:
        """POST /api/product/production-order-phase/{id}/_update_ending_date"""
        resp = self.client.post(
            f"{self.base_url}/api/product/production-order-phase/{phase_id}/_update_ending_date",
            json={"ending_date": ending_date},
        )
        resp.raise_for_status()
