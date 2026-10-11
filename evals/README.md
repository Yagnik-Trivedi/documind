# evals/

How we prove DocuMind's answers are good, with numbers.

## Golden set: `golden.jsonl` (one JSON object per line)
Copy the format from `golden.template.jsonl`. Fields:
| Field | Meaning |
|---|---|
| `id` | short unique id (`q001`) |
| `question` | as a real user would ask it, in `lang` |
| `lang` | `en`, `hi` or `gu` |
| `type` | `single` (one fact), `multi` (needs 2+ passages), `unanswerable` (not in corpus), `paraphrase` (no shared keywords with the source) |
| `answer` | the correct answer in one or two sentences (empty for unanswerable) |
| `relevant` | list of `{"filename": "...", "page": N}` where the answer is found |

Target mix for 50 questions: 30 single, 10 multi, 5 unanswerable, 5 paraphrase. Include at least 8 Hindi/Gujarati questions.

**How to write good questions:** open a PDF, pick a fact (income limit, deadline, documents required,
benefit amount), and write the question the way a student or farmer would phrase it, *without*
copying the PDF's exact words for the paraphrase type.

## Metrics
| Metric | Measures | Needs LLM? |
|---|---|---|
| Recall@5 | is a relevant page in the top 5 retrieved chunks | no |
| MRR | how high the first relevant chunk ranks | no |
| Faithfulness | are the answer's claims supported by the retrieved context | judge |
| Answer relevancy | does the answer address the question | judge |
| Unanswerable accuracy | says "not found" for unanswerable questions | no |
| Phantom citations | `[n]` markers pointing at nothing | no |
| TTFT / latency | time to first token, total | no |

Results go to `results.md` (one row per run) and the `eval_runs` table. The runner (`run_eval.py`) is built in Phase 2 (see docs/PROMPTS.md 2.1).
