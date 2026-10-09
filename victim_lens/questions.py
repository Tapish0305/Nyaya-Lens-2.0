"""Question bank: order is deterministic; extraction can fill any field."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Question:
    key: str
    priority: int
    text: str
    kind: str = 'text'
    parent: str | None = None
    person: bool = False

Q = Question
QUESTIONS = [
    Q('name', 0, 'What name would you like me to use?'),
    Q('respondent_role', 0, 'Were you involved yourself, or are you answering for someone else?'),
    Q('narrative', 1, 'Please describe what happened, starting just before the accident.'),
    Q('date', 1, 'On what date did it happen? Please include the year.', 'date'),
    Q('time', 1, 'Approximately what time did it happen? Include AM or PM.', 'time'),
    Q('location', 1, 'Where did it happen? Include city, state, road and a nearby landmark.'),
    Q('travel_role', 1, 'Were you driving, a passenger, walking, or travelling another way?'),
    Q('people', 1, 'Who was involved or injured? Please identify each person, including yourself if involved.'),
    Q('injuries', 2, 'What injuries did {person} suffer?', person=True),
    Q('treatment_received', 2, 'Has {person} received medical treatment?', 'bool', person=True),
    Q('hospital', 2, 'Which hospital or clinic treated {person}?', parent='treatment_received', person=True),
    Q('hospitalized', 2, 'Was {person} admitted as an inpatient?', 'bool', parent='treatment_received', person=True),
    Q('admission_status', 2, 'Is {person} still admitted, discharged, or receiving follow-up care?', parent='hospitalized', person=True),
    Q('treatment_dates', 2, 'When did {person} receive medical treatment?', parent='treatment_received', person=True),
    Q('transport', 2, 'How did {person} reach medical care? Was an ambulance called?', parent='treatment_received', person=True),
    Q('medical_records', 2, 'What medical records or bills are available for {person}?', parent='treatment_received', person=True),
    Q('daily_impact', 2, 'How are the injuries affecting daily activities or work for {person}?', person=True),
    Q('lasting_impairment', 2, 'Has a doctor assessed lasting impairment for {person}? Describe any record.', person=True),
    Q('vehicles', 3, 'What vehicles were involved? Include your vehicle and the other vehicle.'),
    Q('registration_known', 3, 'Do you know the other vehicle’s full or partial registration number?', 'bool'),
    Q('registration', 3, 'What is the other vehicle’s full or partial registration number?', parent='registration_known'),
    Q('registration_source', 3, 'How did you obtain the registration number?', parent='registration_known'),
    Q('collision_point', 3, 'Which parts or sides of the vehicles made contact?'),
    Q('directions', 3, 'Which direction was each vehicle travelling, and were they turning or changing lanes?'),
    Q('driver_observation', 3, 'What did you personally observe about the other driver’s actions?'),
    Q('driver_stopped', 3, 'Did the other driver stop, leave, or exchange details?'),
    Q('driver_traced', 3, 'Has the other driver or vehicle since been identified or traced?', 'bool'),
    Q('driver_details', 3, 'What are the other driver’s name, contact or vehicle details?', parent='driver_traced'),
    Q('road_conditions', 3, 'What were lighting, weather, traffic and road conditions like?'),
    Q('safety_equipment', 3, 'Were relevant helmets or seat belts being used?', 'bool'),
    Q('safety_equipment_details', 3, 'Describe which helmets or seat belts were used, and whether they stayed on.', parent='safety_equipment'),
    Q('vehicle_documents', 3, 'What registration, insurance or driving licence records are available?'),
    Q('witnesses_known', 4, 'Do you know of anyone who saw the collision or helped afterward?', 'bool'),
    Q('witness_details', 4, 'What witness details do you have, and what did each person observe?', parent='witnesses_known'),
    Q('photos', 4, 'Are scene, vehicle or injury photographs or videos available? Describe who took them and when.'),
    Q('cctv_known', 4, 'Do you know of CCTV or dashcam footage that may show the accident?', 'bool'),
    Q('cctv_details', 4, 'Where might the footage be held, and has anyone requested it?', parent='cctv_known'),
    Q('other_evidence', 4, 'Do you have relevant messages, call records or other evidence?'),
    Q('vehicle_status', 4, 'Where is your vehicle now? Has it been inspected or repaired?'),
    Q('police_reported', 5, 'Has the accident been reported to police?', 'bool'),
    Q('police_station', 5, 'You mentioned reporting to police. Which exact police station and district handled it?', parent='police_reported'),
    Q('report_date', 5, 'Who reported it to police, and when?', parent='police_reported'),
    Q('fir_registered', 5, 'Was an FIR registered?', 'bool', parent='police_reported'),
    Q('fir_copy', 5, 'Do you have an FIR copy?', 'bool', parent='fir_registered'),
    Q('fir_number', 5, 'What FIR number and year are recorded?', parent='fir_registered'),
    Q('other_police_record', 5, 'Do you have a complaint acknowledgement or other police record?'),
    Q('investigating_officer', 5, 'Do you know the investigating officer’s name or contact details?', parent='police_reported'),
    Q('police_statement', 5, 'Have police recorded your statement or contacted you further?', parent='police_reported'),
    Q('notices', 5, 'Have you received police, court or insurer notices? Include any stated response dates.'),
    Q('existing_case', 5, 'Has a claim or case already started? Include reference, forum, lawyer and status if known.'),
    Q('medical_costs', 6, 'How much has {person} spent on treatment? Separate billed amounts from estimates.', parent='treatment_received', person=True),
    Q('other_costs', 6, 'What travel, caregiving, rehabilitation or other expenses arose for {person}?', person=True),
    Q('occupation', 6, 'What work did {person} do before the accident?', person=True),
    Q('income_loss', 6, 'Has {person} missed work or lost income? Include period and amount if known.', person=True),
    Q('property_damage', 6, 'What vehicle or other property damage occurred? Are estimates or invoices available?'),
    Q('insurance_claim', 6, 'Has an insurer been informed or a claim submitted? Include insurer, reference and response.'),
    Q('settlement', 6, 'Has anyone offered or paid money, or asked you to sign anything?'),
    Q('desired_help', 6, 'What would you like the lawyer to help with first?'),
]
INDEX = {q.key: q for q in QUESTIONS}
