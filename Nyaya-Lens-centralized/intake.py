"""Shared setup and pipeline dispatch, independent of the Streamlit interface."""
import datetime as dt
import json

from victim_lens import engine as victim_engine, llm as victim_llm
from accused_lens import engine as accused_engine, llm as accused_llm

OPENING_QUESTION = (
    'Please describe the whole incident, who you are seeking help for, and what help you need. '
    'Include any injuries and any complaint or allegation against that person.'
)


def get_pipeline(side):
    if side == 'victim':
        return victim_engine, victim_llm.GroqExtractor
    if side == 'accused':
        return accused_engine, accused_llm.GroqExtractor
    raise ValueError('Select victim or accused intake')


def initialize_case(side, name, respondent_role, narrative, extractor, routing):
    """Seed shared answers, then extract the incident into the selected bank atomically.

    Nothing is installed into the UI until the entire initialization succeeds. The
    narrative is recorded under its actual question, irrespective of bank priority.
    """
    engine, _ = get_pipeline(side)
    state = engine.new_case()
    state['pipeline'] = side
    shared = [
        ('name', 'What name would you like me to use?', name),
        ('respondent_role', 'Are you answering for yourself or someone else? If someone else, identify them and your relationship.', respondent_role),
    ]
    for key, question, answer in shared:
        if not answer.strip():
            raise ValueError('The shared name and representation answers are required')
        mid = f'm{len(state["messages"]) + 1}'
        state = engine.merge(state, engine.Extraction(updates=[engine.Update(
            field=key, value=answer.strip(), status='answered', quote=answer)]), mid, answer)
        state['messages'].append({'id': mid, 'role': 'user', 'text': answer,
                                  'question': {'key': key, 'person_id': None, 'priority': 0, 'text': question},
                                  'timestamp': dt.datetime.now(dt.timezone.utc).isoformat()})
    question = {'key': 'narrative', 'person_id': None,
                'priority': engine.INDEX['narrative'].priority, 'text': OPENING_QUESTION}
    result = extractor.extract(state, narrative, question)
    # The raw opening account is itself supported narrative, even if extraction
    # only returned individual facts. Avoid asking for the whole incident again.
    if not any(update.field == 'narrative' for update in result.updates):
        result = result.model_copy(update={'updates': [*result.updates, engine.Update(
            field='narrative', value=narrative, status='answered', quote=narrative)]})
    state = engine.merge(state, result, 'm3', narrative)
    state['messages'].append({'id': 'm3', 'role': 'user', 'text': narrative, 'question': question,
                              'timestamp': dt.datetime.now(dt.timezone.utc).isoformat()})
    state['routing'] = routing
    return state


def switch_case(state, side, extractor):
    """Re-extract source answers into a fresh selected bank; never copy incompatible fields.

    The caller keeps the old case if this raises. Preserve source IDs and question
    context so references remain meaningful; regenerated briefs need fresh review.
    """
    engine, _ = get_pipeline(side)
    out = engine.new_case()
    out['id'] = state['id']
    out['created_at'] = state['created_at']
    out['pipeline'] = side
    for message in state['messages']:
        text = message['text']
        # Skips/safety confirmations belong to the original workflow; retain as
        # source history but never mark a different bank's questions declined.
        if text == '[User confirmed current safety]':
            out['emergency'] = False
        if text not in {'[Skipped]', '[User confirmed current safety]'}:
            result = extractor.extract(out, text, message.get('question'))
            out = engine.merge(out, result, message['id'], text)
        out['messages'].append(dict(message))
    previous = state.get('routing', {})
    out['routing'] = {'method': 'user_switch', 'route': side, 'previous': previous}
    return out


def restore_case(raw):
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError('Saved case must be an object')
    # Older standalone victim exports have no pipeline key.
    side = payload.get('pipeline', 'victim')
    engine, _ = get_pipeline(side)
    state = engine.load_case(raw)
    state['pipeline'] = side
    return state
