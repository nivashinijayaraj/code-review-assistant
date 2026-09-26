# Code Review Assistant

This tool reviews Python code and reports bugs, security vulnerabilities, style issues and optimization opportunities. It combines rule-based static analysis (pylint and bandit) with an open-source code model (Qwen2.5-Coder-7B-Instruct), and verifies the AI's answers against the actual code to reduce false positives.

## How it works

1. **Static analysis:** pylint and bandit check the code for bugs, style issues and security problems.
2. **AI review:** Qwen2.5-Coder-7B-Instruct (running locally on a Colab GPU) reviews the numbered code and returns issues in JSON.
3. **Verification:** each AI answer must quote the exact code it refers to. If that code is not on that line (or one line above/below), the answer is rejected as a hallucination. Wrong line numbers are corrected.
4. **Merging:** issues on the same line and category are combined, and each issue shows which tools found it (e.g. `pylint, llm`).

## Project files

| File | Purpose |
|---|---|
| `analyzer.py` | runs pylint and bandit and returns issues in one common format |
| `code_review_assistant.ipynb` | Colab notebook: AI model, verification, web interface and evaluation |
| `test.py` | small sample file with known problems |
| `requirements.txt` | list of required libraries |

## Setup

**Static analysis only (laptop, no GPU):**
```bash
pip install -r requirements.txt
python analyzer.py
```

**Full version with AI (Google Colab):**
1. Open `code_review_assistant.ipynb` in Google Colab.
2. Select **Runtime → Change runtime type → T4 GPU**.
3. Upload `analyzer.py` using the Files panel.
4. Click **Runtime → Run all** (the first model download takes about 5–10 minutes).

## Usage

Run the Gradio cell in the notebook and open the link it prints. Paste Python code into the box and click **Submit**. The review shows the line, category, which tools found it, the problem and a suggested fix.

## Results

Tested on 12 labelled code snippets (10 known issues and 2 clean snippets).

| Mode | Precision | Recall | F1 | Time (s) |
|---|---|---|---|---|
| static (pylint + bandit) | 0.89 | 0.80 | 0.84 | 29.8 |
| llm (AI only) | 0.73 | 0.80 | 0.76 | 78.3 |
| hybrid | 0.71 | 1.00 | 0.83 | 85.7 |

Static tools alone were the most precise and fastest, but missed 2 of the 10 issues, both logic bugs such as division by zero on an empty list. The hybrid mode found all 10 issues (100% recall). The trade-off was lower precision (0.71), mainly because the AI sometimes labelled the same issue with a different category, and because AI review takes several seconds per file.

## Dependencies

All tools and models are open-source:
- pylint (GPL-2.0), run as a separate command-line tool
- bandit (Apache-2.0)
- transformers, accelerate (Apache-2.0)
- bitsandbytes (MIT), for 4-bit quantization
- torch (BSD-3-Clause)
- gradio (Apache-2.0)
- Qwen2.5-Coder-7B-Instruct model (Apache-2.0)

The model runs inside the Colab session, so code is not sent to any external AI service.

## Limitations and future work

- **Small test set:** 12 snippets is enough to compare modes, but not to measure general accuracy. A larger, real-world dataset is needed.
- **Missed boundary case:** the AI did not flag `age > 18`, because whether it is a bug depends on a business rule not stated in the code.
- **Category disagreements:** the AI sometimes labels a security or style issue as a bug (e.g. `eval`), which counts as an extra finding.
- **Weak style comments:** on clean code, the AI occasionally suggests unnecessary style changes. A future improvement is to accept AI style comments only when a static tool agrees.
- **Python only:** support for other languages could be added with tools like ESLint for JavaScript.
