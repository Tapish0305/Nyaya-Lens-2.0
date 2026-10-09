# Nyaya Lens — centralized victim / accused intake

One Streamlit app asks shared opening questions, uses Groq to choose **victim** or
**accused** intake, then continues with that side's existing question bank.
Routing selects the person's intake need; it does not determine legal fault.

## Run on Windows

Open a terminal in the extracted project folder (the folder containing this README
and the root `app.py`), then:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Set `GROQ_API_KEY` in `.env`, or enter your key in the app sidebar. Keep `.env`
local. The default model is `openai/gpt-oss-120b`; choose a model supporting strict
JSON-schema responses and available to your Groq account. Tick the consent box.
No real API key is included in this package.

On macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with your key
.venv/bin/python -m streamlit run app.py
```

Use the **root app.py** for centralized intake. Both standalone apps remain
runnable from their own folders using their original instructions.

## How it works

1. Ask the name to use.
2. Ask whether the speaker represents themselves or someone else, and whom.
3. Ask for the whole incident and the help requested.
4. `route_query()` in `router.py` classifies the account using Groq and strict JSON.
5. If the account does not clearly select a side, the same UI offers two buttons:
   help with injuries/losses (**victim**) or help with an allegation against the
   represented person (**accused**). There is no third pipeline.
6. Seed the name and representation answers with source messages; extract the
   opening incident directly into the selected bank. Keep the raw opening account
   as narrative if the extractor omitted that field.
7. Python selects the next applicable unanswered question, skipping fields already
   supplied in the opening account.

Victim intake collects per-person injury/treatment/financial information. Accused
intake distinguishes allegations from the represented client's account and asks
about police contact, notices, disputed evidence and proceedings.

The router receives the opening account and representation answers. It requires
verbatim supporting quotes, validates its decision, and attempts up to three
responses if output validation fails. Invalid output or API errors do not silently
choose a side. Quotes and schemas do not prove the semantic classification is
correct; the user can override the route.

## Router function

```python
from router import route_query

decision = route_query(
    "Police allege that my car hit a bike. I dispute this and need help responding.",
    api_key="your-local-key",
    name="Rahul",
    respondent_role="I am answering for myself",
)

if decision.needs_clarification:
    # Ask the user to choose victim or accused.
    pass
else:
    print(decision.route)  # 'victim' or 'accused'
```

A `null` route is a request for clarification, not a third intake type. Responses
include `route`, `needs_clarification`, `reason`, and `supporting_quotes`.

## Case controls

- Continue either intake in the same chat interface.
- Skip questions, correct facts, inspect state and review source-linked briefs.
- Export JSON, Markdown and PDF; generate an optional AI account summary.
- Restore a saved case into its own pipeline. Legacy victim JSON exports without
  a `pipeline` key are supported.
- Switch sides through the sidebar. All original user answers are re-extracted
  into the new bank rather than copying incompatible fields. This makes one
  extraction call per original answer and can take time on long cases. A failed
  switch preserves the previous case; switching clears generated summaries and
  review confirmation.
- Pause for an emergency flagged by extraction and resume after a safety
  confirmation. This is not reliable emergency triage.

The central app stores routing metadata alongside `pipeline` in case JSON. API
keys are never stored in that state. Router decisions are not rerun for every
answer; the user can switch the intake if their help request changes.

## Files and integration

| File | Role |
|---|---|
| `app.py` | Central Streamlit interface |
| `router.py` | LLM routing function and validated two-way decision schema |
| `intake.py` | Pipeline dispatch, shared-answer seeding, restore and side switching |
| `victim_lens/` | Victim bank, state engine, extractor and exports |
| `accused_lens/` | Accused bank, state engine, extractor and exports |
| `tests/` | Router, integration and Streamlit interaction tests |

Both packages now support relative imports when used centrally and original
imports when launched standalone. Victim-side new answers/skips also clear stale
AI summaries, and plaintext answer logging was removed. Configuration examples
contain placeholders.

To integrate into an existing clone, copy the root files and updated pipeline
folders from this package. Preserve your own local `.env`. This package is based
on repository commit `8769f53532868e31d75d2a20744b948f535f17bb`.

## Tests

Run these from the root folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q -c victim_lens/pytest.ini victim_lens/tests
.\.venv\Scripts\python.exe -m pytest -q -c accused_lens/pytest.ini accused_lens/tests
```

Alternatively run each pipeline's tests from its own folder, as documented in its
README. See `VALIDATION.md` for checks actually performed.

## Prototype limits

No login, database, document OCR or legal research is added. Cases remain in
Streamlit session memory until you download JSON. Exports contain the submitted
case details. PDF export uses the existing ReportLab exporter and its fonts have
limited Hindi coverage. No live Groq call was made during implementation;
classification quality on real narratives and Hindi/Hinglish needs evaluation
with your own account. The existing field validators and summary prompts are
retained apart from the integration changes described above.
