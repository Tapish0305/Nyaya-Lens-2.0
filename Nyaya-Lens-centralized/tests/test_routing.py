import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from intake import get_pipeline, initialize_case, restore_case, switch_case
from router import RouteDecision, route_query, routing_schema


def completion(payload, finish='stop'):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,
        message=SimpleNamespace(content=json.dumps(payload)))])


def fake_client(*responses):
    client = Mock()
    client.chat.completions.create.side_effect = list(responses)
    return client


@pytest.mark.parametrize('side,query', [
    ('victim', 'A truck hit me. I need help with my injuries.'),
    ('accused', 'Police accused me of hitting a bike. I deny it.'),
])
def test_router_returns_supported_two_way_route(side, query):
    client = fake_client(completion({'route': side, 'needs_clarification': False,
                                    'reason': 'Requested help', 'supporting_quotes': [query]}))
    result = route_query(query, 'dummy', client=client)
    assert result.route == side
    request = client.chat.completions.create.call_args.kwargs
    assert request['response_format']['json_schema']['strict'] is True
    assert query in request['messages'][1]['content']


def test_ambiguous_description_requests_choice_without_third_pipeline():
    client = fake_client(completion({'route': None, 'needs_clarification': True,
        'reason': 'Both injuries and allegations mentioned; help is unclear',
        'supporting_quotes': []}))
    result = route_query('I was hurt and a complaint was filed against me.', 'dummy', client=client)
    assert result.route is None and result.needs_clarification


def test_router_receives_representation_context():
    text = 'My brother is accused of hitting a motorcycle.'
    client = fake_client(completion({'route': 'accused', 'needs_clarification': False,
        'reason': 'The represented brother faces allegations', 'supporting_quotes': [text]}))
    route_query('I am explaining the accident.', 'dummy', name='Tapish', respondent_role=text, client=client)
    payload = json.loads(client.chat.completions.create.call_args.kwargs['messages'][1]['content'])
    assert payload['representation_answer'] == text


@pytest.mark.parametrize('payload', [
    {'route': 'both', 'needs_clarification': False, 'reason': 'x', 'supporting_quotes': ['x']},
    {'route': 'victim', 'needs_clarification': True, 'reason': 'x', 'supporting_quotes': ['x']},
    {'route': None, 'needs_clarification': False, 'reason': 'x', 'supporting_quotes': []},
    {'route': 'accused', 'needs_clarification': False, 'reason': 'x', 'supporting_quotes': []},
])
def test_invalid_route_decisions_rejected(payload):
    with pytest.raises(ValidationError):
        RouteDecision.model_validate(payload)


def test_invented_evidence_is_retried_not_accepted():
    bad = {'route': 'accused', 'needs_clarification': False,
           'reason': 'x', 'supporting_quotes': ['I hit them']}
    good = {'route': None, 'needs_clarification': True,
            'reason': 'Unclear', 'supporting_quotes': []}
    client = fake_client(completion(bad), completion(good))
    decision = route_query('I did not hit them.', 'dummy', client=client)
    assert decision.route is None
    assert client.chat.completions.create.call_count == 2


def test_exhausted_validation_never_defaults_to_victim():
    bad = completion({'route': 'victim', 'needs_clarification': False,
                      'reason': 'x', 'supporting_quotes': ['invented']})
    client = fake_client(bad, bad, bad)
    with pytest.raises(RuntimeError, match='3 attempts'):
        route_query('An accident happened.', 'dummy', client=client)
    assert client.chat.completions.create.call_count == 3


def test_incomplete_router_output_is_rejected():
    client = fake_client(completion({}, finish='length'))
    with pytest.raises(RuntimeError, match='incomplete'):
        route_query('I was injured.', 'dummy', client=client)


def test_router_schema_requires_every_property():
    schema = routing_schema()
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == set(schema['properties'])


@pytest.mark.parametrize('side', ['victim', 'accused'])
def test_opening_description_populates_later_fields_and_keeps_shared_answers(side):
    engine, _ = get_pipeline(side)
    text = 'A collision happened on 20 November 2022 at 1 AM.'
    class Extractor:
        def extract(self, state, text, question):
            assert state['fields']['name']['value'] == 'Rahul'
            assert question['key'] == 'narrative'
            return engine.Extraction(updates=[
                engine.Update(field='narrative', value=text, status='answered', quote=text),
                engine.Update(field='date', value='2022-11-20', status='answered', quote='20 November 2022'),
                engine.Update(field='time', value='01:00', status='answered', quote='1 AM')])
    state = initialize_case(side, 'Rahul', 'Myself', text, Extractor(), {'route': side})
    assert state['pipeline'] == side
    assert state['fields']['date']['value'] == '2022-11-20'
    assert [m['id'] for m in state['messages']] == ['m1', 'm2', 'm3']
    assert state['messages'][-1]['question']['key'] == 'narrative'
    assert engine.next_question(state)['key'] == ('represented_person' if side == 'accused' else 'location')
    assert restore_case(json.dumps(state)) == state


def test_initialization_rejection_does_not_return_partially_seeded_case():
    engine, _ = get_pipeline('victim')
    class BadExtractor:
        def extract(self, *args):
            return engine.Extraction(updates=[engine.Update(field='date',value='2022-11-20',status='answered',quote='invented')])
    with pytest.raises(ValueError):
        initialize_case('victim', 'Rahul', 'Myself', 'I was hit.', BadExtractor(), {})


def test_package_engines_do_not_share_question_banks():
    victim, _ = get_pipeline('victim')
    accused, _ = get_pipeline('accused')
    assert 'allegations' not in victim.INDEX
    assert 'allegations' in accused.INDEX
    assert victim.INDEX['injuries'].person
    assert all(not q.person for q in accused.QUESTIONS)


def test_restore_legacy_victim_and_reject_unknown_pipeline():
    engine, _ = get_pipeline('victim')
    legacy = engine.new_case()
    assert restore_case(json.dumps(legacy))['pipeline'] == 'victim'
    legacy['pipeline'] = 'both'
    with pytest.raises(ValueError):
        restore_case(json.dumps(legacy))


def test_switch_reextracts_answers_and_preserves_original_on_failure():
    victim, _ = get_pipeline('victim')
    accused, _ = get_pipeline('accused')
    state = victim.new_case()
    state['pipeline'] = 'victim'
    state['messages'] = [{'id': 'm1', 'role': 'user', 'text': 'Police accused me.', 'question': None}]
    state['incident_summary'] = 'Old summary'
    class Good:
        def extract(self, state, text, question):
            return accused.Extraction(updates=[accused.Update(field='allegations',value=text,status='answered',quote=text)])
    switched = switch_case(state, 'accused', Good())
    assert switched['id'] == state['id']
    assert switched['fields']['allegations']['value'] == 'Police accused me.'
    assert switched['incident_summary'] is None
    assert state['incident_summary'] == 'Old summary'
    assert 'allegations' not in state['fields']
    class Bad:
        def extract(self, *args):
            raise RuntimeError('Failed')
    with pytest.raises(RuntimeError):
        switch_case(state, 'accused', Bad())
    assert state['pipeline'] == 'victim'
