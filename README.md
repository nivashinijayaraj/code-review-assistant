# Code Review Assistant

This tool reviews Python code and reports bugs, security vulnerabilities, style issues and optimization opportunities. It combines rule-based static analysis (pylint and bandit) with an open-source code model (Qwen2.5-Coder-7B-Instruct), and verifies the AI's answers against the actual code to reduce false positives.


## How it works

The review runs in four steps.

### 1. Preprocessing
- The code is parsed with Python's built-in **Abstract Syntax Tree (`ast`) module**, which reads code the way Python does, without running it.
- The code is cleaned first: tabs are converted to spaces and line endings are normalised.
- If the code is broken (for example, a missing colon), the syntax error is reported and the review **continues**, so incomplete code does not stop the tool.

### 2. Static analysis
Two open-source tools are used:
- **Pylint:** checks bugs and style, e.g. a list used as a default value, or an import that is never used.
- **Bandit:** checks security, e.g. `eval`, `shell=True`, or passwords written in the code.

**Why these tools:** alternatives such as flake8 or ruff exist, but pylint and bandit together cover all four categories (bug, security, style, optimization), are free, and produce JSON output that is easy to process in Python.

These tools follow **fixed rules**: they detect known patterns in how code is written. They are fast and accurate, but they do not understand what the code is supposed to do.

### 3. AI review
- Model: **Qwen2.5-Coder-7B-Instruct**
- **Why this model:** it is open-source, trained specifically on code, follows instructions such as "reply in JSON", and fits on a free Colab GPU using 4-bit quantization. Closed models such as ChatGPT were not used, because they are not open-source and the code would be sent to an external service. The smaller 1.5B model was tested first but missed logic bugs, so the 7B model was chosen.
- The AI also receives the **static tool results as context**, so it focuses on **logic mistakes** the tools cannot detect. For example, `sum(numbers) / len(numbers)` looks correct, but crashes when the list is empty.

### 4. Verification and merging
The AI can make mistakes. During testing, it invented a problem that was not in the code, gave a wrong line number, and used the wrong category. To handle this:
- The AI must **quote the exact code** it refers to. If that code is not found in the file, the answer is **removed** as a hallucination.
- If the line number is off by one, it is **corrected**.
- When several tools report the same problem, the findings are **merged** into one, and the review shows which tools found it (e.g. `pylint, bandit, llm`).

```
code → preprocess (ast) → pylint + bandit → AI review (with tool results) → verifier → merge → review
```



## Why these tools and this model

- **pylint + bandit:** open-source, give JSON output, and together cover bugs, style and security. They follow fixed rules (known patterns), so they are fast and precise but cannot understand logic. Alternatives such as flake8 and ruff focus mainly on style and common errors.
- **Qwen2.5-Coder-7B-Instruct:** open-source (Apache-2.0), trained on code, follows instructions like "reply in JSON", and fits on a free Colab T4 GPU with 4-bit quantization. The smaller 1.5B model was tested first but missed logic bugs.
- Closed models like ChatGPT were not used, because the code would be sent to an external service.

## Project files

| File | Purpose |
|---|---|
| `analyzer.py` | runs pylint and bandit and returns issues in one common format |
| `code_review_assistant.ipynb` | Colab notebook: preprocessing, AI review, verification, web interface, batch mode and evaluation |
| `test.py` | small sample file with known problems |
| `requirements.txt` | list of required libraries |
| `REPORT.md` | design decisions, model selection, evaluation and limitations |
| `.gitignore` | excludes temporary and output files |

## Setup

**Static analysis only (laptop, no GPU):**
```bash
pip install -r requirements.txt
python analyzer.py
```

**Full version with AI (Google Colab):**
1. Open `code_review_assistant.ipynb` in Google Colab.
2. Select **Runtime → Change runtime type → T4 GPU**.
3. Upload `analyzer.py` using the Files panel on the left.
4. Click **Runtime → Run all** (the first model download takes about 5–10 minutes).

## Usage

**Interactive mode (web page):** run the Gradio cell and open the link it prints. Paste Python code and click **Submit**. The review shows the line, category, which tools found it, the problem and a suggested fix.

