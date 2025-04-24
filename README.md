<p align="center">
  <img src="docs/logo.png" alt="Project Logo" width="200">
</p>

<h1 align="center">Generative Policy‑Aware Chatbot</h1>

<p align="center">
  <strong>🧘 Keep calm</strong> and <strong>chat</strong> with me 💬<br>
  📦 Your orders deserve order! ✅
</p>

This project implements a fully generative chatbot. It integrates with two API endpoints: `OrderCancellation` and `OrderTracking`. The chatbot adheres to specific company policies using an LLM for decision-making. The overall flow of ZenBot:

<p align="center">
  <img src="docs/flow_diagram.png" alt="Project Logo" width="600">
</p>


## Table of Contents

1. [🎯 Features](#-features)
2. [🛠 Installation](#-installation)
3. [🧠 Technical Choices](#-technical-choices)
4. [🚀 How to Run](#-how-to-run)
5. [📁 Project Structure](#-project-structure)
6. [🧪 Experiment Design & Evaluation](#-experiment-design--evaluation)
7. [✅ Testing](#-testing)
8. [🤖 Future Enhancements](#-future-enhancements)

## 🎯 Features

- **Conversational order support**: Track and cancel orders using a natural language interface.
- **Policy-aware agent**: Enforces return windows, quotas, and blackout dates as per company rules.
- **Local, fast LLM reasoning**: Makes tool-augmented decisions using the compact LLM model running locally.
- **Sentiment detection**: Flags negative sentiment before routing to tool logic or escalation paths.
- **Baseline A/B testing**: Includes a classical rule-based baseline agent for side-by-side comparison and performance benchmarking.
- **End-to-end evaluation**: Computes quantitative and qualitative metrics for a synthetic evaluation datatest using an LLM judge.

# 🛠 Installation

1. Create a conda environment.

``` bash
conda create -n zenbot python=3.10 -y
conda activate zenbot
```

2. Download ZenBot code and install the requirements for this project.

```bash
git clone https://github.com/curly1/ZenBot.git
cd ZenBot
pip install -r requirements.txt
```

3. Build [llama.cpp](https://github.com/ggml-org/llama.cpp?tab=readme-ov-file#building-the-project) on your system, e.g. on MacOS:

```bash
brew install llama.cpp
```

# 🧠 Technical Choices

**Local inference**  
Lightweight C++ HTTP server (the `llama-server` wrapper from `llama.cpp`) for low-latency, single-node deployment.

**LLM model**  
`Mistral-7B-Instruct-v0.3` (quantized to `Q4_K_M` and stored in `GGUF` format) balances latency and response quality.

**API simulation**  
Mock order tracking/cancellation via the `ZENBOT_SIMULATE_API` flag.

**Python wrappers**  
Internal clients (`OrderTrackingClient`, etc.) encapsulate API logic for clarity and testability.

**Sentiment gating**  
A lightweight `Transformers` model runs `is_frustrated` checks pre-routing.

**Logging & Observability**  
Logs detail tool calls, LLM latency, decisions, and flow outcomes.

**Robust evaluation**  
Quantitative and qualitative metrics benchmark performance.

**Test suite**  
Pytest-based tests validate core behaviors and policy flow correctness.

# 🚀 How to Run

This section shows how to run both agents for a single input prompt and input order information in JSON format.

## Baseline rule-based agent

```bash
input_prompt="track my order"
order_info='{"order_id":"123","order_date":"2025-04-20","user_id":"user_1"}'
log_filepath="logs/baseline.log"

bash run_baseline.sh ${input_prompt} ${order_info} ${log_filepath}
```

## ZenBot

1. Download [Mistral-7B-Instruct-v0.3.Q4_K_M.gguf](https://huggingface.co/MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF/blob/main/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf) model.

2. Run `llama-server`:

> Please note: The port is hard-coded to 8080 in `src/zenbot.py`.

```bash
model_path="pretrained/gguf_models/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf"
llama-server -m ${model_path} --port 8080 --jinja
```

3. Run ZenBot

```bash
input_prompt="track my order"
order_info='{"order_id":"123","order_date":"2025-04-20","user_id":"user_1"}'
log_filepath="logs/zenbot.log"

bash run_zenbot.sh ${input_prompt} ${order_info} ${log_filepath}
```

# 📁 Project Structure

```
.
├── README.md
├── data/                      ← Input CSVs for evaluation
├── docs/                      ← Architecture diagrams & reports
│   ├── evaluation_process.png
│   ├── evaluation_report.pdf
│   ├── flow_diagram.png
│   └── logo.png
├── evaluation/                ← Evaluation scripts & output data
│   ├── analyze_qualitative_metrics.py
│   ├── analyze_quantitative_metrics.py
│   ├── data/                  ← Generated evaluation data
│   ├── evaluate_qualitative_metrics.py
│   └── evaluate_quantitative_metrics.py
├── logs/                      ← Agent run logs (can be removed post-evaluation)
├── pytest.ini                 ← Test configuration
├── requirements.txt           ← Python dependencies
├── run_baseline.sh            ← Convenience script: baseline agent
├── run_zenbot.sh              ← Convenience script: ZenBot agent
├── src/                       ← Core application code
│   ├── api_clients.py         ← HTTP wrappers for order APIs
│   ├── baseline.py            ← Rule-based reference agent
│   ├── policies.py            ← Cancellation policy logic
│   ├── sentiment.py           ← Frustration detection
│   ├── utils.py               ← Logging, pretty-printing helpers
│   └── zenbot.py              ← LLM-powered agent implementation
└── tests/                     ← Unit tests
```


### Directory Overview

- **`src/`**:  
  All production code: baseline rule-based agent, LLM-driven ZenBot, plus shared utilities and policy logic.

- **`evaluation/`**:  
  Scripts for running and analyzing end-to-end tests. Includes both qualitative (LLM-judge) and quantitative metrics, along with generated data under `evaluation/data/`.

- **`data/`**:  
  CSV fixtures and sample inputs used by the evaluation scripts.

- **`logs/`**:  
  Output logs from batch and interactive runs of both agents.

- **`docs/`**:  
  Helpful diagrams, process flowcharts, and final evaluation reports.

- **`tests/`**:  
  Pytest-based unit tests ensuring the baseline agent behaves correctly; more tests can be added to cover ZenBot routes and utilities.


> Please note: The `data/`, `logs/`, and `evaluation/data/` folders are committed here for demonstration purposes. You can safely delete them after you’ve generated or reviewed all evaluation outputs.

# 🧪 Experiment Design & Evaluation

## Objective

Evaluate ZenBot's ability to:

- Accurately recognize user intents and select the appropriate tool.
- Enforce business rules related to cancellations, returns, and blackout periods.
- Generate coherent, contextually appropriate responses using the LLM.

## Baseline Comparison

A lightweight **rule-based agent** serves as the experimental baseline.  
Implemented as a Python CLI, it supports two intents, order cancellation and order tracking, via:

- Simple keyword matching
- Static, hardcoded response templates
- No use of an LLM

This baseline provides a control point to assess the added value of LLM-driven reasoning, policy enforcement, and dynamic generation.

## Evaluation

**The complete evaluation report is available [here](docs/evaluation_report.pdf).**  
Below is a high-level overview of the evaluation process and the metrics used.

### Process Overview

ZenBot’s evaluation follows an iterative, data-driven approach. Each evaluation cycle involves metric analysis, followed by targeted improvements — either in the agent itself, the test data, or the evaluation methodology (e.g., refining the LLM judge).

<p align="center">
  <img src="docs/evaluation_process.png" alt="Evaluation Process" width="200">
</p>

### Steps

- Run a **200-request A/B test**: Evaluate both the baseline and ZenBot on the same input dataset.
- **Log internal decisions**: Capture tool selections, policy applications, API success/failure, and latency.
- Use an **LLM-based judge** to assess response quality across both agents.
- Store all results for metric-based comparison and trend tracking.
- **Analyze and compare**: Examine quantitative and qualitative performance differences.
- **Visualize insights**: Generate comparison tables and plots to spot patterns.
- Investigate **failure cases** to uncover common errors, misinterpretations, or policy violations.

### Synthetic Dataset for Evaluation

To evaluate ZenBot in a controlled yet realistic setting, a **synthetic dataset of 200 user requests** using **ChatGPT-4o** was generated. The prompt was iteratively refined to ensure the data was both accurate and challenging.

#### Dataset Composition

- **50** tracking requests  
  — Includes variations with and without the keyword `track`
- **50** cancellation requests  
  — Includes **eligible** and **ineligible** cases, with and without the keyword `cancel`
- **50** random requests without intent  
  — No occurrence of keywords like `track`, `status`, or `cancel`
- **50** random requests with misleading keywords  
  — Contains those keywords but expresses **no actionable intent**

#### Structure & Labels

Each record in the dataset includes:
- `example_id`: unique identifier
- `user_input`: synthetic user utterance
- `order_info_json`: contains `order_id`, `user_id`, `order_date` (random within past 90 days)
- `correct_tool`: expected tool (`track_order`, `cancel_order`, or `none`)
- `correct_policy`: boolean indicating if policy allows the action (e.g. cancellation eligibility)
- `correct_api_status`: `ok` for valid intents, `None` for no-intent cases

#### Assumptions & Constraints

- Cancellation policy depends on the order date.
- Tracking is always permitted (`correct_policy = True`).
- Dataset is fully synthetic and contains **no sensitive information**.

**Future improvement:** Add programmatic validation to ensure all records conform to the dataset specification above.

### Metrics

ZenBot is evaluated using a mix of **quantitative**, **qualitative**, and **classification** metrics. These help measure the correctness, performance, and user experience quality of the agent.

#### Core Metrics

| **Metric**               | **Type**        | **Description**                                                              |
|--------------------------|------------------|-----------------------------------------------------------------------------|
| **Intent Accuracy**      | Quantitative     | % of requests where the correct tool was selected                           |
| **Policy Adherence**     | Quantitative     | % of responses that correctly enforce business rules                        |
| **API Status Accuracy**  | Quantitative     | % of API calls that return a successful status (excluding `None` cases)     |
| **Latency**              | Quantitative     | End-to-end response time (min, max, mean, median, stdev)                    |
| **Response Naturalness** | Qualitative      | How natural the response sounds (1–5 scale)                                 |
| **Response Coherence**   | Qualitative      | Logical consistency of the response (1–5 scale)                             |
| **Response Helpfulness** | Qualitative      | Usefulness of the response to the user (1–5 scale)                          |
| **Response Quality**     | Qualitative      | Binary judgment: meets or fails a minimum quality threshold                 |

- `Policy Adherence` is only measured when the correct tool is selected.  
- `API Status Accuracy` is evaluated only when a non-`None` status is expected.  
- *Note:* In simulation mode, API statuses are randomized; this metric is included as a placeholder for when real integrations are available.

#### Latency Breakdown

Latency is reported using five statistics:
- **Minimum**
- **Maximum**
- **Mean**
- **Median**
- **Standard deviation (stdev)**

#### Classification Metrics

Where binary outcomes are applicable (e.g., policy decisions, API responses), the following are computed:

- Precision  
- Recall  
- F1 Score  
- False Positive Rate (FPR)  
- False Negative Rate (FNR)  
- ROC Curve  
- Area Under the Curve (AUC)

#### Qualitative Score Analysis

For Likert-style metrics (1–5 scale), basic descriptive statistics are computed (e.g., mean, mode, histograms), along with correlation analysis between dimensions such as coherence and helpfulness.

#### Inter-Rater Agreement (Planned)

After manual annotation, the following metrics can validate consistency between human annotators or between human and automated systems:

- **Cohen’s Kappa**:  
  For binary scores (e.g., response quality). Adjusts for chance agreement and accounts for bias toward always passing or failing.

- **Kendall’s Tau**:  
  Measures the **relative ranking** consistency of Likert scores. Robust to small discrepancies.

- **Spearman’s Rho**:  
  Captures how far apart two sets of rankings are. Useful when **magnitude** of disagreement matters.

> These agreement metrics are part of future work to strengthen the evaluation framework.

### How to run

Evaluation of quantitative metrics:

```bash
python evaluation/evaluate_quantitative_metrics.py \
  --agent {baseline,zenbot} \
  --csv-in data/sample_data.csv \
  --csv-out evaluation/data/sample_data/{baseline,zenbot}/quantitative.csv \
  --log-path logs/sample_data/{baseline,zenbot}/quantitative.log
```

Evaluation of qualitative metrics:

```bash
python evaluation/evaluate_qualitative_metrics.py \
  --agent {baseline,zenbot} \
  --csv-in data/sample_data.csv \
  --csv-out evaluation/data/sample_data/{baseline,zenbot}/qualitative.csv \
  --log-path logs/sample_data/{baseline,zenbot}/qualitative.log
```

Analysis of quantitative metrics:
```bash
python evaluation/analyze_quantitative_metrics.py \
  evaluation/data/eval_data/{baseline,zenbot}/quantitative.csv
```

Analysis of qualitative metrics:
```bash
python evaluation/analyze_qualitative_metrics.py \
  evaluation/data/eval_data/{baseline,zenbot}/qualitative.csv
```

# ✅ Testing

Use pytest to run all tests from project root.
```bash
pytest
```

# 🔮 Future Enhancements

### 🛠️ Feature Expansion
- [ ] Integrate additional APIs and support more user intents
- [ ] Add tool call confirmation for ambiguous or low-confidence user inputs
- [ ] Implement Retrieval-Augmented Generation (RAG)
- [ ] Use real-world data for evaluation in addition to synthetic examples

### 🧠 LLM Model Improvements
- [ ] Switch to a newer and larger Mistral model ([Mistral-Small-3.1-24B-Instruct-2503](https://huggingface.co/bartowski/mistralai_Mistral-Small-3.1-24B-Instruct-2503-GGUF))
- [ ] Experiment with alternative models, e.g. [Llama-xLAM-2-70b-fc-r](https://huggingface.co/DevQuasar/Salesforce.Llama-xLAM-2-70b-fc-r-GGUF)
      (top of [Berkeley Function-Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html), as of 2025‑04‑13)
- [ ] Use 8-bit quantization or full-precision model depending on latency and memory constraints
- [ ] Fine-tune the LLM for domain-specific improvements
- [ ] Explore hyperparameter tuning (e.g., temperature)

### 📏 Evaluation & Testing
- [ ] Improve the diversity and realism of the synthetic dataset
- [ ] Introduce statistical significance testing for evaluation metrics
- [ ] Add meta-evaluation to assess the reliability of the LLM judge
- [ ] Evaluate model performance on:
  - [ ] Safety (e.g., avoidance of sensitive information leakage)
  - [ ] Hallucinations
  - [ ] Sentiment detection accuracy

### 📈 Experiment Tracking
- [ ] Integrate with [Weave](https://github.com/wandb/weave) or similar tools for experiment management and evaluation visualization

### 🧪 Code Quality & Resilience
- [ ] Improve tool input validation
- [ ] Add retry logic and fallback mechanisms for API failures
- [ ] Expand logging for better observability
- [ ] Strengthen unit test coverage:
  - [ ] Emotion-based escalation logic
  - [ ] LLM unavailability fallback
  - [ ] No tool call flow
  - [ ] Full pipeline flow
  - [ ] Cancellation with policy denial
  - [ ] Cancellation with API error
- [ ] Add utility for automated LLM model downloads
