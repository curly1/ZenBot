<p align="center">
  <img src="docs/logo.png" alt="Project Logo" width="200">
</p>

<h1 align="center">Generative Policy‑Aware Chatbot</h1>

<p align="center">
  <strong>🧘 Keep calm</strong> and <strong>chat</strong> with me 💬<br>
  📦 Your orders deserve order! ✅
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#license">License</a>
</p>


This project implements a fully generative chatbot using LangChain, integrating it with two API endpoints: `OrderCancellation` and `OrderTracking`. The chatbot adheres to specific company policies using an LLM for decision-making.

	1.	Intent Recognition → 2. Policy Check → 3. Tool Invocation (API call) → 4. Response Generation

# 🎯 Features
- Order tracking and cancellation via mocked API
- Company policy enforcement (return‑window, monthly quota, blackout‑date rules)
- LLM-agent powered decisions using Mistral-7B-Instruct-v0.3 model
- LLM inference with llama.cpp HTTP server
- Sentiment analysis using Transformers
- Step-by-step evaluation using a synthetic dataset and an LLM judge
- Experiment tracking with Weave by W&B

# 🛠 Installation

1. Create a conda environment.

``` bash
conda create -n zenbot python=3.10 -y
conda activate zenbot
```

2. Download ZenBot code and install the requirements for this project.

```bash
git clone <repo_url>
cd repo
pip install -r requirements.txt
```

3. Build [llama.cpp](https://github.com/ggml-org/llama.cpp?tab=readme-ov-file#building-the-project) on your system, e.g. on MacOS:

```bash
brew install llama.cpp
```

# 🧠 Technical Choices

**Framework**: LangChain, chosen for its intuitive workflow management, chaining capabilities, and strong integration with LLMs.

**LLM**: GPT-3.5-turbo via OpenAI's free API tier, chosen due to accessibility and strong performance.

**Mock APIs**: Implemented by checking a `ZENBOT_SIMULATE_API` environment variable. When enabled, returning randomized dummy responses for cancellation and tracking calls instead of making real HTTP requests.

**Monitoring & Evaluation**: Weave by Weights & Biases provides powerful, interactive experiment tracking and analysis.

# 🚀 How to Run

- **Baseline**: 
```
python src/baseline_agent.py
```

- **ZenBot**:

Download [Mistral-7B-Instruct-v0.3.Q4_K_M.gguf](https://huggingface.co/MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF/blob/main/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf) model.

```
llama-server -m pretrained/gguf_models/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf --port 8080 --jinja
python src/zenbot.py
```

# 📁 Project Structure

### TODO - ADD PROJECT STRUCTURE AND DESCRIBE WHAT IS DONE IN THE FILES


# 🧪 Experiment Design & Evaluation

## Objective
Measure how effectively ZenBot:
- Correctly identifies user intent and selects the appropriate tool.
- Enforces business policies for cancellations, returns and blackout periods.
- Generates accurate, coherent responses via the LLM.

## Baseline

We also provide a simple rule-based agent which serves as a baseline for the experiments. It is a simple Python CLI that handles two intents (order cancellation and order tracking) using straightforward keyword matching and static response templates (no LLM).

## Evaluation

- Run an A/B test, i.e. run the 500‑request evaluation dataset through both agents.
- Log tool selections, policy decisions, API responses (success vs. error) and latencies.
- Call the LLM judge to score response quality for both agents. 
- Track distributions for all metrics (histograms, percentiles). 
- Perform statistical significance tests (z-test for binary metrics, t-test for continuous metrics).
- Compare baseline vs. ZenBot on all metrics.
- Run a small subset (50 requests) through both a human rater and the LLM judge to compute inter‑rater agreement and validate judge reliability.
- Visualize differences (tables, charts) between the two agents.
- Examine failure cases to identify common misunderstandings or policy violations.

### Synthetic dataset for evaluation
- **500** synthetic user requests:
  - **250** cancellation requests (eligible and ineligible)
  - **250** tracking requests (successful and failed)
- Each record labeled with the correct tool (`cancel_order` or `track_order`) and expected policy outcome.

### Metrics
| Metric | Type | Description |
|--------|------|-----|
| Intent Accuracy | Quantitative | % of requests where the correct tool was invoked |
| Policy Adherence | Quantitative | % of chatbot responses correctly adhering to policies |
| API Success Rate | Quantitative | % of API calls returning a successful status (no timeouts or errors) |
| Latency | Quantitative | End‑to‑end response times |
| Response quality | Qualitative | Naturalness, coherence, helpfulness of the response |

### Test Cases
- Eligible and ineligible order cancellations
- Successful and failed order tracking requests

### How to run

```bash
python evaluation/evaluate_quantitative_metrics.py \
  --agent {baseline,zenbot} \
  --csv data/sample_data.csv \
  --log-path logs/sample_data/baseline.log
```

### Results

PDF report: [link](docs/results.pdf)

# ✅ Testing

Use pytest to run all tests from project root.
```bash
pytest
```

# 🤖 Future Enhancements

- [ ] Expand to additional APIs and functionalities
- [ ] Add tool call confirmation for ambiguous user inputs
- [ ] Use a version of Mistral-7B-Instruct-v0.3 model with 8-bit quantization (or full precision model, depending on latency/memory requirements and hardware used)
- [ ] Switch to a newer (and larger) Mistral model ([Mistral-Small-3.1-24B-Instruct-2503](https://huggingface.co/bartowski/mistralai_Mistral-Small-3.1-24B-Instruct-2503-GGUF))
- [ ] Upgrade to a different LLM (e.g. [Llama-xLAM-2-70b-fc-r](https://huggingface.co/DevQuasar/Salesforce.Llama-xLAM-2-70b-fc-r-GGUF) which is currently the best model on [Berkeley Function-Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)) (leaderboard updated on 2025-04-13)
- [ ] Experiment with different hyper-parameters for the LLM model (e.g. temperature)
- [ ] LLM fine-tuning
- [ ] Use RAG
- [ ] [Add robust error handling and recovery]
- [ ] Evaluate:
  - [ ] safety (e.g. revealing sensitive information)
  - [ ] hallucinations
  - [ ] sentiment recognition
- [ ] Use real data for evaluation
- [ ] Code improvements:
  - [ ] Tool input validation (e.g. order_info JSON)
  - [ ] Retry logic
  - [ ] Fallback responses
  - [ ] Add more logging
  - [ ] Add unit tests for ZenBot (emotion escalation, LLM unreachable, no tool call, full pipeline flow, cancel flow with policy deny, cancel flow with API error)