**Batch mode (CI/CD):** `review_folder("folder_name")` reviews every `.py` file in a folder, saves `review_report.md`, and prints a CI status (FAIL if security issues are found). This shows how the tool can run in a CI/CD pipeline.

**Python function:** `review(code)` returns a list of issues for any code string.

## Results

Tested on 12 labelled code snippets: 10 known issues (3 bugs including 2 logic bugs, 3 security, 3 style, 1 optimization) and 2 clean snippets. A prediction is correct if the category matches and the line is within ±1.

| Mode | Precision | Recall | F1 | Time (s) |
|---|---|---|---|---|
| static (pylint + bandit) | 0.89 | 0.80 | 0.84 | 17.9 |
| llm (AI only) | 0.73 | 0.80 | 0.76 | 74.4 |
| hybrid | 0.77 | 1.00 | 0.87 | 92.4 |

**Per category:**

| Category | Static precision | Static recall | Hybrid precision | Hybrid recall |
|---|---|---|---|---|
| bug | 1.00 | 0.33 | 0.75 | 1.00 |
| security | 0.75 | 1.00 | 0.75 | 1.00 |
| style (vs PEP 8) | 1.00 | 1.00 | 0.75 | 1.00 |
| optimization | 1.00 | 1.00 | 1.00 | 1.00 |

Static tools alone were the most precise and fastest, but found only 1 of 3 bugs (bug recall 0.33), missing logic bugs such as division by zero on an empty list. The hybrid mode found all 10 issues (recall 1.00) and had the best F1 score (0.87). Giving the static results to the AI as context improved hybrid precision from 0.71 to 0.77. The remaining 3 false positives were a bandit caution about importing `subprocess`, the AI labelling `eval` as a bug instead of security, and one weak style comment on clean code. Static analysis takes about 1.5 s per file; the hybrid takes about 7.7 s per file on a T4 GPU.

## Dependencies

All tools and models are open-source:
- pylint (GPL-2.0), run as a separate command-line tool
- bandit (Apache-2.0)
- transformers, accelerate (Apache-2.0)
- bitsandbytes (MIT), for 4-bit quantization
- torch (BSD-3-Clause)
- gradio (Apache-2.0)
- Qwen2.5-Coder-7B-Instruct model (Apache-2.0)

The model runs inside the Colab session, so code is not sent to any external AI service. (The Gradio `share=True` demo link passes through Gradio's servers; for private code, run the interface without `share`.)

## Limitations and future work

- **Small test set:** 12 snippets is enough to compare modes, but not to measure general accuracy. A larger, real-world dataset is needed.
- **Missed boundary case:** the AI did not flag `age > 18`, because whether it is a bug depends on a business rule not stated in the code.
- **Category disagreements:** the AI sometimes labels a security or style issue as a bug (e.g. `eval`), which counts as an extra finding.
- **Weak style comments:** on clean code, the AI occasionally suggests unnecessary style changes. A future improvement is to accept AI style comments only when a static tool agrees.
- **Long files:** the AI answer is limited to 500 new tokens, so very long files may get incomplete AI reviews. Future work: split long files into chunks by function.
- **Python only:** the design is extensible. A new language needs its own analyzer function (e.g. ESLint for JavaScript) returning the same issue format, while the AI, verifier and merger stay the same.

## References

- Python (ast, subprocess, json): https://docs.python.org/3/library/
- Pylint documentation: https://pylint.readthedocs.io/
- Bandit documentation: https://bandit.readthedocs.io/
- PEP 8 style guide: https://peps.python.org/pep-0008/
- Qwen2.5-Coder-7B-Instruct model: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct
- Hugging Face Transformers (pipeline, 4-bit quantization): https://huggingface.co/docs/transformers/
- Gradio documentation: https://www.gradio.app/docs
- Prompt Engineering Guide (few-shot prompting): https://www.promptingguide.ai/


## Colab File 
- Link : https://colab.research.google.com/drive/1LU3r0NPJ4q0GLkc1wuh2wRu-lcVpsxAr?usp=sharing 


