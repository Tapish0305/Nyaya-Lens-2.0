"""Run: python -m streamlit run app.py"""
import json
import os
import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError
from engine import INTRO, new_case, next_question, process, skip, report, load_case
from llm import GroqExtractor
from pdf_export import export_markdown_to_pdf

from pathlib import Path
load_dotenv(Path(__file__).with_name('.env'))
st.set_page_config(page_title='Nyaya Lens', page_icon='⚖️', layout='wide')
st.title('⚖️ Nyaya Lens')
st.caption('Accused-side road accident intake • structured facts for lawyer review')
if 'case' not in st.session_state or st.session_state.case.get('pipeline') != 'accused':
    st.session_state.case = new_case()
state = st.session_state.case

with st.sidebar:
    st.subheader('Case workspace')
    st.caption('This local prototype keeps case data in browser-session memory. Download JSON to save and resume. Answers and current state are sent to Groq for extraction. Do not deploy publicly with real client data without access controls.')
    consent = st.checkbox('I agree to send this intake to Groq.', key='consent')
    
    api_key_input = st.text_input(
        'Groq API Key',
        value=os.getenv('GROQ_API_KEY', ''),
        type='password',
        help='Enter your Groq API key (starts with gsk_...) or set it in .env',
    )
    api_key = api_key_input.strip() or os.getenv('GROQ_API_KEY', '').strip()
    if not api_key:
        st.warning('⚠️ Groq API key is required. Enter it above or set GROQ_API_KEY in .env.')
    
    model = st.text_input('Groq model ID', value=os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b'))
    
    st.divider()
    st.subheader('Case Exports & Reports')
    brief_md = report(state)
    brief_pdf = export_markdown_to_pdf('Nyaya Lens — Accused-Side Road Accident Intake Brief', f'Case ID: {state["id"]}', brief_md)
    st.download_button('📄 Download lawyer brief (PDF)', brief_pdf, f'nyaya-brief-{state["id"][:8]}.pdf', 'application/pdf')
    st.download_button('📝 Download lawyer brief (MD)', brief_md, f'nyaya-brief-{state["id"][:8]}.md', 'text/markdown')
    st.download_button('💾 Save case JSON', json.dumps(state, ensure_ascii=False, indent=2), f'nyaya-{state["id"]}.json', 'application/json')
    
    st.divider()
    st.subheader('AI Incident Narrative Summary')
    if st.button('✨ Generate Incident Summary (AI)', disabled=not consent or not api_key):
        try:
            extractor = GroqExtractor(api_key, model)
            with st.spinner('Generating comprehensive incident narrative summary via Groq...'):
                summary_text = extractor.generate_incident_summary(state)
                state['incident_summary'] = summary_text
                state['reviewed'] = False
                st.session_state.case = state
                st.rerun()
        except Exception as exc:
            st.error('Summary generation failed (' + type(exc).__name__ + '). Check API configuration and try again.')

    if state.get('incident_summary'):
        summary_pdf = export_markdown_to_pdf('Accused-Side Account Summary', f'Case ID: {state["id"]}', state['incident_summary'])
        st.download_button('📄 Download Incident Summary (PDF)', summary_pdf, f'nyaya-summary-{state["id"][:8]}.pdf', 'application/pdf')
        st.download_button('📝 Download Incident Summary (MD)', state['incident_summary'], f'nyaya-summary-{state["id"][:8]}.md', 'text/markdown')

    st.divider()
    uploaded = st.file_uploader('Resume saved case JSON', type=['json'])
    if st.button('Load saved case', disabled=uploaded is None):
        try:
            if uploaded.size > 2_000_000:
                raise ValueError('Case exceeds 2 MB limit')
            st.session_state.case = load_case(uploaded.getvalue())
            st.rerun()
        except (ValueError, KeyError, TypeError):
            st.error('Invalid saved case. Your existing session was preserved.')
    if st.button('Start a new case'):
        st.session_state.case = new_case()
        st.rerun()

chat, details = st.columns([3, 2])
with details:
    if state.get('incident_summary'):
        with st.expander('✨ AI Incident Narrative Summary', expanded=True):
            st.markdown(state['incident_summary'])
    with st.expander('Lawyer brief preview', expanded=not state.get('incident_summary')):
        st.text(report(state))
    with st.expander('Live JSON state', expanded=False):
        st.json(state)
    reviewed = st.checkbox('I reviewed this summary and confirm it reflects my account.', value=state['reviewed'], key=f'review-{len(state["messages"])}-{state["id"]}')
    if reviewed != state['reviewed']:
        state['reviewed'] = reviewed
        st.rerun()

with chat:
    with st.chat_message('assistant'):
        st.write(INTRO)
    for m in state['messages']:
        q = m.get('question')
        if q:
            with st.chat_message('assistant'):
                st.caption(f'Priority {q["priority"]} • {q["key"]}')
                st.write(q['text'])
        with st.chat_message('user'):
            st.write(m['text'])
    current = next_question(state)
    if state['emergency']:
        st.error('The conversation indicates a current unresolved emergency. Pause the intake and seek immediate local emergency assistance.')
        if st.button('Everyone is now safe; resume intake'):
            state['emergency'] = False
            state['messages'].append({'id': f'm{len(state["messages"])+1}', 'role': 'user', 'text': '[User confirmed current safety]', 'question': None})
            st.rerun()
    elif current:
        with st.chat_message('assistant'):
            st.caption(f'Priority {current["priority"]} • {current["key"]}')
            st.write(current['text'])
        if st.button('Skip this question', disabled=not consent):
            st.session_state.case = skip(state)
            st.rerun()
    else:
        st.success('The question bank is complete or remaining details need lawyer follow-up. You can generate your comprehensive incident summary and lawyer brief above or in the sidebar.')
    if not api_key and not state['emergency']:
        st.info('👈 Please enter your Groq API Key in the sidebar to begin the intake.')
    answer = st.chat_input('Answer naturally, or say “I don’t know”…', disabled=not consent or state['emergency'] or not api_key, max_chars=12000)
    if answer:
        if not api_key:
            st.error('Please provide a Groq API Key in the sidebar or in .env.')
        else:
            try:
                extractor = GroqExtractor(api_key, model)
                with st.spinner('Extracting supported facts and updating state…'):
                    updated = process(state, answer, extractor)
                st.session_state.case = updated
                st.rerun()
            except ValidationError as exc:
                details_err = '; '.join('.'.join(str(part) for part in error['loc']) + ': ' + error['type'] for error in exc.errors(include_input=False))
                st.error('Groq output did not match the extraction schema. ' + details_err + '. Your case was not changed.')
            except ValueError as exc:
                st.error('Extraction rejected: ' + str(exc) + '. Your case was not changed.')
            except RuntimeError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error('Unexpected extraction error (' + type(exc).__name__ + '). Your case was not changed.')
