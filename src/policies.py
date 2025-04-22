"""
policies.py

Defines business rules for order cancellation, refunds, and tracking.
Extendable to add new policies (e.g. loyalty overrides, blackout periods).
"""
from datetime import datetime, timedelta

# Core policy parameters
CANCELLATION_WINDOW_DAYS = 10
MAX_CANCELLATIONS_PER_USER_PER_MONTH = 3
RETURN_WINDOW_DAYS = 30
BLACKOUT_DATES = ["2025-12-25", "2025-01-01"]

# Simulated user cancellation history: in real usage, query a database
user_cancellation_count = {
    # 'user_id': count
}

def is_within_window(order_date_str: str, window_days: int) -> bool:
    """Checks if order_date is within the given window in days."""
    order_date = datetime.strptime(order_date_str, "%Y-%m-%d")
    return (datetime.utcnow() - order_date) < timedelta(days=window_days)

def can_cancel(order_date_str: str, user_id: str = None) -> bool:
    """
    Determines if an order can be cancelled based on multiple policies:
    - Order placed less than CANCELLATION_WINDOW_DAYS ago
    - User has not exceeded monthly cancellation quota
    - Not during blackout dates
    """
    # Window policy
    if not is_within_window(order_date_str, CANCELLATION_WINDOW_DAYS):
        print("Order is outside the cancellation window.")
        return False
    # Monthly quota
    if user_id:
        count = user_cancellation_count.get(user_id, 0)
        if count >= MAX_CANCELLATIONS_PER_USER_PER_MONTH:
            print("User has exceeded monthly cancellation quota.")
            return False
    # Blackout dates
    if order_date_str in BLACKOUT_DATES:
        print("Order date is in a blackout period.")
        return False
    return True

def can_return(order_date_str: str) -> bool:
    """Checks if an order is within the return window."""
    return is_within_window(order_date_str, RETURN_WINDOW_DAYS)
