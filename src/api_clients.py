"""
api_clients.py

Defines HTTP clients for external APIs: OrderCancellation and OrderTracking.
If ZENBOT_SIMULATE_API is true (default), returns dummy data so you can test
the solution locally.
"""
import os
import random
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Toggle simulation mode via env var (default: True)
SIMULATE = os.getenv("ZENBOT_SIMULATE_API", "true").lower() in ("1", "true", "yes")

def safe_http_call(func):
    """
    Decorator to wrap HTTP methods, catch RequestException,
    and return a uniform error dict.
    """
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except requests.RequestException as e:
            order_id = (kwargs.get("order_id")
                        or (args[1] if len(args) > 1 else None))
            logger.error("%s failed for order %s", func.__name__, order_id,
                         exc_info=e)
            return {
                "status": "error",
                "order_id": order_id,
                "message": str(e)
            }
    return wrapper

class OrderCancellationClient:
    BASE_URL = "https://api.example.com/OrderCancellation"

    @safe_http_call
    def cancel(self, order_id: str) -> Dict[str, Any]:
        if SIMULATE:
            logger.warning("Simulating cancellation for order %s", order_id)
            if random.random() < 0.9:
                return {"status": "ok", "order_id": order_id,
                        "message": "Simulated cancellation successful."}
            else:
                return {"status": "error", "order_id": order_id,
                        "message": "Simulated cancellation failure."}

        resp = requests.post(self.BASE_URL,
                             json={"order_id": order_id},
                             timeout=5)
        resp.raise_for_status()
        return resp.json()

class OrderTrackingClient:
    BASE_URL = "https://api.example.com/OrderTracking"

    @safe_http_call
    def track(self, order_id: str) -> Dict[str, Any]:
        if SIMULATE:
            logger.warning("Simulating tracking for order %s", order_id)
            status = random.choice(
                ["pending","shipped","in_transit","delivered","error"]
            )
            return {"status": status,
                    "order_id": order_id,
                    "message": f"Simulated tracking: {status}."}

        resp = requests.get(self.BASE_URL,
                            params={"order_id": order_id},
                            timeout=5)
        resp.raise_for_status()
        return resp.json()