import json
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from engine import new_case, Extraction, Update, NewPerson, merge, skip, next_question, load_case, report, _resolve_quote, applicable
from questions import QUESTIONS, INDEX
from llm import GroqExtractor, strict_schema
from pdf_export import export_markdown_to_pdf

def upd(key,value,quote,status='answered',correction=False):
    return Update(field=key,value=value,quote=quote,status=status,correction=correction)

def test_priority_and_bank():
    assert len(INDEX)==len(QUESTIONS)
    assert all(not q.person and (not q.parent or q.parent in INDEX) for q in QUESTIONS)
    s=skip(skip(skip(new_case())))
    assert next_question(s)['key']=='allegations'

def test_future_facts_and_attribution():
    text='Police accuse me; I deny contact. 20 November 2022, 1 AM.'
    s=merge(new_case(),Extraction(updates=[upd('allegations','Police allege contact; client denies it','Police accuse me; I deny contact'),upd('date','2022-11-20','20 November 2022'),upd('time','01:00','1 AM')]),'m1',text)
    assert s['fields']['date']['status']=='answered'
    assert 'denies' in s['fields']['allegations']['value']

def test_unknown():
    s=merge(new_case(),Extraction(updates=[upd('name',None,'unknown','unknown')]),'m1','unknown')
    assert next_question(s)['key']=='respondent_role'

def test_non_driver_and_notices():
    s=merge(new_case(),Extraction(updates=[upd('client_driving',False,'not driving'),upd('notice_received',True,'notice received')]),'m1','not driving; notice received')
    assert not applicable(s,INDEX['own_driving_actions'],None)
    assert applicable(s,INDEX['notices'],None)

def test_people_do_not_get_irrelevant_medical_questions():
    s=merge(new_case(),Extraction(people=[NewPerson(id='p1',label='other driver',quote='other driver')]),'m1','other driver')
    assert s['people']['p1']['fields']=={}
    assert next_question(s)['person_id'] is None

def test_quotes_and_distinct_names():
    assert _resolve_quote('I hit them','I did not hit them') is None
    s=merge(new_case(),Extraction(people=[NewPerson(id='p1',label='Ravi',quote='Ravi'),NewPerson(id='p2',label='Ravish',quote='Ravish')]),'m1','Ravi and Ravish')
    assert len(s['people'])==2

def test_transactional():
    s=new_case()
    with pytest.raises(ValueError):
        merge(s,Extraction(updates=[upd('name','Rahul','Rahul'),upd('date','2022-11-20','invented')]),'m1','Rahul')
    assert s['fields']['name']['value'] is None

def test_conflict_correction():
    s=merge(new_case(),Extraction(updates=[upd('time','01:00','1 AM')]),'m1','1 AM')
    s=merge(s,Extraction(updates=[upd('time','13:00','1 PM')]),'m2','1 PM')
    assert s['fields']['time']['status']=='conflicting'
    s=merge(s,Extraction(updates=[upd('time','13:00','I meant 1 PM',correction=True)]),'m3','I meant 1 PM')
    assert s['fields']['time']['status']=='answered'
    assert len(s['fields']['time']['history'])==3

def test_invalidate_and_restore():
    s=new_case();s['incident_summary']='old';s['reviewed']=True
    s=skip(s)
    assert s['incident_summary'] is None and not s['reviewed']
    assert load_case(json.dumps(s))==s
    s['pipeline']='victim'
    with pytest.raises(ValueError):load_case(json.dumps(s))

def test_report_and_pdf():
    content=report(new_case())
    assert 'Accused-side' in content and 'does not establish guilt' in content
    pdf=export_markdown_to_pdf('Accused-side brief','Test',content)
    assert pdf.startswith(b'%PDF') and len(pdf)>1000

def test_strict_schema():
    schema=strict_schema()
    for obj in [schema,*schema['$defs'].values()]:
        assert obj['additionalProperties'] is False
        assert set(obj['required'])==set(obj['properties'])

def test_groq_repair():
    def resp(quote):
        data=Extraction(people=[NewPerson(id='p1',label='client',quote=quote)]).model_dump_json()
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=data))])
    with patch('llm.Groq') as client:
        client.return_value.chat.completions.create.side_effect=[resp('invented'),resp('I drove')]
        s=new_case();result=GroqExtractor('dummy').extract(s,'I drove',None)
        assert len(result.people)==1 and not s['people']
        assert client.return_value.chat.completions.create.call_count==2
