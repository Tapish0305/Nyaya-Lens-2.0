"""Validated state, merge policy, deterministic scheduling and attributed reports."""
import calendar
import copy
import datetime as dt
import difflib
import json
import re
import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from questions import QUESTIONS, INDEX

class Update(BaseModel):
    model_config = ConfigDict(extra='forbid')
    field: str
    person_id: str | None = None
    value: str | bool | None
    status: Literal['answered', 'partial', 'unknown', 'declined', 'not_applicable']
    quote: str
    correction: bool = False


class NewPerson(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    label: str
    quote: str

class Extraction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    people: list[NewPerson] = Field(default_factory=list)
    updates: list[Update] = Field(default_factory=list)
    emergency: bool = False
    emergency_quote: str | None = None

INTRO = ('Hello, I’m Nyaya Lens. I’ll organize your road accident account for lawyer review. '
         'You can say “I don’t know” or skip any question, and correct details at any time. '
         'Assuming everyone is currently safe, what name would you like me to use?')
TERMINAL = {'answered', 'unknown', 'declined', 'not_applicable'}

def empty_field():
    return {'value': None, 'status': 'unanswered', 'history': [], 'clarifications': 0}

def new_case():
    return {'schema_version': 1, 'id': str(uuid.uuid4()),
            'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'fields': {q.key: empty_field() for q in QUESTIONS if not q.person},
            'people': {}, 'messages': [], 'emergency': False, 'reviewed': False,
            'incident_summary': None}

def get_field(state, key, person_id=None):
    return state['people'][person_id]['fields'][key] if person_id else state['fields'][key]

def normalize(q, value, status):
    if status in {'unknown', 'declined', 'not_applicable'}:
        if value is not None:
            raise ValueError(f'{q.key}: unresolved statuses require null values')
        return None, status
    if q.kind == 'bool':
        if type(value) is not bool:
            raise ValueError(f'{q.key} must be a JSON boolean')
    else:
        if isinstance(value, bool):
            value = 'Yes' if value else 'No'
        elif not isinstance(value, str) or not value.strip():
            raise ValueError(f'{q.key} requires nonempty text')
    if q.kind == 'date':
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            dt.date.fromisoformat(value)
        else:
            status = 'partial'
    if q.kind == 'time':
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d(?:\s+approximately)?', value):
            status = 'partial'
    return value, status


def _resolve_quote(quote: str, text: str, min_ratio: float = 0.82) -> str | None:
    """Return an exact or fuzzy-matched substring of *text* for the given *quote*.

    Resolution order:
    1. Exact substring match.
    2. Case-insensitive exact match (returns the original-cased span).
    3. Fuzzy sliding-window match using difflib; accepted when similarity >= min_ratio.
    Returns None when no acceptable match is found.
    """
    if not quote:
        return None
    q = quote.strip()
    if not q:
        return None
    # 1. Exact
    if q in text:
        return q
    # 2. Case-insensitive exact
    tl, ql = text.lower(), q.lower()
    idx = tl.find(ql)
    if idx != -1:
        return text[idx: idx + len(q)]
    # 3. Fuzzy sliding window — skip for very short quotes to avoid false positives
    if len(q) < 6:
        return None
    best_ratio, best_sub = 0.0, ''
    for wlen in range(max(1, len(q) - 3), min(len(text) + 1, len(q) + 4)):
        for start in range(len(text) - wlen + 1):
            sub = text[start: start + wlen]
            ratio = difflib.SequenceMatcher(None, ql, sub.lower(), autojunk=False).ratio()
            if ratio > best_ratio:
                best_ratio, best_sub = ratio, sub
    return best_sub if best_ratio >= min_ratio else None


def _is_same_person(label1: str, label2: str) -> bool:
    l1 = (label1 or '').strip().lower()
    l2 = (label2 or '').strip().lower()
    if not l1 or not l2:
        return False
    if l1 == l2:
        return True
    if l1 in l2 or l2 in l1:
        return True
    return difflib.SequenceMatcher(None, l1, l2).ratio() >= 0.75


def merge(state, result, message_id, text):
    """Transactional: rejected extraction never partially changes the case."""
    out = copy.deepcopy(state)
    seen = set()
    id_remap = {}
    for person in result.people:
        if not re.fullmatch(r'p[1-9]\d*', person.id):
            raise ValueError('Person IDs must be p1, p2, ...')
        # Check if this person is already registered in the case:
        if person.id in out['people']:
            existing_label = out['people'][person.id]['label']
            if _is_same_person(existing_label, person.label):
                continue
        existing_pid = next(
            (pid for pid, p in out['people'].items() if _is_same_person(p['label'], person.label)),
            None
        )
        if existing_pid:
            if person.id != existing_pid:
                id_remap[person.id] = existing_pid
            continue
        if not _resolve_quote(person.quote, text) or not person.label.strip():
            raise ValueError('New person must have a supporting quote')
        target_id = person.id
        if target_id in out['people']:
            existing_nums = [int(re.findall(r'\d+', pid)[0]) for pid in out['people'] if re.findall(r'\d+', pid)]
            next_num = max(existing_nums + [0]) + 1
            target_id = f'p{next_num}'
            id_remap[person.id] = target_id
        out['people'][target_id] = {'label': person.label.strip(), 'source': message_id,
                                    'fields': {q.key: empty_field() for q in QUESTIONS if q.person}}
    for u in result.updates:
        pid = id_remap.get(u.person_id, u.person_id)
        q = INDEX.get(u.field)
        if q is None or q.person != (pid is not None):
            raise ValueError(f'{u.field}: unknown field or incorrect person scope')
        if pid and pid not in out['people']:
            raise ValueError('Unknown person ID')
        identity = (pid, u.field)
        if identity in seen:
            raise ValueError('Duplicate field update')
        seen.add(identity)
        resolved_u_quote = _resolve_quote(u.quote, text)
        if not resolved_u_quote:
            raise ValueError(f'{u.field}: supporting quote must appear in your latest answer')
        value, status = normalize(q, u.value, u.status)
        f = get_field(out, u.field, pid)
        entry = {'value': value, 'status': status, 'source': message_id, 'quote': resolved_u_quote,
                 'correction': u.correction, 'document_verified': False}
        previous = f['status']
        f['history'].append(entry)
        # Unknown/declined must never erase an established fact without an explicit correction.
        if previous in {'answered', 'conflicting'} and status in {'unknown', 'declined', 'not_applicable'} and not u.correction:
            continue
        if previous == 'answered' and f['value'] != value and not u.correction:
            f['status'] = 'conflicting'
        elif previous == 'conflicting' and not u.correction:
            f['status'] = 'conflicting'
        else:
            f['value'], f['status'] = value, status
            f['source'] = message_id
            f['clarifications'] = 0
    if result.emergency:
        if not _resolve_quote(result.emergency_quote, text):
            raise ValueError('Emergency needs supporting text')
        out['emergency'] = True
    out['reviewed'] = False
    return out

def applicable(state, q, pid):
    if not q.parent:
        return True
    parent = get_field(state, q.parent, pid)
    parent_q = INDEX[q.parent]
    return parent['status'] == 'answered' and (parent['value'] is True if parent_q.kind == 'bool' else bool(parent['value']))

def next_question(state):
    if state['emergency']:
        return None
    for q in QUESTIONS:
        ids = list(state['people']) if q.person else [None]
        for pid in ids:
            f = get_field(state, q.key, pid)
            if not applicable(state, q, pid) or f['status'] in TERMINAL:
                continue
            if f['clarifications'] >= 2:
                continue  # unresolved fact remains in report; do not trap the user
            text = q.text.format(person=state['people'][pid]['label'] if pid else '')
            if f['status'] == 'partial':
                text = f'You provided {f["value"]!r}. Please clarify the missing detail. ' + text
            if f['status'] == 'conflicting':
                candidates = list(dict.fromkeys(str(h['value']) for h in f['history'] if h['status'] in {'answered', 'partial'}))
                text = 'I have conflicting accounts: ' + ' / '.join(candidates) + '. Which is correct? Please say “I meant …” to correct it. ' + text
            return {'key': q.key, 'person_id': pid, 'priority': q.priority, 'text': text}
    return None

def process(state, text, extractor):
    asked = next_question(state)
    mid = f'm{len(state["messages"]) + 1}'
    result = extractor.extract(state, text, asked)
    out = merge(state, result, mid, text)
    out['messages'].append({'id': mid, 'role': 'user', 'text': text, 'question': asked,
                            'timestamp': dt.datetime.now(dt.timezone.utc).isoformat()})
    if asked:
        f = get_field(out, asked['key'], asked['person_id'])
        if f['status'] not in TERMINAL:
            f['clarifications'] += 1
            
    # Live terminal log for developer visibility
    print(f"\n[Nyaya Lens {mid}]")
    if asked:
        print(f"  Question : [Priority {asked['priority']} • {asked['key']}] {asked['text']}")
    else:
        print("  Question : [Initial / Open statement]")
    print(f"  Answer   : {text}")
    if result.people:
        print(f"  People   : {[p.label for p in result.people]}")
    if result.updates:
        for u in result.updates:
            print(f"  Update   : {u.field} -> {u.value!r} ({u.status})")
    print()
    return out

def skip(state):
    out = copy.deepcopy(state)
    q = next_question(out)
    if q:
        mid = f'm{len(out["messages"]) + 1}'
        f = get_field(out, q['key'], q['person_id'])
        f.update(value=None, status='declined', source=mid)
        f['history'].append({'value': None, 'status': 'declined', 'source': mid,
                              'quote': '[Skip button]', 'correction': False, 'document_verified': False})
        out['messages'].append({'id': mid, 'role': 'user', 'text': '[Skipped]', 'question': q})
        out['reviewed'] = False
    return out

def report(state):
    lines = ['# Nyaya Lens — Road accident intake brief', '', f'Case ID: {state["id"]}',
             f'User reviewed: {state["reviewed"]}', '',
             'All facts below are user-reported, not document-verified. Liability and legal strategy require lawyer review.', '']
    for priority in range(7):
        lines += [f'## Priority {priority}', '']
        for q in QUESTIONS:
            if q.priority != priority:
                continue
            for pid in (list(state['people']) if q.person else [None]):
                f = get_field(state, q.key, pid)
                label = (state['people'][pid]['label'] + ': ') if pid else ''
                status = f['status']
                if not applicable(state, q, pid) and status == 'unanswered':
                    status = 'not asked: conditional question'
                lines.append(f'- {label}{q.key}: {json.dumps(f["value"], ensure_ascii=False)} [{status}; {f.get("source", "no source")}]')
                if f['status'] == 'conflicting':
                    for h in f['history']:
                        lines.append(f'  - Alternative: {h["value"]!r} [{h["source"]}]')
        lines.append('')
    lines += ['## Source messages', '']
    for m in state['messages']:
        lines += [f'### {m["id"]}', '', m['text'], '']
    return '\n'.join(lines)

def load_case(raw):
    """Validate a local exported case before restoring the UI session."""
    state = json.loads(raw)
    base = new_case()
    if state.get('schema_version') != 1:
        raise ValueError('Unsupported case version')
    for k in base:
        if k not in state:
            if k == 'incident_summary':
                state['incident_summary'] = None
            else:
                raise ValueError(f'Missing {k}')
    uuid.UUID(state['id'])
    if set(state['fields']) != set(base['fields']):
        raise ValueError('Unexpected case fields')
    person_fields = {q.key for q in QUESTIONS if q.person}
    for p in state['people'].values():
        if set(p['fields']) != person_fields or not isinstance(p['label'], str):
            raise ValueError('Invalid person record')
    for fields in [state['fields']] + [p['fields'] for p in state['people'].values()]:
        for key, f in fields.items():
            if f['status'] not in TERMINAL | {'unanswered', 'partial', 'conflicting'}:
                raise ValueError('Invalid status')
            if not isinstance(f['history'], list) or not isinstance(f['clarifications'], int):
                raise ValueError('Invalid history or clarification count')
            if f['status'] in {'answered', 'partial'}:
                normalize(INDEX[key], f['value'], f['status'])
    if type(state['emergency']) is not bool or type(state['reviewed']) is not bool or not isinstance(state['messages'], list):
        raise ValueError('Invalid case metadata')
    return state
