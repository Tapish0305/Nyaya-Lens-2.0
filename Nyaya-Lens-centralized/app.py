"""Central Nyaya Lens app. Run from repository root: python -m streamlit run app.py"""
import hashlib
import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from intake import OPENING_QUESTION, get_pipeline, initialize_case, restore_case, switch_case
from router import CLARIFICATION, route_query
from victim_lens.pdf_export import export_markdown_to_pdf

load_dotenv(Path(__file__).with_name('.env'))
st.set_page_config(page_title='Nyaya Lens', page_icon='⚖️', layout='wide')
st.title('⚖️ Nyaya Lens')
st.caption('Road accident intake • your account, organized for lawyer review')


def fresh_intake():
    return {'stage': 'name', 'name': '', 'respondent_role': '', 'narrative': '', 'decision': None}


def reset():
    st.session_state.pop('case', None)
    st.session_state.intake = fresh_intake()


if 'intake' not in st.session_state:
    st.session_state.intake = fresh_intake()

with st.sidebar:
    st.subheader('Case workspace')
    st.caption('Answers and relevant case facts are sent to Groq. Download JSON to save your case; browser sessions are temporary.')
    consent = st.checkbox('I agree to send this intake to Groq.', key='central_consent')
    api_key = st.text_input('Groq API Key', value=os.getenv('GROQ_API_KEY', ''),
                            type='password', key='central_api_key').strip()
    model = st.text_input('Groq model ID', value=os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b'),
                          key='central_model').strip()
    ready = consent and bool(api_key) and bool(model)
    if not api_key:
        st.info('Enter your Groq API key to begin.')
    uploaded = st.file_uploader('Resume saved case JSON', type=['json'], key='central_upload')
    if st.button('Load saved case', disabled=uploaded is None):
        try:
            if uploaded.size > 2_000_000:
                raise ValueError('File too large')
            restored = restore_case(uploaded.getvalue())
            st.session_state.case = restored
            st.rerun()
        except (ValueError, KeyError, TypeError, AttributeError):
            st.error('Invalid saved case. The current session was preserved.')
    if st.button('Start a new case'):
        reset()
        st.rerun()


def activate(side, method, decision=None):
    intake = st.session_state.intake
    _, extractor_type = get_pipeline(side)
    metadata = {'method': method, 'route': side,
                'decision': decision.model_dump() if decision else intake['decision']}
    with st.spinner('Organizing your description and preparing the next question…'):
        case = initialize_case(side, intake['name'], intake['respondent_role'], intake['narrative'],
                               extractor_type(api_key, model), metadata)
    st.session_state.case = case
    st.rerun()


def classify_and_activate():
    intake = st.session_state.intake
    with st.spinner('Identifying which intake fits your request…'):
        decision = route_query(intake['narrative'], api_key, model,
                               name=intake['name'], respondent_role=intake['respondent_role'])
    intake['decision'] = decision.model_dump()
    if decision.route:
        activate(decision.route, 'llm', decision)
    st.rerun()


def show_error(action, exc=None):
    # Do not render exception bodies, keys or client answers in the UI or logs.
    diagnostic = ''
    if exc is not None:
        status_code = getattr(exc, 'status_code', None)
        diagnostic = f' (Groq HTTP {status_code})' if status_code is not None else f' ({type(exc).__name__})'
    st.error(f'{action} could not complete{diagnostic}. Check your API key, model and connection, then retry. Your current answers are preserved.')


if 'case' not in st.session_state:
    intake = st.session_state.intake
    st.write('Hello, I’m Nyaya Lens. I’ll ask about the incident, then continue with the questions that fit the help you need. You can correct details or skip questions during the intake. This organizes facts for a lawyer; it does not decide fault.')
    shared_questions = {
        'name': 'What name would you like me to use?',
        'respondent_role': 'Are you answering for yourself or someone else? If someone else, identify them and your relationship.',
        'narrative': OPENING_QUESTION,
    }
    for key, question in shared_questions.items():
        if intake[key]:
            with st.chat_message('assistant'):
                st.write(question)
            with st.chat_message('user'):
                st.write(intake[key])
    if intake['stage'] in shared_questions:
        with st.chat_message('assistant'):
            st.write(shared_questions[intake['stage']])
        answer = st.chat_input('Answer naturally…', disabled=not ready, max_chars=12000, key='shared_answer')
        if answer and answer.strip():
            stage = intake['stage']
            intake[stage] = answer.strip()
            intake['stage'] = {'name': 'respondent_role', 'respondent_role': 'narrative', 'narrative': 'route'}[stage]
            if stage == 'narrative':
                try:
                    classify_and_activate()
                except Exception:
                    show_error('Routing or incident extraction')
            else:
                st.rerun()
    if intake['stage'] == 'route':
        decision = intake['decision']
        if decision and decision['route']:
            st.info(f'The description fits {decision["route"]}-side intake. Continue to organize the incident, or choose the other side below.')
            if st.button('Continue with selected intake', disabled=not ready):
                try:
                    activate(decision['route'], 'llm')
                except Exception:
                    show_error('Incident extraction')
        elif decision:
            with st.chat_message('assistant'):
                st.write(CLARIFICATION)
        else:
            st.info('Your description is saved in this session. Retry routing or select the help you need below.')
            if st.button('Retry automatic routing', disabled=not ready):
                try:
                    classify_and_activate()
                except Exception:
                    show_error('Routing or incident extraction')
        left, right = st.columns(2)
        with left:
            victim = st.button('Help with injuries / losses (victim)', disabled=not ready, use_container_width=True)
        with right:
            accused = st.button('Help with allegation against me (accused)', disabled=not ready, use_container_width=True)
        if victim or accused:
            try:
                activate('victim' if victim else 'accused', 'user_choice')
            except Exception:
                show_error('Incident extraction')
        if st.button('Edit incident description'):
            intake['narrative'] = ''
            intake['decision'] = None
            intake['stage'] = 'narrative'
            st.rerun()
    st.stop()

