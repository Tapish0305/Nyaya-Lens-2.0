import copy
import json
import pytest
from engine import new_case, merge, Extraction, Update, NewPerson, next_question, process, skip, report, load_case

def update(field, value, quote, pid=None, status='answered', correction=False):
    return Update(field=field, value=value, status=status, quote=quote, person_id=pid, correction=correction)

def test_multi_field_skips_later_priority():
    s = new_case()
    text = 'Rahul, 26 August 2026, 1 AM. No witnesses.'
    s = merge(s, Extraction(updates=[update('name','Rahul','Rahul'), update('date','2026-08-26','26 August 2026'), update('time','01:00','1 AM'), update('witnesses_known',False,'No witnesses')]), 'm1', text)
    assert s['fields']['date']['status'] == 'answered'
    assert s['fields']['witnesses_known']['value'] is False
    assert next_question(s)['key'] == 'respondent_role'

def test_unknown_is_answered_not_false():
    s = merge(new_case(), Extraction(updates=[update('name',None,"I don't know",status='unknown')]), 'm1', "I don't know")
    assert next_question(s)['key'] == 'respondent_role'
    assert s['fields']['name']['value'] is None

def test_date_without_year_stays_partial():
    s = merge(new_case(), Extraction(updates=[update('date','26 August','26 August')]), 'm1','26 August')
    assert s['fields']['date']['status'] == 'partial'

def test_person_records_and_conditional_questions():
    s = merge(new_case(), Extraction(people=[NewPerson(id='p1',label='self',quote='I'), NewPerson(id='p2',label='wife',quote='wife')], updates=[update('hospitalized',False,'not admitted','p1'), update('hospitalized',True,'wife admitted','p2')]), 'm1','I was not admitted; wife admitted')
    from engine import applicable
    from questions import INDEX
    assert not applicable(s,INDEX['admission_status'],'p1')
    assert applicable(s,INDEX['admission_status'],'p2')
    assert s['people']['p1']['fields']['hospital']['status'] == 'unanswered'

def test_conflict_and_explicit_correction_keep_history():
    s = merge(new_case(),Extraction(updates=[update('time','01:00','1 AM')]),'m1','1 AM')
    s = merge(s,Extraction(updates=[update('time','13:00','1 PM')]),'m2','1 PM')
    assert s['fields']['time']['status'] == 'conflicting'
    assert s['fields']['time']['value'] == '01:00'
    s = merge(s,Extraction(updates=[update('time','13:00','I meant 1 PM',correction=True)]),'m3','I meant 1 PM')
    assert s['fields']['time']['status'] == 'answered'
    assert len(s['fields']['time']['history']) == 3

def test_transactional_rejection():
    s = new_case()
    original = copy.deepcopy(s)
    with pytest.raises(ValueError):
        merge(s,Extraction(updates=[update('name','Rahul','Rahul'), update('time','01:00','made up')]),'m1','Rahul')
    assert s == original

def test_empty_and_false_quote_rejected():
    with pytest.raises(ValueError):
        merge(new_case(),Extraction(updates=[update('name','Rahul','')]),'m1','Rahul')

def test_boolean_not_string():
    with pytest.raises(ValueError):
        merge(new_case(),Extraction(updates=[update('police_reported','yes','yes')]),'m1','yes')

def test_bounded_clarification():
    class EmptyExtractor:
        def extract(self,*args): return Extraction()
    s = process(new_case(),'hello',EmptyExtractor())
    s = process(s,'hello again',EmptyExtractor())
    assert next_question(s)['key'] == 'respondent_role'
    assert s['fields']['name']['status'] == 'unanswered'

def test_skip_and_round_trip_and_report():
    s = skip(new_case())
    assert next_question(s)['key'] == 'respondent_role'
    assert load_case(json.dumps(s)) == s
    assert 'declined' in report(s)
    assert 'm1' in report(s)

def test_unknown_does_not_erase_fact():
    s = merge(new_case(),Extraction(updates=[update('time','01:00','1 AM')]),'m1','1 AM')
    s = merge(s,Extraction(updates=[update('time',None,'not sure',status='unknown')]),'m2','not sure')
    assert s['fields']['time']['value'] == '01:00'

