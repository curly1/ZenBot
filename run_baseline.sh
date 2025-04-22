#!/bin/bash

# run_baseline.sh
# A simple bash runner to invoke baseline rule-based agent.

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <user_input> <order_info_json> <log_path>"
  echo "user_input            - the user input message to the chatbot (string)"
  echo "order_info_json       - the order information in JSON format (string)"
  echo "log_path              - the path to the log file, it is created internally in src/baseline.py if it doesn't exist (string)"
  echo ""
  echo "Example: $0 \"cancel my order\" '{\"order_id\":\"123\",\"order_date\":\"2025-04-20\",\"user_id\":\"user_1\"}' \"logs/baseline.log\""
  exit 1
fi

MESSAGE="$1"
ORDER_JSON="$2"
LOG_PATH="$3"

python3 src/baseline.py "$MESSAGE" "$ORDER_JSON" "$LOG_PATH" || {
  echo "Error: Baseline agent execution failed."
  exit 1
}