state = st.session_state.case
side = state['pipeline']
engine, extractor_type = get_pipeline(side)
st.caption(f'Current intake: {side.capitalize()} side')

with st.sidebar:
    st.divider()
    st.subheader('Intake side')
    st.caption('If the selected side does not fit, switch it. Existing answers will be reprocessed for that intake.')
    other = 'accused' if side == 'victim' else 'victim'
    if st.button(f'Switch to {other} intake', disabled=not ready or state['emergency']):
        try:
            with st.spinner('Reorganizing your answers for the selected intake…'):
                switched = switch_case(state, other, get_pipeline(other)[1](api_key, model))
            st.session_state.case = switched
            st.rerun()
        except Exception:
            show_error('Switching intake')
    st.divider()
    st.subheader('Reports and exports')
    brief = engine.report(state)
    st.download_button('Save case JSON', json.dumps(state, ensure_ascii=False, indent=2),
                       f'nyaya-{side}-{state["id"]}.json', 'application/json')
    st.download_button('Download lawyer brief (MD)', brief, f'nyaya-{side}-brief.md', 'text/markdown')
    st.download_button('Download lawyer brief (PDF)', export_markdown_to_pdf(
        f'Nyaya Lens — {side.capitalize()}-side intake brief', f'Case ID: {state["id"]}', brief),
        f'nyaya-{side}-brief.pdf', 'application/pdf')
    if st.button('Generate account summary (AI)', disabled=not ready or state['emergency']):
        try:
            with st.spinner('Preparing the account summary…'):
                summary = extractor_type(api_key, model).generate_incident_summary(state)
            state['incident_summary'] = summary
            state['reviewed'] = False
            st.rerun()
        except Exception as exc:
            show_error('Summary generation', exc)
    if state.get('incident_summary'):
        st.download_button('Download account summary (MD)', state['incident_summary'],
                           f'nyaya-{side}-summary.md', 'text/markdown')
        st.download_button('Download account summary (PDF)', export_markdown_to_pdf(
            f'{side.capitalize()}-side account summary', f'Case ID: {state["id"]}', state['incident_summary']),
            f'nyaya-{side}-summary.pdf', 'application/pdf')

chat, details = st.columns([3, 2])
with details:
    if state.get('incident_summary'):
        with st.expander('Account summary', expanded=True):
            st.markdown(state['incident_summary'])
    with st.expander('Lawyer brief', expanded=not state.get('incident_summary')):
        st.text(engine.report(state))
    with st.expander('Case facts and sources'):
        st.json(state)
    fingerprint = hashlib.sha256((engine.report({**state, 'reviewed': False}) + str(state.get('incident_summary'))).encode()).hexdigest()[:16]
    reviewed = st.checkbox('I reviewed the summary and confirm it reflects my account.',
                           value=state['reviewed'], key=f'central_review_{state["id"]}_{side}_{fingerprint}')
    if reviewed != state['reviewed']:
        state['reviewed'] = reviewed
        st.rerun()

with chat:
    for message in state['messages']:
        if message.get('question'):
            with st.chat_message('assistant'):
                st.write(message['question']['text'])
        with st.chat_message('user'):
            st.write(message['text'])
    if state['emergency']:
        st.error('Your account indicates a current unresolved emergency. Pause the intake and seek immediate local emergency assistance.')
        if st.button('Everyone is now safe; resume intake'):
            state['emergency'] = False
            state['reviewed'] = False
            state['incident_summary'] = None
            state['messages'].append({'id': f'm{len(state["messages"])+1}', 'role': 'user',
                                      'text': '[User confirmed current safety]', 'question': None})
            st.rerun()
    else:
        question = engine.next_question(state)
        if question:
            with st.chat_message('assistant'):
                st.write(question['text'])
            if st.button('Skip this question', disabled=not consent):
                st.session_state.case = engine.skip(state)
                st.rerun()
        else:
            st.success('The intake is complete or remaining details need lawyer follow-up. Review your brief; you can still add or correct facts below.')
    answer = st.chat_input('Answer naturally, add details, or correct an earlier answer…',
                           disabled=not ready or state['emergency'], max_chars=12000, key='pipeline_answer')
    if answer and answer.strip():
        try:
            with st.spinner('Organizing the facts from your answer…'):
                updated = engine.process(state, answer, extractor_type(api_key, model))
            st.session_state.case = updated
            st.rerun()
        except Exception:
            show_error('Fact extraction')
