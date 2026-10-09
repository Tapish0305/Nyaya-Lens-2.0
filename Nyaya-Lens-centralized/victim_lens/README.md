# Nyaya Lens — Groq road accident intake chatbot

A runnable local Python/Streamlit prototype implementing the agreed state-based design. Groq extracts facts from every answer against the whole question bank. Python validates and merges updates, then picks the next applicable unanswered question by priority. There is no autonomous multi-agent framework.

## Setup (Windows PowerShell)

Use Python 3.11 or 3.12. Extract this ZIP, open a terminal inside `nyaya_lens`, then run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Replace `replace_with_your_new_api_key` with your Groq API key. Keep the key local; do not paste it into the chat or commit `.env`. Set `GROQ_MODEL` to a structured-output-capable model available to your account. The starter model is `openai/gpt-oss-120b`; availability must be checked with your own key.

Run the app without activating PowerShell scripts:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local address shown in the terminal (usually `http://localhost:8501`). Agree to send the intake to Groq in the sidebar, then answer the chat. No API key goes into exported cases.

On macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with your key
.venv/bin/python -m streamlit run app.py
```

## What is included

- Introductory questions and Priorities 1–6, with conditional follow-ups.
- Whole-schema extraction from every response, including later-priority facts.
- Separate injured-person records with stable IDs.
- Unknown, declined, partial, answered, not applicable and conflicting states.
- Exact supporting message quotes for extraction updates.
- Transactional validation: a rejected extraction cannot partially mutate state.
- Conflict preservation and explicit correction history.
- Two unsuccessful clarification attempts before an unresolved field is deferred to lawyer review.
- Current-emergency pause with explicit safety confirmation to resume.
- Live JSON view, JSON save/resume, editable-through-chat facts, review confirmation and an attributed Markdown lawyer brief.
- Offline engine tests; no API key is needed to run these tests.

The report is deterministic and lists facts, status, person and source message. It does not use another LLM to embellish the account or assert legal liability. It is a structured intake brief, not legal analysis.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit chat interface and exports |
| `questions.py` | Question text, priority, field type and branching |
| `engine.py` | State, validation, transactional merging, scheduling, report |
| `llm.py` | Prompt, JSON schema, REST request and bounded retry handling |
| `tests/test_engine.py` | Core workflow regression tests |
| `.env.example` | API configuration template |

## Groq API configuration

The adapter uses the official `groq` Python SDK with `openai/gpt-oss-120b` and strict JSON-schema output. Set `GROQ_API_KEY` and optionally `GROQ_MODEL` in `.env`. All object fields are required in the request schema, and extra properties are forbidden. Pydantic validation and transactional state merging still run locally.

Official reference: https://console.groq.com/docs/structured-outputs

## Quick manual check

1. Answer the name question with:
   `I'm Rahul. On 26 August 2026 at about 1 AM a truck hit my bike near ISBT Kashmiri Gate, Delhi. My wife was with me. We were both admitted to AIIMS Delhi. The truck number was UP94S0836. I don't know of any witnesses.`
2. Inspect the live state. Expect several fields across priorities to populate, two person records, and witnesses marked unknown rather than false. Groq extraction can vary; inspect the actual result.
3. The bot should ask the earliest missing field, not ask the full accident date again.
4. Try `Actually, I meant 1 PM, not 1 AM.` The time should change with preserved history.
5. Give a conflicting time without saying it is a correction. It should be flagged for clarification.
6. Answer `I don't know` to the current question. It should move on.
7. Download case JSON, start a new case, and load the JSON to resume.
8. Review the brief and confirm the summary. Download the updated brief.

Run offline checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Scope and implementation limits

This is a local development prototype. It has no document upload/OCR, legal research, authentication, database, production access controls or automated case sharing. Browser refresh/disconnect can lose session state: download JSON periodically to persist work. JSON and Markdown exports contain sensitive case details in plaintext.

Question wording is English; Groq is instructed to extract from natural language, but Hindi/Hinglish handling should be evaluated with your own samples. Dates use an India-local clock for relative terms. Time preserves approximate status as text; unsupported precision must not be invented.

Structured outputs enforce JSON shape, not factual truth. Exact quote checks and field validation reduce errors but do not prove semantic correctness. The user and lawyer must review populated facts. New people are resolved by the extractor; deliberately test aliases and pronouns. Admission history is represented as one summary field per person, not a full sequence of hospital episodes.

Negative or unknown prerequisite answers skip dependent questions; the underlying child fields remain unanswered and the report identifies them as conditional questions not asked. Skipped fields can still be updated by a later explicit statement. Explicit edits reset summary-review confirmation.

Medical emergencies are detected by the extractor and are not a dependable emergency triage service. The flow assumes safety at the beginning, as requested. Death/dependant-specific intake is outside this injury-focused prototype.

No live Groq request was tested in the build environment because no live API call was made with the exposed key. Dependency installation and offline tests are recorded in `VALIDATION.md`.
