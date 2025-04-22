import sys
import requests
import json
from datetime import datetime
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

# Your model name
model = "pretrained/gguf_models/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf"

# Minimal self-contained system prompt
today = datetime.now().strftime("%Y-%m-%d")
order_info = {
    "order_id": "123",
    "order_date": "2025-04-20",
    "user_id": "user_1"
}

SYSTEM_PROMPT = f"""
You are ZenBot, a helpful order support assistant.

You have access to tools to help the user:
- Use the `track_order` tool if the user wants to check or track their order.
- Use the `cancel_order` tool if the user wants to cancel their order.

Call the appropriate tool **only** if the user's intent is clear.

Examples:
- "Where is my package?" → call `track_order`
- "Cancel my order" → call `cancel_order`
- "Can you help me?" → do not call any tool

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

print(f"""
====================================================================
⚡                         ZenBot is live!                    
====================================================================

(type 'quit' or 'exit' to stop)

👋 Hey there! I’m ZenBot. Not a human, but here to help!
🧘 I don’t get angry, just keep it bot-positive.
🎯 I can track or cancel your order.

⚠️  Using dummy order info for this demo:
{order_info}

🗨️ What would you like to do?
""")

try:
    user_input = input()
except EOFError:
    print("\nGoodbye!")
    sys.exit()
if user_input.lower().strip() in ("quit", "exit"):
    print("Goodbye!")
    sys.exit()

# check sentiment before doing anything else
# TODO - improve sentiment analysis model
# the threshold is set to 10 here because all cancellation requests
# are flagged as negative with lower values... 
# is_frustrated is left as a placeholder
if is_frustrated(user_input, threshold=10.0):
    # record it in memory
    escalation_msg = (
      "I'm sorry, you seem frustrated. "
      "I'm transferring you to a live agent now."
    )
    print(f"Bot: {escalation_msg}")
    # TODO - call a real escalation API
    sys.exit()

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
    "model": model,
    "messages": messages,
    "tools": tools,
    "temperature": 0.15
}

# 1. Send initial request to model, expecting it to call the function
response = requests.post(url, headers=headers, data=json.dumps(data))
reply = response.json()["choices"][0]["message"]

tool_calls = reply.get("tool_calls", [])
if tool_calls:
    tool_call = tool_calls[0]
    function_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])

    print("\n====================================================================")
    print("📲 Model requested function call:")
    print("====================================================================")
    print(json.dumps(tool_call, indent=2))

    # 2. Perform the actual function call (Real FREE API call)
    if function_name == "track_order":
        try:
            order_id = arguments["order_id"]
            resp = OrderTrackingClient().track(order_id)
            result = f"Order status: {resp}"
        except Exception as e:
            result = f"Error retrieving status: {str(e)}"
    elif function_name == "cancel_order":
        try:
            order_id = arguments["order_id"]
            order_date = arguments["order_date"]
            user_id = arguments["user_id"]
            if not can_cancel(order_date, user_id):
                result = f"Order {order_id} cannot be canceled per policy."
            else:
                resp = OrderCancellationClient().cancel(order_id)
                result = f"Cancellation result: {resp}"
        except Exception as e:
            result = f"Error processing cancellation: {str(e)}"
    else:
        print(f"Unknown function called: {function_name}")
else:
    print("\nNo function calls were triggered by the model.")
    sys.exit()


# Step 3: Format the function response and send it back to the model
print("\n====================================================================")
print("🛠 Tool's output:")
print("====================================================================")
print(result)

messages.append({
    "role": "assistant",
    "content": f"{function_name} tool response: {result}"
})

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
    "model": model,
    "messages": messages,
    "temperature": 0.5
}

response = requests.post(url, headers=headers, data=json.dumps(followup_data))

if response.status_code == 200:
    final_reply = response.json()["choices"][0]["message"]
    print("\n====================================================================")
    print("🤖 Model's response:")
    print("====================================================================")
    print(final_reply["content"])
else:
    print("Follow-up request failed:", response.status_code, response.text)
    