def test_emergency_pauses_questions():
    s = merge(new_case(),Extraction(emergency=True,emergency_quote='bleeding now'),'m1','bleeding now')
    assert next_question(s) is None

def test_invalid_calendar_date_rejected():
    with pytest.raises(ValueError):
        merge(new_case(),Extraction(updates=[update('date','2026-02-30','30 Feb 2026')]),'m1','30 Feb 2026')

def test_re_registering_existing_person_does_not_raise_error():
    s = merge(new_case(), Extraction(people=[NewPerson(id='p1', label='girlfriend', quote='girlfriend')],
                                     updates=[update('hospitalized', True, 'girlfriend hospitalized', 'p1')]),
              'm1', 'girlfriend hospitalized')
    assert 'p1' in s['people']
    assert s['people']['p1']['fields']['hospitalized']['value'] is True

    # Next turn: LLM re-includes p1, even with no quote or repeated quote
    s = merge(s, Extraction(people=[NewPerson(id='p1', label='girlfriend', quote='girlfriend')],
                            updates=[update('hospital', 'City Hospital', 'City Hospital', 'p1')]),
              'm2', 'City Hospital')
    assert s['people']['p1']['fields']['hospitalized']['value'] is True
    assert s['people']['p1']['fields']['hospital']['value'] == 'City Hospital'

def test_person_id_collision_allocates_next_id():
    s = merge(new_case(), Extraction(people=[NewPerson(id='p1', label='girlfriend', quote='girlfriend')]),
              'm1', 'girlfriend')
    # LLM mistakenly sends p1 for a different new person (driver)
    s = merge(s, Extraction(people=[NewPerson(id='p1', label='driver', quote='driver')],
                            updates=[update('hospitalized', False, 'driver uninjured', 'p1')]),
              'm2', 'driver uninjured')
    assert 'p1' in s['people']
    assert s['people']['p1']['label'] == 'girlfriend'
    assert 'p2' in s['people']
    assert s['people']['p2']['label'] == 'driver'
    assert s['people']['p2']['fields']['hospitalized']['value'] is False

def test_duplicate_person_under_new_id_remapped():
    s = merge(new_case(), Extraction(people=[NewPerson(id='p1', label='girlfriend', quote='girlfriend')]),
              'm1', 'girlfriend')
    # LLM sends p2 with label 'girlfriend'
    s = merge(s, Extraction(people=[NewPerson(id='p2', label='my girlfriend', quote='my girlfriend')],
                            updates=[update('hospital', 'Apollo', 'Apollo', 'p2')]),
              'm2', 'my girlfriend Apollo')
    assert len(s['people']) == 1
    assert 'p1' in s['people']
    assert s['people']['p1']['fields']['hospital']['value'] == 'Apollo'

def test_boolean_for_text_field_coerces_gracefully():
    s = merge(new_case(), Extraction(updates=[update('driver_observation', True, 'observed speeding')]), 'm1', 'observed speeding')
    assert s['fields']['driver_observation']['value'] == 'Yes'

def test_treatment_received_false_skips_hospital_and_medical_costs():
    from engine import applicable
    from questions import INDEX
    s = merge(new_case(), Extraction(people=[NewPerson(id='p1', label='self', quote='I')],
                                     updates=[update('treatment_received', False, 'no treatment', 'p1')]),
              'm1', 'I had no treatment')
    assert not applicable(s, INDEX['hospital'], 'p1')
    assert not applicable(s, INDEX['hospitalized'], 'p1')
    assert not applicable(s, INDEX['treatment_dates'], 'p1')
    assert not applicable(s, INDEX['transport'], 'p1')
    assert not applicable(s, INDEX['medical_records'], 'p1')
    assert not applicable(s, INDEX['medical_costs'], 'p1')

def test_registration_and_driver_traced_conditionals():
    from engine import applicable
    from questions import INDEX
    s = merge(new_case(), Extraction(updates=[update('registration_known', False, 'no number'),
                                             update('driver_traced', True, 'driver traced')]),
              'm1', 'no number, driver traced')
    assert not applicable(s, INDEX['registration'], None)
    assert not applicable(s, INDEX['registration_source'], None)
    assert applicable(s, INDEX['driver_details'], None)


