"""
baseline.py

A simple rule-based chatbot for order cancellation and tracking.
"""

import sys
import os
import json
import logging
import time
from dataclasses import dataclass
from api_clients import OrderCancellationClient, OrderTrackingClient
from policies import can_cancel
from utils import pretty_section, configure_logger, validate_inputs

# Static templates
TEMPLATES = {
    'cancel_success': "Your order {order_id} has been canceled successfully.",
    'cancel_fail': "Order {order_id} cannot be canceled due to policy.",
    'track': "The current status of order {order_id} is: {status}.",
    'error': "Sorry, an error occurred: {error}"
}

@dataclass
class AgentResult:
    tool_name: str
    policy_passed: bool
    api_status: str
    tool_output: dict
    final_response: str
    response_time: float

def route_message(user_input: str, order_info: dict) -> AgentResult:
    """
    Routes the user input to the appropriate tool based on the message content.
    Args:
        user_input (str): The user's input message.
        order_info (dict): Information about the order, including order_id, order_date, and user_id.
    Returns:
        AgentResult: The result of the tool call, including tool name, policy status, API status, and final response.
    """

    logger = logging.getLogger(__name__)
    logger.info("Baseline agent started")
    start = time.time()

    logger.info("User input: %s", user_input)
    logger.info("Order info: %s", order_info)

    text = user_input.lower()
    order_id = order_info["order_id"]
    order_date = order_info["order_date"]
    user_id = order_info["user_id"]

    if "track" in text or "status" in text:
        pretty_section("📲 Model requested tool call", "Tool name: track_order")
        resp = OrderTrackingClient().track(order_id)
        status = resp.get("status", "error")
        final = (
            TEMPLATES["track"].format(order_id=order_id, status=status)
            if status != "error"
            else TEMPLATES["error"].format(error=resp.get("message", "Unknown"))
        )
        return AgentResult("track_order", True, status, resp, final, time.time() - start)

    if "cancel" in text:
        pretty_section("📲 Model requested tool call", "Tool name: cancel_order")
        if not can_cancel(order_date, user_id):
            return AgentResult(
                tool_name="cancel_order",
                policy_passed=False,
                api_status=None,
                tool_output=None,
                final_response=TEMPLATES["cancel_fail"].format(order_id=order_id),
                response_time=time.time() - start
            )
        resp = OrderCancellationClient().cancel(order_id)
        status = resp.get("status", "error")
        final = (
            TEMPLATES["cancel_success"].format(order_id=order_id)
            if status == "ok"
            else TEMPLATES["error"].format(error=resp.get("message", "Unknown"))
        )
        return AgentResult("cancel_order", True, status, resp, final, time.time() - start)

    # nothing matched
    return AgentResult("none", False, None, None, "Sorry, I didn't understand that.", time.time() - start)

if __name__ == "__main__":
    
    # Check if the script is run with the correct number of arguments
    if len(sys.argv) != 4:
        print("Usage: python3 src/baseline.py '<user_input>' '<order_info_json>' '<log_path>'")
        sys.exit(1)

    # Read command line arguments
    user_input = sys.argv[1]
    order_info = json.loads(sys.argv[2])
    log_path   = sys.argv[3]

    # Configure logger
    logger = logging.getLogger(__name__)
    configure_logger(log_path, level=logging.INFO)

    # Validate inputs
    if not validate_inputs(user_input, order_info):
        print("Invalid input data. Please check your inputs.")
        sys.exit(1)

    # Print the banner
    banner = (
        "======================================================================\n"
        "🕹 Baseline Rule-Based Chatbot                                        \n"
        "======================================================================\n"
        "🎯 I can track or cancel your order."
    )
    print(banner)

    # Input details
    pretty_section("💬 Using input data:", 
                   f"Prompt: {user_input}\nOrder info: {json.dumps(order_info, indent=2)}")

    # Run baseline agent
    result = route_message(user_input, order_info)

    # Print some info for the user
    pretty_section("🔧 Tool output", json.dumps(result.tool_output, indent=2))
    pretty_section("🤖 Final response", result.final_response)
    pretty_section("📜 Log file", f"Log path: {log_path}")

    # Log the results
    logger.info("Tool requested: %s", result.tool_name)
    logger.info("Policy passed: %s", result.policy_passed)
    logger.info("API status: %s", result.api_status)
    logger.info("Tool output: %s", result.tool_output)
    logger.info("Final response: %s", result.final_response)
    logger.info("ZenBaseline agent finished, response time: %s", f"{result.response_time:.2f} seconds.")
