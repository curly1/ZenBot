"""
api_clients.py

Defines HTTP clients for external APIs: OrderCancellation and OrderTracking.
If ZENBOT_SIMULATE_API is true (default), returns dummy data so you can test
the solution locally.
"""
import os
import random
from typing import Dict, Any

# Toggle simulation mode via env var (default: True)
SIMULATE = os.getenv("ZENBOT_SIMULATE_API", "true").lower() in ("1", "true", "yes")

# TODO - add timeout simulation

class OrderCancellationClient:
    """Client for the OrderCancellation API endpoint (simulated or real)."""
    BASE_URL = "https://api.example.com/OrderCancellation"

    def cancel(self, order_id: str) -> Dict[str, Any]:
        """
        Cancels the given order_id.
        In simulate mode, returns a dummy OK or error at random.
        """
        if SIMULATE:
            # fake a success most of the time
            if random.random() < 0.9:
                return {
                    "status": "ok",
                    "order_id": order_id,
                    "message": "Simulated cancellation successful."
                }
            else:
                return {
                    "status": "error",
                    "order_id": order_id,
                    "message": "Simulated cancellation failure."
                }

        # Real HTTP path
        import requests
        try:
            resp = requests.post(self.BASE_URL, json={"order_id": order_id}, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"status": "error", "order_id": order_id, "message": str(e)}

class OrderTrackingClient:
    """Client for the OrderTracking API endpoint (simulated or real)."""
    BASE_URL = "https://api.example.com/OrderTracking"

    def track(self, order_id: str) -> Dict[str, Any]:
        """
        Retrieves tracking info for order_id.
        In simulate mode, returns a dummy status.
        """
        if SIMULATE:
            status = random.choice(["pending", "shipped", "in_transit", "delivered", "error"])
            return {
                "status": status,
                "order_id": order_id,
                "message": f"Simulated tracking: {status}."
            }

        # Real HTTP path
        import requests
        try:
            resp = requests.get(self.BASE_URL, params={"order_id": order_id}, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"status": "error", "order_id": order_id, "message": str(e)}