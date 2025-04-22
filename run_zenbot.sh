#!/bin/bash

# run_zenbot.sh
# A simple bash runner to invoke ZenBot.

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <user_input> <order_info_json> <model_path> <log_path>"
  echo "user_input            - the user input message to the chatbot (string)"
  echo "order_info_json       - the order information in JSON format (string)"
  echo "model_path            - the path to the model file (string)"
  echo "log_path              - the path to the log file, it is created internally in src/zenbot.py if it doesn't exist (string)"
  echo ""
  echo "Example: $0 \"cancel my order\" '{\"order_id\":\"123\",\"order_date\":\"2025-04-20\",\"user_id\":\"user_1\"}' \"pretrained/gguf_models/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf\" \"logs/zenbot.log\""
  exit 1
fi

MESSAGE="$1"
ORDER_JSON="$2"
MODEL_PATH="$3"
LOG_PATH="$4"

python3 src/zenbot.py "$MESSAGE" "$ORDER_JSON" "$MODEL_PATH" "$LOG_PATH" || {
  echo "Error: ZenBot execution failed."
  exit 1
}