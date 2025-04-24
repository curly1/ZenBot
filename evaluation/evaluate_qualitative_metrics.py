"""
Evaluation script for Baseline and ZenBot agents: qualitative response quality metrics.

Usage:
    python evaluation/evaluate_qualitative_metrics.py \
        --agent baseline \
        --csv-in data/sample_data.csv \
        --log-path logs/sample_data/baseline/qualitative.log \
        --csv-out evaluation/data/sample_data/baseline/qualitative.csv

The input CSV must have columns:
    example_id,user_input,order_info_json,correct_tool,correct_policy,correct_api_status

The output CSV will have columns:
    example_id,naturalness[1-5],coherence[1-5],helpfulness[1-5],binary_pass[0|1]

Metrics computed per dataset:
    - Naturalness (1-5 average)
    - Coherence   (1-5 average)
    - Helpfulness (1-5 average)
    - Response Quality Pass Rate (0-1 avg)
"""
import argparse
import sys
import os
import csv
import json
import statistics
import importlib
import logging
import requests
import re

# TODO - add source directory to path in a different way
SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, SRC)

from utils import configure_logger, pretty_section

# LLM endpoint (reuse ZenBot settings)
from zenbot import url as LLM_URL, headers as LLM_HEADERS

# System prompt for the judge LLM
def build_judge_prompt(user_input: str, response: str) -> dict:
    system = {
        "role": "system",
        "content": (
            "You are an expert judge evaluating chatbot responses. "
            "Rate the following response on three criteria: naturalness, coherence, and helpfulness. "
            "A helpful response is in line with the user's intent. "
            "Examples of unhelpful responses: "
            "- Sorry. I’m having trouble reaching the language LLM server right now. Please try again later. "
            "- Sorry. I didn't understand that. "
            "- Sorry. An error occurred. "
            "- Error generating final response. "
            "- Unknown tool. "
            "Give each a score from 1 to 5 and a one-sentence justification for each. "
            "Format your output as valid JSON with keys 'naturalness', 'coherence', 'helpfulness', each mapping to an object with 'score' and 'reason'. "
            "Respond only with the raw JSON object, no extra text or markdown."
            "If you’re near your LLM’s token limit, bump up max_tokens so it has room to finish the JSON."
            "Make sure the JSON object starts with { and ends with }."
        )
    }
    user = {
        "role": "user",
        "content": (
            f"User message:\n\"\"\"\n{user_input}\n\"\"\"\n\n"
            "Chatbot response:\n```text\n"
            f"{response}\n"
            "```"
        )
    }
    return {"messages": [system, user], "temperature": 0.0}


