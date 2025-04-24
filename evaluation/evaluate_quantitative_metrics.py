"""
Evaluation script for Baseline and ZenBot agents: quantitative response quality metrics.

Usage:
    python evaluation/evaluate_quantitative_metrics.py \
        --agent baseline \
        --csv-in data/sample_data.csv \
        --log-path logs/sample_data/baseline_quantitative.log \
        --csv-out evaluation/data/sample_data/baseline_quantitative.csv

The input CSV must have columns:
    example_id,user_input,order_info_json,correct_tool,correct_policy,correct_api_status

The output CSV will have columns:
    example_id,intent_is_correct[yes|no|unknown],policy_error[TP|TN|FP|FN|unknown],api_error[TP|TN|FP|FN|unknown],response_time

Metrics computed:
    - Intent Accuracy
    - Policy Adherence
    - API Status Accuracy
    - Latency statistics
"""
import argparse
import sys
import os
import csv
import json
import statistics
import importlib
import logging

# TODO - add source directory to path in a different way
SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, SRC)

from utils import configure_logger, pretty_section

def str_to_bool(s: str) -> bool:
    return s.strip().lower() in ('true', '1', 'yes')


def main():
    parser = argparse.ArgumentParser(description="Evaluate chatbot agents on a set of examples.")
    parser.add_argument("--agent", choices=["baseline", "zenbot"], required=True,
                        help="Which agent to evaluate (module name in src/)")
    parser.add_argument("--log-path", required=True,
                        help="Path to write logs for all examples")
    parser.add_argument("--csv-in", required=True,
                        help="Path to input CSV with example_id,user_input,order_info_json,correct_tool,correct_policy,correct_api_status")
    parser.add_argument("--csv-out", required=True,
                        help="Path to output CSV with example_id,intent_is_correct,policy_error,api_error,response_time")
    args = parser.parse_args()

    # Validate that the input CSV exists
    if not os.path.isfile(args.csv_in):
        parser.error(f"The input CSV file '{args.csv_in}' does not exist.")

    # Ensure the output directory exists
    output_dir = os.path.dirname(args.csv_out)
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        parser.error(f"Could not create output directory '{output_dir}': {e}")

    # Dynamically import the agent module (baseline or zenbot)
    agent_mod = importlib.import_module(args.agent)
    run_agent = agent_mod.run_agent

    # Configure logger, log dir creation is handeled here
    logger = logging.getLogger(__name__)
    configure_logger(args.log_path, level=logging.DEBUG)

    total = 0
    intent_correct = 0
    policy_correct = 0
    api_attempts = 0
    api_correct = 0
    policy_evaluated = 0
    latencies = []
    details = []

    # Load all examples to enable progress reporting
    with open(args.csv_in, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    total_examples = len(rows)
    print(f"Starting evaluation of {total_examples} examples with agent: {args.agent}\n")

    for idx, row in enumerate(rows, start=1):
        example_id = row['example_id']
        user_input = row['user_input']
        order_info = json.loads(row['order_info_json'])
        expected_tool = row['correct_tool']
        expected_policy = str_to_bool(row['correct_policy'])
        exp_api_raw = row['correct_api_status'].strip()
        expected_api = exp_api_raw if exp_api_raw else None
        intent_is_correct = "unknown"
        policy_error = "unknown"
        api_error = "unknown"

        # Print progress
        print(f"Processing example {idx}/{total_examples} (ID: {example_id})")

        # Log example metadata
        logger.debug("Example ID: %s", example_id)

        # Run the agent
        try:
            result = run_agent(user_input, order_info, args.log_path)
        except Exception as e:
            print(f"Example {example_id} raised exception: {e}", file=sys.stderr)
            continue

        # Intent Accuracy
        if result.tool_name == expected_tool:
            intent_correct += 1
            logger.debug("Intent correct: Yes (actual=%s, expected=%s)", result.tool_name, expected_tool)
            intent_is_correct = "yes"
        else:
            logger.debug("Intent correct: No (actual=%s, expected=%s)", result.tool_name, expected_tool)
            intent_is_correct = "no"

        # Policy Adherence - only if the intent was recognized correctly
        # and we actually called the tool (so api_status and tool_output exist)
        if (
            result.tool_name == expected_tool
            and result.api_status is not None
            and result.tool_output is not None
        ):
            policy_evaluated += 1
            if result.policy_passed == expected_policy:
                policy_correct += 1
                if result.policy_passed == True and expected_policy == True:
                    policy_error = "TP"
                else:
                    policy_error = "TN"
                logger.debug(
                    "Policy correct: Yes (actual=%s, expected=%s, classification_error=%s)",
                    result.policy_passed,
                    expected_policy,
                    policy_error
                )
            else:
                if result.policy_passed == True and expected_policy == False:
                    policy_error = "FP"
                else:
                    policy_error = "FN"
                logger.debug(
                    "Policy correct: No (actual=%s, expected=%s, classification_error=%s)",
                    result.policy_passed,
                    expected_policy,
                    policy_error
                )

        # API Status Accuracy
        if expected_api is not None and result.api_status is not None:
            api_attempts += 1
            # Normalize: anything except "error" counts as "ok"
            actual_api = "ok" if result.api_status != "error" else "error"
            if actual_api == expected_api:
                api_correct += 1
                if actual_api == "ok" and expected_api == "ok":
                    api_error = "TP"
                else:
                    api_error = "TN"
                logger.debug("API status OK: Yes (normalized actual=%s, expected=%s, classification_error=%s)", 
                             actual_api, expected_api, api_error)

            else:
                if actual_api == "ok" and expected_api == "error":
                    api_error = "FP"
                else:
                    api_error = "FN"
                logger.debug("API status OK: No (normalized actual=%s, expected=%s, classification_error=%s)", 
                             actual_api, expected_api, api_error)

        # Latency
        latencies.append(result.response_time)
        # Record per‐example metrics
        details.append({
            "example_id": example_id,
            "intent_is_correct": intent_is_correct,
            "policy_error": policy_error,
            "api_error": api_error,
            "response_time": f"{result.response_time:.3f}"
        })

        total += 1

    # Compute final metrics
    intent_acc = (intent_correct / total * 100) if total else 0.0
    policy_acc = (policy_correct / policy_evaluated * 100) if policy_evaluated else 0.0
    api_acc = (api_correct / api_attempts * 100) if api_attempts else 0.0

    # Latency summary
    latency_summary = {
        'min': min(latencies, default=0.0),
        'max': max(latencies, default=0.0),
        'mean': statistics.mean(latencies) if latencies else 0.0,
        'median': statistics.median(latencies) if latencies else 0.0,
        'stdev': statistics.stdev(latencies) if len(latencies) > 1 else 0.0
    }

    # Log and print summary
    summary = (
        f"Evaluated {total} examples with agent: {args.agent}\n\n"
        f"Intent Accuracy:      {intent_acc:.2f}% ({intent_correct}/{total})\n"
        f"Policy Adherence:     {policy_acc:.2f}% ({policy_correct}/{policy_evaluated if policy_evaluated else 0})\n"
        f"API Status Accuracy:  {api_acc:.2f}% ({api_correct}/{api_attempts if api_attempts else 0})\n\n"
        "Latency (seconds):\n"
        f"  min    = {latency_summary['min']:.3f}\n"
        f"  mean   = {latency_summary['mean']:.3f}\n"
        f"  max    = {latency_summary['max']:.3f}\n"
        f"  median = {latency_summary['median']:.3f}\n"
        f"  stdev  = {latency_summary['stdev']:.3f}"
    )

    with open(args.csv_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=details[0].keys())
        writer.writeheader()
        writer.writerows(details)

    logger.info("Quantitative details written to %s", args.csv_out)
    logger.info(summary)

    pretty_section("📊 Evaluation summary", summary)
    pretty_section("📜 Log files", f"Log path: {args.log_path}\nOutput details path: {args.csv_out}") 

if __name__ == '__main__':
    main()

