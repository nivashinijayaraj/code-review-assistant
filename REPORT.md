# Code Review Assistant: Design and Evaluation Report

## 1. Goal

Build a tool that reviews Python code and finds bugs, security issues, style issues and optimization opportunities, using open-source static analysis tools together with an open-source large language model (LLM), while keeping code private and reducing false positives.

## 2. System design

```
code → pylint + bandit → LLM review (JSON) → verifier → merge duplicates → final review
```

| Component | File / cell | Role |
|---|---|---|
| Static analyzer | `analyzer.py` | runs pylint and bandit via subprocess and converts their JSON output into one common format: line, category, message, tool |
| LLM reviewer | notebook `llm_review()` | sends line-numbered code to the model with a few-shot prompt and parses the JSON answer |
| Verifier | notebook `is_real()` | rejects AI answers whose quoted evidence does not appear on the reported line (±1 line), and corrects wrong line numbers |
| Merger | notebook `review()` | combines issues with the same line and category and records which tools found each one |
| Interface | notebook Gradio cell | web page: paste code, get the review |

**Why a hybrid design:** static tools are fast and precise but only detect known patterns. The LLM can reason about logic (for example, division by zero on an empty list) but can hallucinate. Combining them, with a verification step, uses the strengths of both.

**Category mapping:** pylint's message types are mapped to the four categories (error/warning → bug, convention → style, refactor → optimization). `eval`/`exec` are mapped to security, and unused imports/variables to style. Docstring and final-newline checks are disabled because they are noise for short snippets.

## 3. Model selection

| Model | Result in testing |
|---|---|
| Qwen2.5-Coder-1.5B-Instruct | fast to load (about 2 minutes); found pattern issues (eval, mutable default, unused import) but missed logic bugs |
| **Qwen2.5-Coder-7B-Instruct (4-bit)** | found the division-by-zero logic bug; followed the JSON format more reliably |

The 7B model was chosen because it is code-specialised, Apache-2.0 licensed, and fits on a free Colab T4 GPU when loaded with 4-bit quantization (bitsandbytes), which reduces memory from about 15 GB to about 5.5 GB.

## 4. Prompt engineering

Changes were made step by step, based on test results:

| Version | Problem observed | Change |
|---|---|---|
| 1. Free-text review | answer was a paragraph; no line numbers; invented a naming issue | asked for JSON only, and added line numbers to the code |
| 2. Strict "do not invent problems" | model returned an empty list `[]` | removed the over-strict wording |
| 3. Few-shot example | found all 3 issues in the test code | added one example input and output using different code |
| 4. Logic-bug example | logic bugs were still missed | added a logic-bug example and an instruction to think about edge cases (empty lists, zero, boundaries) |

Greedy decoding (`do_sample=False`) is used so results are repeatable.

## 5. Handling unreliable AI output

- **Messy JSON:** the answer is cut from the first `[` to the last `]`; if parsing fails, an empty list is returned instead of crashing.
- **Invented categories:** categories outside bug, security, style and optimization are mapped to bug.
- **Hallucinations:** each answer must include the exact code as evidence. If that code is not in the file, the answer is rejected. A test with a deliberately fake answer confirmed it is rejected, while a real one is kept.
- **Verifier bug found during testing:** the first version compared text exactly and wrongly rejected a correct answer (`items = []` vs `items=[]`). It was fixed by ignoring spaces and allowing ±1 line, because LLMs often miscount lines.

## 6. Evaluation

**Dataset:** 12 labelled snippets: 4 bugs (2 of them logic bugs), 3 security issues, 3 style issues, 1 optimization issue, and 2 clean snippets. A prediction counts as correct if the category matches and the line is within ±1.

| Mode | Precision | Recall | F1 | TP | FP | FN | Time (s) |
|---|---|---|---|---|---|---|---|
| static | 0.89 | 0.80 | 0.84 | 8 | 1 | 2 | 29.8 |
| llm | 0.73 | 0.80 | 0.76 | 8 | 3 | 2 | 78.3 |
| hybrid | 0.71 | 1.00 | 0.83 | 10 | 4 | 0 | 85.7 |

**Findings:**
- Static tools were the most precise and fastest, but missed the logic bugs.
- The hybrid system found all 10 known issues (100% recall).
- Latency: about 2.5 s per snippet for static analysis vs about 7 s with the LLM on a T4 GPU.

**Error analysis:** most false positives were category disagreements, such as the AI labelling `== None` or `eval` as a bug while the answer key had style or security. One was a weak style comment on clean code.

## 7. Limitations

- The test set is small (12 snippets) and written by one person.
- The `age > 18` case was not flagged; whether it is a bug depends on an unstated business rule.
- Only single-file Python code is supported.
- The Gradio `share=True` link passes through Gradio's servers; for private code the interface should run locally.

## 8. Future improvements

- A larger, real-world test set, with more than one person labelling it.
- Accept AI style comments only when a static tool agrees, to reduce weak suggestions.
- Support for more languages (e.g. ESLint for JavaScript).
- Collect user feedback (helpful / not helpful) to tune the prompt.
- Review only the changed lines in pull requests, for CI/CD integration.

## 9. AI assistance

Claude (an AI assistant) was used for learning, explanations and debugging during development. All tests and evaluations were run and checked by me.