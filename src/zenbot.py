"""
zenbot.py

A simple chatbot for order cancellation and tracking using a locally running LLM server,
with sentiment-awareness.
"""

import logging
import sys
import os
import json
import requests
from sentiment import is_frustrated
from policies import can_cancel
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

def handle_message(user_input: str, order_info: dict, model_path: str) -> bool:
    """
    Processes the user's message, decides which tool to use (track or cancel),
    enforces policy for cancellations, calls the appropriate API client,
    and then uses the specified LLM endpoint to craft a final reply.

    Args:
        user_input (str): The user's input message.
        order_info (dict): The order information containing order_id, order_date, and user_id.
        model_path (str): Path to the model to be used for generating responses.
    
    Returns:
        bool: True if the message was fully handled successfully, False otherwise.

    """

    logger.info("ZenBot started")

    banner = (
        "====================================================================\n"
        "⚡ ZenBot is live!                                                   \n"
        "====================================================================\n\n"
        "👋 Hey there! I’m ZenBot. Not a human, but here to help!\n"
        "🧘 I don’t get angry, just keep it bot-positive.\n"
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
    logger.info("Model path: %s", model_path)

    # Check sentiment before doing anything else
    # TODO - improve sentiment analysis model
    # the threshold is set to 10 here because all cancellation requests
    # are flagged as negative with lower values... 
    # is_frustrated is left here as a placeholder
    
    if is_frustrated(user_input, threshold=10.0):
        # TODO - call a real escalation API
        escalation_msg = (
          "I'm sorry, you seem frustrated. "
          "I'm transferring you to a live agent now."
        )
        print(f"{escalation_msg}")
        return False

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
        "model": model_path,
        "messages": messages,
        "tools": tools,
        "temperature": 0.15
    }

    # Send initial request to model, expecting it to call the function
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
    except requests.exceptions.RequestException as e:
        logger.error("LLM endpoint unreachable: %s", e)
        logger.debug("Full exception details:", exc_info=True)
        print("Sorry, I’m having trouble reaching the language LLM server right now. "
              "Please try again in a moment.")
        return False

    reply = response.json()["choices"][0]["message"]

    tool_calls = reply.get("tool_calls", [])
    if tool_calls:
        tool_call = tool_calls[0]
        tool_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])

        print("\n====================================================================")
        print("📲 Model requested function call:")
        print("====================================================================")
        print(json.dumps(tool_call, indent=2))

        # Perform the actual function call
        if tool_name == "track_order":
            try:
                order_id = arguments["order_id"]
                resp = OrderTrackingClient().track(order_id)
                result = f"Order status: {resp}"
                api_status = resp.get("status", "error")
            except Exception as e:
                result = f"Error retrieving status: {str(e)}"
                api_status = "error"
        elif tool_name == "cancel_order":
            try:
                order_id = arguments["order_id"]
                order_date = arguments["order_date"]
                user_id = arguments["user_id"]
                if not can_cancel(order_date, user_id):
                    policy_passed = "False"
                    result = f"Order {order_id} cannot be canceled per policy."
                else:
                    policy_passed = "True"
                    resp = OrderCancellationClient().cancel(order_id)
                    result = f"Cancellation result: {resp}"
                    api_status = resp.get("status", "error")
                logger.info("Policy passed: %s", policy_passed)
            except Exception as e:
                result = f"Error processing cancellation: {str(e)}"
        else:
            print(f"Unknown function called: {tool_name}")
            return False
        logger.info("Tool used: %s", tool_name)
        logger.info("API status: %s", api_status)

    else:
        print("\nNo tool calls were triggered by the model.")
        tool_name = "none"
        logger.info("Tool used: %s", tool_name)
        return False


    # Format the function response and send it back to the model
    print("\n====================================================================")
    print("🛠 Tool's output:")
    print("====================================================================")
    print(result)

    messages.append({
        "role": "assistant",
        "content": f"{tool_name} tool response: {result}"
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
        "model": model_path,
        "messages": messages,
        "temperature": 0.5
    }

    # Send follow-up request to model for final response
    response = requests.post(url, headers=headers, data=json.dumps(followup_data))

    if response.status_code == 200:
        final_response = response.json()["choices"][0]["message"]['content']
        print("\n====================================================================")
        print("🤖 Model's response:")
        print("====================================================================")
        print(final_response)
    else:
        print("Follow-up request failed:", response.status_code, response.text)
        return False
    
    # Log the final response
    logger.info("Final response: %s", final_response)
    
    return True


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 src/zenbot.py '<user_input>' '<order_info_json>' '<model_path>' '<log_path>'")
        sys.exit(1)

    user_input = sys.argv[1]
    order_info = json.loads(sys.argv[2])
    model_path = sys.argv[3]
    log_path = sys.argv[4]

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

    # Run ZenBot
    if handle_message(user_input, order_info, model_path):
        logger.info("ZenBot finished successfully")
    else:
        logger.info("ZenBot didn't finish successfully")

    print("\n====================================================================")
    print("📃 More information in the log file:")
    print("====================================================================")
    print(log_path)

    