"""
Evaluation script for Baseline and ZenBot agents using run_agent.

Usage:
    python evaluate_quantitative_metrics.py \
        --agent baseline \
        --log-path logs/sample_data/baseline.log \
        --csv data/sample_data.csv

The input CSV must have columns:
    example_id,user_input,order_info_json,correct_tool,correct_policy,correct_api_status

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
    parser.add_argument("--csv", required=True,
                        help="Path to input CSV with example_id,user_input,order_info_json,correct_tool,correct_policy,correct_api_status")
    args = parser.parse_args()

    # Dynamically import the agent module (baseline or zenbot)
    agent_mod = importlib.import_module(args.agent)
    run_agent = agent_mod.run_agent

    # Configure logger
    logger = logging.getLogger(__name__)
    configure_logger(args.log_path, level=logging.DEBUG)

    total = 0
    intent_correct = 0
    policy_correct = 0
    api_attempts = 0
    api_correct = 0
    policy_evaluated = 0
    latencies = []

    # Load all examples to enable progress reporting
    with open(args.csv, newline='', encoding='utf-8') as csvfile:
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

        # Progress
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
            logger.debug("Intent correct: True (actual=%s, expected=%s)", result.tool_name, expected_tool)
        else:
            logger.debug("Intent correct: False (actual=%s, expected=%s)", result.tool_name, expected_tool)

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
                logger.debug(
                    "Policy correct: True (actual=%s, expected=%s)",
                    result.policy_passed,
                    expected_policy,
                )
            else:
                logger.debug(
                    "Policy correct: False (actual=%s, expected=%s)",
                    result.policy_passed,
                    expected_policy,
                )

        # API Status Accuracy
        if expected_api is not None and result.api_status is not None:
            api_attempts += 1
            # Normalize: anything except "error" counts as "ok"
            actual_api = "ok" if result.api_status != "error" else "error"
            if actual_api == expected_api:
                api_correct += 1
                logger.debug("API status OK: True (normalized actual=%s, expected=%s)", actual_api, expected_api)
            else:
                logger.debug("API status OK: False (normalized actual=%s, expected=%s)", actual_api, expected_api)

        # Latency
        latencies.append(result.response_time)

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

    # Print results

    logger.info("Evaluated %d examples with agent: %s", total, args.agent)
    logger.info("Intent Accuracy:      %.2f%% (%d/%d)", intent_acc, intent_correct, total)
    logger.info("Policy Adherence:     %.2f%% (%d/%d)", policy_acc, policy_correct, policy_evaluated if policy_evaluated else 0)
    logger.info("API Status Accuracy:  %.2f%% (%d/%d)", api_acc, api_correct, api_attempts if api_attempts else 0)
    logger.info("Latency (seconds): min=%.3f mean=%.3f max=%.3f median=%.3f stdev=%.3f",
                latency_summary['min'], latency_summary['mean'], latency_summary['max'],
                latency_summary['median'], latency_summary['stdev'])
    
    pretty_section("📜 Log file", f"Log path: {args.log_path}")

if __name__ == '__main__':
    main()

