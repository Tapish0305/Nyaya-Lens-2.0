# Centralized intake validation

Base repository: `Tapish0305/Nyaya-Lens-2.0`, commit
`8769f53532868e31d75d2a20744b948f535f17bb`.

## Checks performed

- Python compilation passed for root code and both pipeline packages.
- 25 central tests passed (router schema/evidence validation, ambiguous two-way
  selection, third-party context, opening extraction, pipeline separation,
  restore, atomic rejection, side switching and Streamlit interactions).
- 21 existing victim tests passed.
- 12 existing accused tests passed.
- Total: **58 passing tests**.
- Streamlit AppTest exercised consent/key gating, shared opening questions,
  automatic victim and accused routing, follow-up chat, summary generation,
  summary invalidation on skip, new-case reset, explicit choice after ambiguity,
  extraction failure/retry, routing error recovery, emergency pause/resume and
  switching sides in one interface.
- Both pipelines remain importable simultaneously as distinct packages and
  runnable with their original standalone imports.
- Archive excludes `.env`, `.git`, virtual environments and caches; configuration
  examples contain only placeholders.

## Limits of validation

Router and Groq extraction outputs were mocked in offline tests. No live Groq
request was made and no model classification accuracy measurement is claimed.
Evaluate real victim/accused narratives, mixed-role descriptions, negations,
third-party representation and Hindi/Hinglish on your account before relying on
routing quality. Existing intake and PDF limitations remain as documented.