def main():
    parser = argparse.ArgumentParser(description="Evaluate chatbot qualitative response quality.")
    parser.add_argument("--agent", choices=["baseline", "zenbot"], required=True,
                        help="Which agent to evaluate (module name in src/)")
    parser.add_argument("--log-path", required=True,
                        help="Path to write the evaluation log")
    parser.add_argument("--csv-in", required=True,
                        help="Path to input CSV with examples")
    parser.add_argument("--csv-out", required=True,
                        help="Path to output CSV with metrics details per response")
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

    # Configure logger, log dir creation is handeled here
    logger = logging.getLogger(__name__)
    configure_logger(args.log_path, level=logging.DEBUG)

    # Import agent and run_agent
    agent_mod = importlib.import_module(args.agent)
    run_agent = agent_mod.run_agent

    natural_scores = []
    coherence_scores = []
    helpful_scores = []
    binary_scores = []
    details = []
    # Score threshold for binary response quality evaluation
    binary_threshold = 4

    # Read examples
    with open(args.csv_in, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    total = len(rows)
    logger.info("Starting qualitative evaluation of %d examples with agent %s", total, args.agent)

    for idx, row in enumerate(rows, start=1):
        example_id = row['example_id']
        user_input = row['user_input']
        order_info = json.loads(row['order_info_json'])

        # Print progress
        print(f"Processing example {idx}/{total} (ID: {example_id})")

        # Log example metadata
        logger.info("Example ID: %s", example_id)

        # Run the agent to get the response
        try:
            result = run_agent(user_input, order_info, args.log_path)
        except Exception as e:
            logger.error("Example %s run_agent error: %s", example_id, e)
            continue

        response = result.final_response
        # Build judge prompt and call LLM
        payload = build_judge_prompt(user_input, response)
        payload["max_tokens"] = 1024
        try:
            resp = requests.post(LLM_URL, headers=LLM_HEADERS, json=payload)
            resp.raise_for_status()
            judge_text = resp.json().get('choices', [])[0].get('message', {}).get('content', '')

            # there is still a missing closing brace for some LLM judge responses
            # even after adjusting token limit and making the prompt more strict, 
            # so patch it here with a brace balancer
            opens = judge_text.count('{')
            closes = judge_text.count('}')
            if opens > closes:
                judge_text += '}' * (opens - closes)           

            # Try strict JSON parse
            try:
                metrics = json.loads(judge_text)
            except json.JSONDecodeError:
                # Fallback: extract the first JSON object non-greedily
                m = re.search(r'\{.*?\}', judge_text, re.DOTALL)
                if m:
                    try:
                        metrics = json.loads(m.group(0))
                    except json.JSONDecodeError:
                        metrics = None
                else:
                    metrics = None
            
            if logger.getEffectiveLevel() == logging.DEBUG:
                debug_dir = os.path.join(os.path.dirname(args.log_path), "judge_debug")
                os.makedirs(debug_dir, exist_ok=True)
                # If still no valid metrics, dump raw text for debugging
                if metrics is None:
                    debug_file = os.path.join(debug_dir, f"{example_id}-fail.txt")
                    with open(debug_file, "w", encoding="utf-8") as dbg:
                        dbg.write(judge_text)
                    logger.error(
                        "Judge LLM parse failed for example %s; raw output saved to %s",
                        example_id, debug_file
                    )
                    continue
                else:
                    debug_file = os.path.join(debug_dir, f"{example_id}-ok.txt")
                    with open(debug_file, "w", encoding="utf-8") as dbg:
                        dbg.write(judge_text)
                
        except Exception as e:
            logger.error("Judge LLM failed for example %s: %s", example_id, e)
            continue
        
        # Extract and log
        for key, scores_list in (('naturalness', natural_scores),
                                  ('coherence', coherence_scores),
                                  ('helpfulness', helpful_scores)):
            entry = metrics.get(key, {})
            score = entry.get('score')
            reason = entry.get('reason')
            if isinstance(score, (int, float)):
                scores_list.append(score)
            logger.info(
                "Example %s %s: score=%s, reason=%s",
                example_id, key, score, reason
            )
        # Compute binary pass/fail: average score >= threshold
        avg_score = sum((metrics.get('naturalness',{}).get('score',0),
                         metrics.get('coherence',{}).get('score',0),
                         metrics.get('helpfulness',{}).get('score',0))) / 3
        binary = 1 if avg_score >= binary_threshold else 0
        binary_scores.append(binary)
        logger.info(
            "Example %s binary_pass: %d (avg=%.2f)",
            example_id, binary, avg_score
        )
        details.append({
            "example_id":   example_id,
            "naturalness":  metrics.get('naturalness',{}).get('score',0),
            "coherence":    metrics.get('coherence',{}).get('score',0),
            "helpfulness":  metrics.get('helpfulness',{}).get('score',0),
            "binary_pass":  binary
        })

    # Compute averages
    def avg(lst): return statistics.mean(lst) if lst else 0.0

    # Log and print summary
    summary = (
        f"Evaluated {total} examples with agent: {args.agent}\n\n"
        f"Naturalness (1-5 avg): {avg(natural_scores):.2f}\n"
        f"Coherence   (1-5 avg): {avg(coherence_scores):.2f}\n"
        f"Helpfulness (1-5 avg): {avg(helpful_scores):.2f}\n"
        f"Response Quality Pass Rate (0-1 avg): {avg(binary_scores):.2f}"
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
