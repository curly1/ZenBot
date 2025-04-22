"""
baseline.py

A simple rule-based chatbot for order cancellation and tracking.
"""

import logging
import sys
import os
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

def handle_message(user_input: str, order_info: dict) -> bool:
    """
    Simple intent routing by keyword matching.

    Args:
        user_input (str): The user's input message.
        order_info (dict): The order information containing order_id, order_date, and user_id.
    
    Returns:
        bool: True if the message was handled successfully, False otherwise.
    
    """

    logger.info("Baseline agent started")

    banner = (
        "====================================================================\n"
        "🕹 Baseline Rule-Based Chatbot                                      \n"
        "====================================================================\n\n"
        "🎯 I can track or cancel your order.\n"
    )
    print(banner)

    print("====================================================================")
    print("💬 Using input data:")
    print("====================================================================\n")
    print(f"Prompt: {user_input}")
    print(f"Order info: {json.dumps(order_info, indent=2)}")

    # Log input details
    logger.info("User input: %s", user_input)
    logger.info("Order info: %s", order_info)

    text = user_input.lower()
    order_id = order_info.get('order_id')
    order_date = order_info.get('order_date')
    user_id = order_info.get('user_id')

    try:
        if 'track' in text or 'status' in text:
            tool_name = "track_order"
            resp = OrderTrackingClient().track(order_id)
            api_status = resp.get("status", "error")
            if api_status == "error":
                logger.error("API error: %s", resp.get("message"))
                print(TEMPLATES['error'].format(error=resp['message']))
                return False
            final_response = TEMPLATES['track'].format(order_id=order_id, status=resp.get('status'))
        elif 'cancel' in text:
            tool_name = "cancel_order"
            if not can_cancel(order_date, user_id):
                policy_passed = "False"
                return TEMPLATES['cancel_fail'].format(order_id=order_id)
            policy_passed = "True"
            logger.info("Policy passed: %s", policy_passed)
            resp = OrderCancellationClient().cancel(order_id)
            api_status = resp.get("status", "error")
            if api_status == "error":
                print(TEMPLATES['error'].format(error=resp['message']))
                return False
            final_response = TEMPLATES['cancel_success'].format(order_id=order_id)
        else:
            print("\nNo tool calls were triggered by the model.")
            tool_name = "none"
            logger.info("Tool used: %s", tool_name)
            return False
        logger.info("Tool used: %s", tool_name)
        logger.info("API status: %s", api_status)
        logger.info("Final response: %s", final_response)

        print("\n====================================================================")
        print("🤖 Model's response:")
        print("====================================================================")
        print(final_response)

        return True
    
    except Exception as e:
        return TEMPLATES['error'].format(error=str(e))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 src/baseline.py '<user_input>' '<order_info_json>' '<log_path>'")
        sys.exit(1)

    user_input = sys.argv[1]
    order_info = json.loads(sys.argv[2])
    log_path = sys.argv[3]

    # Configure the logger
    log_dir  = os.path.dirname(log_path)

    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    if not os.path.exists(log_path):
        open(log_path, "a").close()

    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        filemode='w',
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    )
    logger = logging.getLogger(__name__)

    # Run baseline agent
    if handle_message(user_input, order_info):
        logger.info("Baseline agent finished successfully")
    else:
        logger.info("Baseline agent didn't finish successfully")

    print("\n====================================================================")
    print("📃 More information in the log file:")
    print("====================================================================")
    print(log_path)