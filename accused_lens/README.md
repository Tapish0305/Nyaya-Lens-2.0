# Nyaya Lens — Accused-side road accident intake

Standalone accused-side version adapted from your uploaded app, engine, question bank, Groq adapter and PDF exporter. The victim-side files are unchanged. There is no classification or routing layer yet.

## Windows setup

Extract the ZIP and open PowerShell inside `accused_lens`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Put your current Groq key into `.env`, or enter it in the app's password field. Model: `openai/gpt-oss-120b`. This package contains no API key. Consent and an API key are required before submitting answers. If running alongside the victim app, add `--server.port 8502`.

## Question priorities

0. Name, respondent relationship and represented client.
1. Allegations, sources, police contact, notices and current procedural situation.
2. Client's account, date, time, location, people, vehicles and collision circumstances.
3. Client's driving and post-collision actions, injuries and vehicle records.
4. Agreements/disputes and available or conflicting evidence.
5. FIR, police records, statements and proceedings.
6. Insurance, financial impact, payments, documents and requested lawyer help.

Any answer can populate any supported field. Python selects the next applicable unanswered question. A person responding for someone else is distinct from the client seeking representation. Question wording uses 'you' after establishing this context; answer from the represented person's perspective and state the source if you did not witness it.

Driver-specific questions depend on `client_driving=true`. Medical information and financial impact are collected as case-level summaries relevant to the represented client, rather than asking full medical and employment questions for every registered individual. People still have stable IDs, with labels and source message IDs. Shared incident field names such as `date`, `time`, `location`, `narrative`, `fir_number` and `insurance_claim` are retained for the future routing layer.

## Reports and safeguards

- Deterministic source-linked lawyer brief with PDF, Markdown and JSON exports.
- Optional Groq-generated account summary for this client's own lawyer. The prompt separates allegations, the client's account and disputed facts; requires source attribution; and avoids findings of guilt or legal strategy.
- Source quotes, unknown/declined/partial/conflicting states, correction history and transactional merging.
- Up to three extraction attempts when validation fails, with the same validation on each attempt.
- Exact or case-insensitive quote matching. Fuzzy paraphrase matching was removed because similar wording can change a negation or meaning. Similar person names alone no longer cause automatic merging.
- New answers and skips invalidate the generated summary and review confirmation.
- Saved cases contain `pipeline: accused`; this app rejects victim-side JSON rather than silently converting it.
- No automatic plaintext terminal logging of client answers.

## Try this sample

First provide your name and who you represent. Then answer an allegation question with:

> Police contacted me yesterday about an allegation that my car hit a motorcycle on 20 November 2022 at around 1 AM near Kashmiri Gate, Delhi. I was driving, but I dispute that I struck the motorcycle. I stopped and called an ambulance. I have dashcam footage. I have not received a notice and do not know whether an FIR exists.

Check the live state: date and time should be filled, allegations should remain attributed to police, contact should not automatically establish an FIR, and denial should not become an admission. Extraction depends on model output and requires review. Try explicit corrections, unknown answers and save/resume.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

12 offline tests passed, plus a Streamlit startup/consent/key interaction check. No live Groq call was performed.

## Limits

Local development app: no login, database, document OCR, legal research or lawyer sharing. Session state can be lost on disconnect; periodically download JSON. Exports contain client information in plaintext. Generated summaries require review; JSON shape and source matching do not prove factual correctness. PDFs retain your supplied ReportLab exporter, whose default Helvetica font has limited coverage for Hindi and other non-Latin scripts.

Allegations are stored as attributed text, not a full multi-source allegation graph. Anonymous helpers remain group descriptions rather than invented individuals. Explicit alias resolution may need clarification. This version collects facts for lawyer review and does not advise on statutory provisions, filing deadlines, guilt or defence strategy.
