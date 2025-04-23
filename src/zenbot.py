"""
zenbot.py

A simple chatbot for order cancellation and tracking using a locally running LLM server,
with sentiment-awareness.
"""

import sys
import os
import json
import logging
import time
from dataclasses import dataclass
import requests
from sentiment import is_frustrated
from policies import can_cancel
from utils import pretty_section, configure_logger, validate_inputs
from api_clients import OrderCancellationClient, OrderTrackingClient


# Endpoint details for locally running LLM server (llama.cpp)
url = "http://localhost:8080/v1/chat/completions"

# Headers with authorization if needed
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer token"
}

# System prompt for the model
SYSTEM_PROMPT = f"""
You are ZenBot, a helpful order support assistant.

You have access to tools to help the user:
- Use the `track_order` tool if the user wants to check or track their order.
- Use the `cancel_order` tool if the user wants to cancel their order.

Call the appropriate tool **only** if the user's intent is clear.

Examples:
- "Where is my package?" - call `track_order`
- "Cancel my order" - call `cancel_order`
- "Can you help me?" - do not call any tool

Only respond with a tool call if the user's message contains or implies the need to **track** or **cancel** an order.
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel an order if it meets policy requirements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The ID of the order to cancel"
                    },
                    "order_date": {
                        "type": "string",
                        "description": "The date the order was placed (format: YYYY-MM-DD)"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "The ID of the user who placed the order"
                    }
                },
                "required": ["order_id", "order_date", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "track_order",
            "description": "Retrieve the current status of an order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The ID of the order to track"
                    }
                },
                "required": ["order_id"]
            }
        }
    }
]

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
    Routes the user message to the appropriate tool based on the user's intent.
    Args:
        user_input (str): The user's message.
        order_info (dict): The order information.
    Returns:
        AgentResult: The result of the tool call, including tool name, policy status, API status, and final response.
    """
    
    logger = logging.getLogger(__name__)
    logger.info("ZenBot started")
    start = time.time()

    logger.info("User input: %s", user_input)
    logger.info("Order info: %s", order_info)

    # Check sentiment before doing anything else
    if is_frustrated(user_input, threshold=10.0):
        # TODO - Improve the sentiment analysis model.
        # The threshold is currently set to 10 because lower values incorrectly 
        # flag all cancellation requests as negative. The 'is_frustrated' flag 
        # remains as a placeholder for future use.
        escalation = "I'm sorry, you seem frustrated. I'm transferring you to a live agent now."
        pretty_section("⚠️ Escalation", escalation)
        return AgentResult("escalate", False, None, None, escalation, time.time() - start)

    messages = [
        {
            "role": "system", 
            "content": SYSTEM_PROMPT
        },
        # === FEW-SHOT 1: Track order ===
        {
            "role": "user",
            "content": f"Where is my package? My order info is: {order_info}"
        },
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tool_1",
                    "type": "function",
                    "function": {
                        "name": "track_order",
                        "arguments": '{ "order_id": "123" }'
                    }
                }
            ]
        },
        # === FEW-SHOT 2: Cancel order ===
        {
            "role": "user",
            "content": f"I need to cancel my order. My order info is: {order_info}"
        },
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tool_2",
                    "type": "function",
                    "function": {
                        "name": "cancel_order",
                        "arguments": '{ "order_id": "123", "order_date": "2025-04-05", "user_id": "user_1" }'
                    }
                }
            ]
        },
        # REAL USER INPUT
        {
            "role": "user", 
            "content": f"{user_input}. My order info is: {order_info}"
        }
    ]

    data = {
        "messages": messages,
        "tools": tools,
        "temperature": 0.15
    }

    # Send initial request to model
    try:
        resp = requests.post(url, headers=headers, json=data)
        resp.raise_for_status()
    except Exception as e:
        logger.error("LLM unreachable: %s", e)
        err = "Sorry, I’m having trouble reaching the language LLM server right now. Please try again later."
        return AgentResult("llm_error", False, None, None, err, time.time() - start)    

    reply = resp.json()["choices"][0]["message"]
    calls = reply.get("tool_calls", [])

    # Handle tool call
    if not calls:
        return AgentResult("none", False, None, None, "No tool call triggered by the model.", time.time() - start)
    
    call = calls[0]
    tool_name = call["function"]["name"]
    args = json.loads(call["function"]["arguments"])

    # Execute tool logic
    policy_passed = True
    api_status = None
    tool_output = None
    result_msg = ""

     # Perform the actual function call
    if tool_name == "track_order":
        tool_output = OrderTrackingClient().track(args["order_id"])
        api_status = tool_output.get("status", "error")
        result_msg = (
            TEMPLATES["track"].format(order_id=args["order_id"], status=api_status)
            if api_status != "error"
            else TEMPLATES["error"].format(error=tool_output.get("message", "Unknown"))
        )
    elif tool_name == "cancel_order":
        if not can_cancel(args["order_date"], args["user_id"]):
            policy_passed = False
            result_msg = TEMPLATES["cancel_fail"].format(order_id=args["order_id"])
        else:
            tool_output = OrderCancellationClient().cancel(args["order_id"])
            api_status = tool_output.get("status", "error")
            result_msg = (
                TEMPLATES["cancel_success"].format(order_id=args["order_id"])
                if api_status == "ok"
                else TEMPLATES["error"].format(error=tool_output.get("message", "Unknown"))
            )
    else:
        return AgentResult(tool_name, False, None, None, f"Unknown tool: {tool_name}", time.time() - start)

    # Send the tool message back to the model
    messages.append({
        "role": "assistant",
        "content": f"{tool_name} tool response: {result_msg}"
    })

    # Add the instructions for the model to generate a natural language response
    messages.append({
        "role": "user",
        "content": "Use the information returned by the tool and translate it into a natural language response. \
                    Don't repeat the tool name or any technical details. \
                    Don't include any code or JSON. \
                    Don't mention the function call or the tool. \
                    Don't mention the order ID or any other sensitive information. \
                    Don't use any technical jargon. \
                    Don't use any abbreviations. \
                    Don't use any slang. \
                    Make your reply coherent and polite."
    })

    # New request with updated conversation
    followup_data = {
        "messages": messages,
        "temperature": 0.5
    }

    try:
        resp_followup = requests.post(url, headers=headers, data=json.dumps(followup_data))
        resp_followup.raise_for_status()
        final_response = resp_followup.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error("Follow-up request failed: %s", e)
        final_response = f"Error generating final response: {e}"

    return AgentResult(tool_name, policy_passed, api_status, tool_output, final_response, time.time() - start)

