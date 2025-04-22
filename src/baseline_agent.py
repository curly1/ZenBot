"""
baseline_agent.py

A simple rule-based chatbot for order cancellation and tracking.
"""
import sys
from datetime import datetime, timedelta
import json
from api_clients import OrderCancellationClient, OrderTrackingClient
from policies import can_cancel, can_return

# Static templates
TEMPLATES = {
    'cancel_success': "Your order {order_id} has been canceled successfully.",
    'cancel_fail': "Order {order_id} cannot be canceled due to policy.",
    'track': "The current status of order {order_id} is: {status}.",
    'error': "Sorry, an error occurred: {error}"
}

def baseline_handle(user_input: str, context: dict) -> str:
    """
    Simple intent routing by keyword matching.
    Expects context={'order_id':..., 'order_date':..., 'user_id':...}.
    """
    text = user_input.lower()
    order_id = context.get('order_id')
    order_date = context.get('order_date')
    user_id = context.get('user_id')

    try:
        if 'cancel' in text:
            if not can_cancel(order_date, user_id):
                return TEMPLATES['cancel_fail'].format(order_id=order_id)
            resp = OrderCancellationClient().cancel(order_id)
            if resp.get('error'):
                return TEMPLATES['error'].format(error=resp['message'])
            return TEMPLATES['cancel_success'].format(order_id=order_id)

        if 'track' in text or 'status' in text:
            resp = OrderTrackingClient().track(order_id)
            if resp.get('error'):
                return TEMPLATES['error'].format(error=resp['message'])
            return TEMPLATES['track'].format(order_id=order_id, status=resp.get('status'))

    except Exception as e:
        return TEMPLATES['error'].format(error=str(e))

if __name__ == '__main__':
    # Example order info; in a real CLI, you would parse args
    order_info = {
        "order_id": "123",
        "order_date": "2025-04-20",
        "user_id": "user_1"
    }
    print("Baseline Rule-Based Chatbot")
    print("I can help you cancel or track orders. Please specify which.")
    msg = input("You: ")
    if msg.lower() in ('quit','exit'):
        sys.exit(0)
    print("Bot:", baseline_handle(msg, order_info))
