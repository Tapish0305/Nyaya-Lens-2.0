"""Standalone accused-side question bank. Shared incident keys retained for later routing."""
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
PRIORITY_LABELS = {
    0: 'Introduction', 1: 'Allegations and current procedural contact',
    2: 'Client’s accident account', 3: 'Client’s actions and vehicle',
    4: 'Evidence and response to allegations', 5: 'Police records and proceedings',
    6: 'Insurance, impact and lawyer handoff'}
QUESTIONS = [
Q('name',0,'What name would you like me to use?'),
Q('respondent_role',0,'Are you answering for yourself or someone else? If someone else, what is your relationship?'),
Q('represented_person',0,'Who is seeking representation, and were they the driver, passenger, vehicle owner, or involved in another way?'),
Q('allegations',1,'What allegation, complaint or claim has been made against you or the person you represent? Describe what was said, without assuming it is proven.'),
Q('allegation_source',1,'How did you learn about it, from whom, and when? Was it spoken or recorded in a document?'),
Q('police_contacted',1,'Have police contacted you or the person you represent?', 'bool'),
Q('police_contact_details',1,'What did police ask or tell you, and when?',parent='police_contacted'),
Q('notice_received',1,'Have you received a police, court or insurer notice?', 'bool'),
Q('notices',1,'What does each notice say? Include issuer, reference, date received, any appearance date and stated response date.',parent='notice_received'),
Q('current_status',1,'What is your current situation regarding police contact, detention or arrest, release, or any scheduled appearance? Say what you know.'),
Q('existing_lawyer',1,'Is a lawyer already assisting you? What help do you need now?'),
Q('narrative',2,'Please describe what happened from your perspective, starting just before the accident. Distinguish what you saw from what you were told.'),
Q('date',2,'On what date did the accident happen? Include the year.','date'),
Q('time',2,'Approximately what time did it happen? Include AM or PM.','time'),
Q('location',2,'Where did it happen? Include city or district, state, road and landmark.'),
Q('travel_role',2,'At the time, were you driving, a passenger, the vehicle owner elsewhere, or involved in another way?'),
Q('people',2,'Who was involved? Identify drivers, passengers and injured people separately, as far as you know.'),
Q('vehicles',2,'Which vehicles were involved? Distinguish your vehicle from the other vehicles.'),
Q('directions',2,'Describe each vehicle’s direction and movement before contact.'),
Q('collision_point',2,'Where did contact occur on each vehicle, if you observed it?'),
Q('road_conditions',2,'What were the road, lighting, visibility, weather, traffic and signal conditions?'),
Q('client_driving',3,'Was the person seeking representation driving?', 'bool'),
Q('own_driving_actions',3,'Describe your driving immediately before contact, including turns, lane changes, signals or braking you remember.',parent='client_driving'),
Q('speed_account',3,'What do you remember about your speed? Distinguish an estimate from a recorded measurement.',parent='client_driving'),
Q('driver_observation',3,'What did you personally observe the other driver or road user doing?'),
Q('stopped_after_collision',3,'Did you stop after the collision?', 'bool',parent='client_driving'),
Q('post_collision_actions',3,'What did you do immediately afterward, in what order? Include stopping, leaving, assistance, calls or exchanging details.'),
Q('departure_account',3,'If you left the scene, explain when, where you went and your reasons. Otherwise say you stayed or that this does not apply.'),
Q('assistance',3,'Did you call emergency services or provide assistance? What happened after that?'),
Q('own_injuries',3,'Did you or the person you represent suffer injuries? What treatment was received, if any?'),
Q('other_injuries_known',3,'What do you know about injuries to other people, and how did you learn it? Do not guess diagnoses.'),
Q('own_vehicle_registration',3,'What is the registration number of the vehicle associated with you, if known?'),
Q('vehicle_ownership',3,'Who owned the vehicle, who was driving, and what permission or employment relationship applied?'),
Q('vehicle_documents',3,'What licence, registration, insurance, permit or other vehicle documents are available?'),
Q('vehicle_status',3,'Where is the vehicle now? Has it been seized, inspected, repaired or moved?'),
Q('safety_equipment',3,'Describe relevant helmets or seat belts for yourself and others, only as far as you know.'),
Q('agreed_points',4,'Which parts of the allegation or other account do you agree with? You can also say you have not seen the account.'),
Q('disputed_points',4,'Which parts do you dispute or not know about? Explain your account without guessing another person’s motives.'),
Q('witnesses_known',4,'Do you know anyone who saw the collision or helped afterward?', 'bool'),
Q('witness_details',4,'What did each person see or do, and what contact details are available?',parent='witnesses_known'),
Q('photos',4,'What photographs, videos or dashcam recordings are available? Who made them and when?'),
Q('cctv_known',4,'Do you know of CCTV footage that may show what happened?', 'bool'),
Q('cctv_details',4,'Where is it held and has anyone requested or obtained it?',parent='cctv_known'),
Q('other_evidence',4,'What messages, calls, location records, inspection reports or other records may help clarify the incident?'),
Q('conflicting_evidence',4,'Are there records or accounts that differ from your recollection? Describe the difference and source.'),
Q('police_reported',5,'As far as you know, was the accident reported to police?', 'bool'),
Q('police_station',5,'Which exact station and district handled the matter?',parent='police_reported'),
Q('report_date',5,'Who made the report, and when, if known?',parent='police_reported'),
Q('fir_registered',5,'Do you know whether an FIR was registered?', 'bool'),
Q('fir_number',5,'What FIR number, year and station are recorded?',parent='fir_registered'),
Q('fir_copy',5,'Do you have the FIR copy?', 'bool',parent='fir_registered'),
Q('recorded_allegations',5,'What allegations or sections are actually written in the record? You may quote them or say you do not know.',parent='fir_registered'),
Q('investigating_officer',5,'Do you know the investigating officer’s name or contact details?'),
Q('police_statement',5,'Have you given a statement or signed anything for police? Describe when, what and any copy available.'),
Q('other_police_record',5,'What acknowledgements, seizure records, inspection records or other police documents are available?'),
Q('existing_case',5,'Has a court matter or compensation claim started? Include forum, reference and known status.'),
Q('orders_conditions',5,'Have any orders or release conditions been communicated? Describe the recorded wording and source, if available.'),
Q('insurance_claim',6,'Has the insurer been notified or received a claim? Include insurer, reference, dates and response.'),
Q('property_damage',6,'What vehicle or other property damage do you know about? Distinguish estimates from invoices.'),
Q('client_financial_impact',6,'What expenses or work disruption has this caused you or the person you represent?'),
Q('settlement',6,'Has anyone offered or paid money, discussed a settlement, or asked you to sign anything? Describe any record.'),
Q('documents_available',6,'Which relevant documents can you provide to your lawyer, and which are missing?'),
Q('desired_help',6,'What would you like your lawyer to address first?'),
]
INDEX = {q.key:q for q in QUESTIONS}
