import json
from types import SimpleNamespace
from unittest.mock import patch
from engine import new_case, Extraction
from llm import GroqExtractor, strict_schema

def test_groq_extraction():
    result = Extraction().model_dump_json()
    completion = SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content=result))])
    with patch('llm.Groq') as client:
        client.return_value.chat.completions.create.return_value = completion
        extracted = GroqExtractor('dummy-key').extract(new_case(),'hello',None)
        assert extracted.updates == []
        args = client.return_value.chat.completions.create.call_args.kwargs
        assert args['model'] == 'openai/gpt-oss-120b'
        assert args['response_format']['json_schema']['strict'] is True
        assert 'hello' in args['messages'][1]['content']

def test_strict_schema_required_fields():
    schema = strict_schema()
    for obj in [schema, *schema['$defs'].values()]:
        assert obj['additionalProperties'] is False
        assert set(obj['required']) == set(obj['properties'])