# TODO - create a shared driver for both baseline and zenbot
def run_agent(user_input: str, order_info: dict, log_path: str) -> AgentResult:
    """
    Run the baseline agent with the provided user input and order information.
    Args:
        user_input (str): The user's input message.
        order_info (dict): Information about the order, including order_id, order_date, and user_id.
        log_path (str): Path to the log file.
    Returns:
        AgentResult: The result of the agent's processing.
    """
    # Configure logger
    logger = logging.getLogger(__name__)
    configure_logger(log_path, level=logging.INFO)

    # Validate inputs
    if not validate_inputs(user_input, order_info):
        raise ValueError("Invalid input data. Please check your inputs.")

    # Run baseline agent
    result = route_message(user_input, order_info)

    # Log the results
    logger.info("Tool requested: %s", result.tool_name)
    logger.info("Policy passed: %s", result.policy_passed)
    logger.info("API status: %s", result.api_status)
    logger.info("Tool output: %s", result.tool_output)
    logger.info("Final response: %s", result.final_response)
    logger.info("Response time: %s", f"{result.response_time:.2f} seconds.")

    return result

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 src/zenbot.py '<user_input>' '<order_info_json>' '<log_path>'")
        sys.exit(1)

    user_input = sys.argv[1]
    order_info = json.loads(sys.argv[2])
    log_path = sys.argv[3]

    banner = (
        "======================================================================\n"
        "⚡ ZenBot is live!                                                     \n"
        "======================================================================\n"
        "👋 Hey there! I’m ZenBot. Not a human, but here to help!\n"
        "🧘 I don’t get angry, just keep it bot-positive.\n"
        "🎯 I can track or cancel your order."
    )
    print(banner)

    # Print input details
    pretty_section(
        "💬 Using input data:",
        f"Prompt: {user_input}\nOrder info: {json.dumps(order_info, indent=2)}"
    )

    result = run_agent(user_input, order_info, log_path)

    # Print some more info for the user
    pretty_section("📲 Tool name", result.tool_name)
    pretty_section("🔧 Tool output", json.dumps(result.tool_output, indent=2))
    pretty_section("🤖 Final response", result.final_response, wrap=True)
    pretty_section("📜 Log file", f"Log path: {log_path}")