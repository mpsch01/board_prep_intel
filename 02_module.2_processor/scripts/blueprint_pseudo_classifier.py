"""
blueprint_pseudo_classifier.py
===============================
Classifies ITE questions (2018–2023) into ABFM Blueprint Categories using
rule-based regex on question_text + concept_summary.

Official ABFM definitions (content area descriptions, 2024 blueprint):
  Acute Care and Diagnosis    — ambulatory scenarios; next steps in diagnosis,
                                correct diagnosis, or initial treatment.
  Chronic Care Management     — ambulatory or long-term care; ongoing management
                                of a chronic disease.
  Emergent and Urgent Care    — hospital/ED/urgent care/ambulatory; management
                                decisions needed in a matter of hours.
  Preventive Care             — ambulatory; preventive care services being provided.
  Foundations of Care         — statistics, health policy, legal issues,
                                health equity, communication, and other topics.

Target percentages (ABFM): Acute 35%, Chronic 25%, Emergent 20%, Preventive 15%, Foundations 5%

Priority (highest → lowest): Emergent → Foundations → Preventive → Chronic → Acute

Concept_summary is treated as a first-class signal alongside question_text.
Patterns may match either field; regex applied to the combined string.

2024 and 2025 data is Gold Standard (ABFM official). This script targets 2018–2023
(pseudo-label). Blueprint values written to the same `blueprint` column with no
qualifier — provenance documented in BATON_024 and CLAUDE.md.

Usage:
  python blueprint_pseudo_classifier.py --dry-run          # validate vs Gold Standard only
  python blueprint_pseudo_classifier.py --dry-run --verbose # + misclassification detail
  python blueprint_pseudo_classifier.py --year 2022        # preview distribution for one year
  python blueprint_pseudo_classifier.py --write            # apply to 2018–2023 (nulls only)
  python blueprint_pseudo_classifier.py --write --force    # overwrite existing values too
"""

import sqlite3
import re
import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

GOLD_YEARS = (2024, 2025)
TARGET_YEARS = (2018, 2019, 2020, 2021, 2022, 2023)

# ─── CLASSIFICATION PATTERNS ─────────────────────────────────────────────────
# Evaluated against combined (question_text + concept_summary), case-insensitive.
# concept_summary uses language like "Tests knowledge that [X] is first-line for [Y]"
# question_text has patient scenarios and clinical settings.

# ── EMERGENT AND URGENT CARE ─────────────────────────────────────────────────
# ABFM: "hospital/ED/urgent care settings or ambulatory settings where management
# decisions are needed in a matter of hours."
# Broader than ICU-level emergencies — includes urgent care presentations, all
# trauma/injuries, acute fractures, burns, lacerations, acute psychiatric crises.

EMERGENT_PATTERNS = [
    # ── True time-critical language ──
    # Primary signal: the TREATMENT decision cannot wait hours.
    # ED/urgent care setting alone is NOT sufficient — ABFM labels many diagnostic
    # questions set in those venues as "Acute Care."  Setting + treatment focus = Emergent.
    r'in a matter of hours',
    r'brought.*?by ambulance',
    r'found.*?on (?:the )?floor',
    r'life.?threatening',
    r'immediate(?:ly)? (?:transport|transfer|resuscitat|stabiliz|reposit|cool|reduc)',
    r'within (?:1|one|two|2) hours?.{0,30}(?:for best|optimal|essential)',

    # ── Setting + TREATMENT focus (not purely diagnostic) ──
    # Checked AFTER the exclusion guard in classify_question().
    # These are ED/inpatient presentations where the question is about management.
    r'(?:presents? to|brought to|arrived at).{0,15}emergency department.{0,200}(?:management|treatment|stabiliz|resuscitat|urgent|immediate)',
    r'\badmitted to.{0,30}(?:hospital|ICU|floor).{0,200}(?:management|treatment|require|urgent)',
    r'hospitalized.{0,40}(?:patient|adult).{0,100}(?:management|treatment|threshold|require)',

    # ── Concept-summary treatment urgency (first-class signal) ──
    r'(?:medical|vascular|surgical|ophthalmologic|urologic|obstetric) emergency',
    r'time.sensitive (?:decision|management|condition)',
    r'within \d+ (?:hours?|minutes?).{0,30}(?:repair|reposit|replant|cool|closure|best)',
    r'(?:immediate|urgent).{0,40}(?:transfer|evacuation|resuscitation|decompression)',
    r'vascular emergency',

    # ── Trauma and acute injury TREATMENT (hands-on management) ──
    # Splinting, rewarming, repositioning = treatment that must happen now.
    # Diagnostic workup questions for the same injuries = Acute.
    r'thumb spica',
    r'non.weight.bearing.{0,30}(?:fracture|injury|boot|splint)',
    r'scaphoid fracture.{0,40}(?:splint|management|treat)',
    r'Lisfranc.{0,80}(?:management|treatment|splint|surgery|weight|non.weight)',
    r'laceration.{0,40}(?:repair|closure|suture|primary)',
    r'wound closure',
    r'burn(?:s?).{0,60}(?:cool|running.{0,10}water|immediate|first aid)',  # burn cooling treatment
    r'avuls(?:ed|ion).{0,30}(?:tooth|teeth|dental)',
    r'dog bite.{0,40}(?:closure|primary|wound|facial)',
    r'dislocation.{0,40}(?:reduction|reduced|immobiliz|splint|buddy)',
    r'concussion.{0,40}(?:management|return.to.play|protocol|rest period)',

    # ── Critical diagnoses / presentations ──
    r'hypertensive (?:emergency|crisis|urgency)',
    r'(?:severe|symptomatic) hyponatremia.{0,80}(?:treat|hypertonic|correct)',
    r'hyponatremia.{0,30}<\s*12[0-9]\b',              # truly critical sodium
    r'\bHELLP\b',
    r'septic? shock',
    r'\banaphyla(?:xis|ctic)\b.{0,60}(?:present|episode|occur|onset|develop|react|trigger)',
    r'acute aortic dissection',
    r'status epilepticus',
    r'respiratory failure',
    r'hemodynamic(?:ally)? unstable',
    r'cardiac arrest',
    r'\bDKA\b.{0,40}(?:management|treatment|fluid|insulin)',
    r'diabetic ketoacidosis.{0,40}(?:management|treatment|fluid|insulin)',
    r'euglycemic.{0,20}ketoacidosis',
    r'refeeding syndrome.{0,40}(?:management|electrolyte|calorie|gradual)',
    r'pulmonary embolism.{0,40}(?:high pretest|CT pulmonary|anticoagul|management)',
    r'high pretest probability.{0,30}(?:PE|pulmonary embolism)',
    r'acute limb ischemia',
    r'retinal detachment.{0,120}(?:immediate|urgent|referral|ophthalmolog)',
    r'\bpriapism\b',
    r'high.altitude pulmonary edema|\bHAPE\b',
    r'pelvic inflammatory disease.{0,120}(?:empiric|treatment|management|antibiotic|diagnosis|cervical motion|adnexal)',
    r'\bRBC transfusion\b|transfusion threshold.{0,40}hospitalized',
    r'blood pressure of (?:18[0-9]|19\d|2\d{2})/\d{2,3}',  # ≥180 systolic only

    # ── Acute psychiatric crises (treatment needed immediately) ──
    r'suicidal ideation.{0,60}(?:assessment|safety|plan|risk|immediate|management)',
    r'suicide risk assessment',
    r'safety plan(?:ning)?.{0,40}(?:suicid|imminent|crisis)',

    # ── Time-critical office-level emergencies ──
    r'sexual assault.{0,60}(?:empiric|STI|prophylaxis|protocol|treatment)',
    r'SVT.{0,60}(?:adenosine|vagal maneuver|management)',
    r'supraventricular tachycardia.{0,60}(?:adenosine|vagal|management)',
    r'\bpriapism\b',
    r'Todd.?s? paralysis',
    r'child abuse.{0,30}(?:TEN.?4|bruising|suspect|physical abuse)',
    r'\bTEN.?4\b',
    r'acute angle.closure glaucoma',

    # ── Additional specific diagnoses (v2 — from verbose misclassification analysis) ──
    # Classic emergent presentations with no chronic form
    r'thyroid storm',
    r'thyrotoxic crisis',
    r'subarachnoid hemorrhage',
    r'worst headache.{0,30}(?:of (?:his|her|their|the patient|a|my) life|ever)',
    r'thunderclap headache',
    r'orbital cellulitis',
    r'ischemic colitis',
    r'perforated? peptic ulcer',
    r'peptic ulcer.{0,20}perforation',
    r'perforated? (?:bowel|viscus|hollow organ)',
    r'Rocky Mountain spotted fever|\bRMSF\b',

    # Opioid / toxicology emergencies
    # Note: r'\bnaloxone\b' alone is too broad — catches prescribing guideline questions.
    # Require opioid toxidrome context or comatose/acute presentation.
    r'opioid.{0,30}toxidrome',
    r'opioid.{0,30}overdose.{0,60}(?:reversal|management|treat|acute|emergency|comatose|unconscious|respiratory depression)',
    r'comatose.{0,60}(?:overdose|opioid|naloxone)',

    # Acute cardiac — STEMI equivalents (LBBB + chest pain = STEMI equivalent)
    r'STEMI equivalent',
    r'new.{0,5}left bundle branch block.{0,100}(?:chest pain|ACS|emergent|coronary|transport|PCI|acute)',

    # Heavy bleeding emergencies
    r'(?:acute|heavy|severe).{0,15}(?:uterine|vaginal) bleeding',
    r'tranexamic acid.{0,80}(?:bleeding|hemorrhage|uterine|vaginal|heavy)',

    # Acute presentations in urgent/emergent contexts
    r'epistaxis.{0,60}(?:active|persistent|management|control|compression|anticoagul)',
    r'(?:first|second|third).{0,5}degree burn',   # prevents Preventive prophylaxis false positive
    r'hip fracture.{0,60}(?:present|management|surgical|acute|external rotation|diagnosis)',
    r'spinal (?:immobilization|stabilization|precaution)',   # spine trauma always urgent
    r'\bdelirium\b.{0,60}(?:management|treatment|antipsychotic|risperidone|haloperidol|agitation)',

    # Aortic / vascular emergencies
    r'aortic aneurysm.{0,80}(?:rupture|ruptured|severe pain|back pain|expanding)',
    r'severe abdominal pain.{0,40}radiates?.{0,15}(?:back|flank)',  # AAA rupture pattern

    # Structural heart disease with urgent intervention
    r'(?:severe|symptomatic) aortic stenosis.{0,80}(?:urgent|emergent|replacement|repair|intervention)',

    # Sexual assault — fix reversed-order combined-text distance issue
    r'sexual assault.{0,400}(?:STI|empiric|gonorrhea|prophylaxis|protocol)',  # Q text + CS combined
    r'(?:empiric|STI treatment|gonorrhea).{0,60}(?:sexual assault|assault victim)',  # reversed order

    # Pediatric respiratory distress
    r'(?:grunting|retractions).{0,40}(?:pneumonia|respiratory|distress)',

    # Additional missed conditions
    r'choledocholithiasis',                  # post-cholecystectomy biliary obstruction = emergent
    r'gross hematuria.{0,80}(?:immediate|urgent|cystoscopy|urolog|malignancy)',
    r'all adults? with gross hematuria',
    r'\bneck.{0,20}(?:stabilization|immobilization)\b',  # spine trauma sideline management
    r'facial (?:palsy|paralysis).{0,100}(?:stroke|central|brain MRI|urgent)',

    # PE workup — fix reversed-order concept_summary issue
    r'high pretest probability.{0,100}(?:CT angiography|CTPA|anticoagul)',
    r'(?:CT pulmonary angiography|CTPA).{0,60}(?:high pretest|PE|pulmonary embolism)',

    # ── Time-critical conditions: ALWAYS Emergent regardless of question type ──
    # KEY INSIGHT (Wang et al. 2025, Table 2): The category reflects the time-urgency
    # of the UNDERLYING CONDITION, not whether the question asks about diagnosis or
    # treatment. An appendicitis imaging question = Emergent because "this is an issue
    # that needs to be addressed in the next hours to 1-2 days or else harm will happen."

    # Acute abdomen / surgical emergencies
    r'\bappendicitis\b',               # always a surgical emergency; no chronic form
    r'ectopic pregnancy',              # rupture risk; hours to hemodynamic collapse
    r'suspected ectopic',
    r'heterotopic pregnancy',
    r'testicular torsion',             # 6-hour salvage window
    r'torsion of.{0,20}(?:testicle|testis|ovary|ovarian)',
    r'ovarian torsion',
    r'compartment syndrome',           # hours to irreversible muscle/nerve death
    r'cauda equina',                   # hours to permanent bowel/bladder deficit
    r'mesenteric ischemia',
    r'acute mesenteric',
    r'small bowel obstruction.{0,40}(?:management|surgical|strangulat|NG|nasogastric|decompres)',
    r'strangulated.{0,20}(?:hernia|bowel|obstruction)',

    # Airway / respiratory emergencies
    r'\bepiglottitis\b',               # airway can close in hours; always emergent
    r'tension pneumothorax',           # minutes to arrest
    r'needle.{0,20}decompression',     # treatment = tension pneumo
    r'needle.{0,20}thoracostomy',

    # Acute neurological emergencies
    r'cauda equina syndrome',
    r'bacterial meningitis.{0,80}(?:treat|antibiotic|steroid|LP|lumbar|management|empiric)',
    r'meningococcal.{0,40}(?:meningitis|disease|infection)',
    r'spinal epidural abscess',
    r'epidural abscess.{0,60}(?:MRI|emergent|surgical|management|treatment|drain)',
    r'spinal cord compression.{0,60}(?:emergent|urgent|dexamethasone|MRI|management)',

    # Acute cardiac emergencies
    r'\bSTEMI\b.{0,80}(?:present|ECG|cath|PCI|alteplase|reperfusion|management|treat|door)',
    r'ST.elevation.{0,40}(?:myocardial infarction|\bMI\b)',
    r'door.to.(?:balloon|needle)',     # time-to-treatment metric = acute MI or stroke
    r'primary PCI.{0,40}(?:STEMI|preferred|door)',

    # Acute stroke
    r'acute ischemic stroke.{0,80}(?:tPA|alteplase|thrombolysis|treatment|management|imaging|present)',
    r'\btPA\b.{0,40}(?:stroke|ischemic|eligible|window|contra)',
    r'\balteplase\b.{0,40}(?:stroke|ischemic|window|eligible)',
    r'stroke.{0,30}thrombolysis',
    r'tissue plasminogen activator.{0,40}(?:stroke|ischemic)',
]

# ── FOUNDATIONS OF CARE ───────────────────────────────────────────────────────
# ABFM: "statistics, health policy, legal issues, health equity, and other topics."
# Narrow the health policy patterns to avoid false positives on clinical questions
# that incidentally mention Medicare/Medicaid in a patient context.

FOUNDATIONS_PATTERNS = [
    # ── Biostatistics ──
    r'\bNNT\b', r'\bNNH\b', r'\bARR\b', r'\bRRR\b',
    r'number needed to treat',
    r'absolute risk reduction', r'relative risk reduction',
    r'number needed to (?:harm|treat)',
    r'sensitivity.{0,30}specificity|specificity.{0,30}sensitivity',
    r'\bPPV\b', r'\bNPV\b',
    r'positive predictive value', r'negative predictive value',
    r'confidence interval', r'\bp[\s\-]?value\b',
    r'\bodds ratio\b', r'likelihood ratio',
    r'event rate.{0,60}treatment group|treatment group.{0,60}event rate',
    r'\bfalse positive rate\b', r'\bfalse negative rate\b',
    r'pre.?test probability.{0,30}(?:test|rule)',  # narrow — avoid PE overlap
    r'post.?test probability',
    r'\bintention.to.treat\b', r'\bper.?protocol analysis\b',
    r'randomized controlled trial.{0,30}(?:design|which|demonstrates)',
    r'study design|cohort study|case.control',

    # ── Health systems / policy ──
    r'Medicaid.{0,60}(?:program|largest|coverage|fund|enroll|long.term care|benefit)',
    r'Medicare.{0,60}(?:program|largest|coverage|fund|enroll|benefit|advantage)',
    r'\bCHIP\b',
    r'health (?:insurance program|policy|system reform)',
    r'Affordable Care Act', r'\bACA\b',
    r'fee.for.service', r'capitation payment',
    r'value.based (?:care|payment)',
    r'health care (?:cost|spending|reform|financing)',

    # ── Legal / ethics ──
    r'\bconfidentiality\b',
    r'informed consent',
    r'\bHIPAA\b',
    r'mandatory report(?:ing)?',
    r'advance directive', r'\bguardianship\b', r'\bpower of attorney\b',
    r'minor.{0,40}(?:confiden|disclos|parent|right|sexual|contraception)',
    r'adolescent.{0,40}(?:confiden|disclos|right|consent)',
    r'patient.{0,30}(?:autonomy|right to refuse)',
    r'legal(?:ly)? (?:obligat|required|mandated|report)',
    r'medical decision.making capacity',

    # ── Health equity / SDOH ──
    r'social determinants? of health',
    r'\bSDOH\b',
    r'health (?:equity|disparity|disparities|inequit)',
    r'structural racism', r'implicit bias',
    r'protective.{0,30}(?:social determinant|factor).{0,30}(?:alzheimer|dementia|disease)',

    # ── Communication frameworks ──
    r'motivational interviewing',
    r'teach.back',
    r'shared decision.making',
    r'health literacy',
    r'medical interpreter',
    r'(?:address|speak to) the patient directly',
    r'private setting.{0,30}(?:deliver|news|diagnos)',
    r'patient communication.{0,30}(?:strateg|technique|framework)',

    # ── Mental status / neuropsych assessment (Foundations by ABFM) ──
    r'mental status (?:exam|assessment|component)',
    r'spell.{0,20}(?:backward|backwards)',
    r'serial (?:sevens|threes)',
]

# ── PREVENTIVE CARE ───────────────────────────────────────────────────────────
# ABFM: "ambulatory setting where preventive care services are being provided."

PREVENTIVE_PATTERNS = [
    # ── USPSTF / ACIP guidelines ──
    r'U\.?S\.? Preventive Services Task Force',
    r'\bUSPSTF\b',
    r'\bACIP\b',
    r'Advisory Committee on Immunization',

    # ── Vaccines / immunizations ──
    r'\bvaccin(?:e|ation|ated|ate)\b',
    r'\bimmuniz(?:ation|e|ed)\b',
    r'booster dose',
    r'vaccine series|vaccine schedule',
    r'two doses.{0,30}(?:vaccine|immuniz|apart|least)',
    r'shingles vaccine', r'zoster vaccine',
    r'HPV vaccin', r'human papillomavirus vaccin',
    r'tdap.{0,20}pregnan',
    r'influenza vaccine', r'flu shot',
    r'hepatitis [AB] vaccin', r'pneumococcal vaccin',
    r'recombinant zoster',
    r'vaccine refusal',
    r'vaccine timing|timing of (?:the )?(?:vaccine|vaccination)',

    # ── Screening (asymptomatic / wellness context) ──
    r'annual (?:health maintenance|physical|wellness|exam)',
    r'health maintenance (?:exam|visit|appointment)',
    r'well.child (?:exam|visit|check)',
    r'well.woman (?:exam|visit)',
    r'presents? for (?:a )?routine (?:well|health|check|preventive)',
    r'routine (?:wellness|preventive|health maintenance|well.child|well.woman)',
    r'presents? for (?:his|her|a) (?:annual|routine) (?:health|physical|exam|check)',
    r'cancer (?:screening).{0,40}(?:guideline|recommendation|USPSTF|interval|surveillance)',
    r'screening.{0,30}(?:recommendation|guideline|USPSTF|interval)',
    r'sports (?:preparticipation|pre.participation) (?:exam|evaluation)',

    # ── Chemoprophylaxis / primary prevention ──
    r'\bchemoprophylaxis\b',
    r'\bPrEP\b',
    r'primary prevention (?:of|for)',
    r'altitude sickness prevention',
    r'postexposure prophylaxis',
    r'\bprophylax.{0,10}(?:antibiotic|antimicrobial|medication)',
    r'early introduction.{0,40}(?:food|allergen|peanut)',
    r'risk of developing.{0,30}(?:allergy|food allergy|disease)',
    r'reduce.{0,20}risk of (?:developing|diverticulitis|cancer|disease)',
    r'protective (?:effect|factor|diet).{0,40}(?:against|for preventing)',
    r'anticoagulation management.{0,30}(?:prior to|before|perioperative)',  # peri-procedure VTE prevention
    r'bridging (?:anticoagulation|therapy)',
]

# ── CHRONIC CARE MANAGEMENT ───────────────────────────────────────────────────
# ABFM: "ambulatory or long-term care; ongoing management of a chronic disease."
# Broader than explicit "follow-up" visits — includes all questions where the
# task is ongoing management of a named chronic condition, including fact-style
# knowledge questions about first-line therapy for chronic diseases.

CHRONIC_PATTERNS = [
    # ── Explicit follow-up language ──
    r'(?:presents?|comes?|sees?) (?:you )?for (?:routine )?follow.?up of',
    r'follow.?up (?:visit|appointment|care) for',
    r'returns? for (?:routine )?(?:follow.?up|management|monitoring)',
    r'sees you for (?:routine )?follow.?up',
    r'office visit for (?:follow.?up|management) of',

    # ── Long-standing / established condition ──
    r'long.?(?:standing|term) (?:history of|symptoms? of|diagnosis of)',
    r'(?:symptoms?|condition).{0,20}for (?:the past )?(?:several )?(?:\d+ )?(?:months?|years?)',
    r'has had.{0,40}for (?:the past )?(?:several )?(?:\d+ )?(?:months?|years?)',
    r'(?:\d+).(?:month|year).{0,10}history of.{0,60}(?:pain|fatigue|disturbance|dysfunction|disease|disorder)',

    # ── Established chronic diseases (explicit management context) ──
    r'(?:follow.?up|management|monitoring|control|ongoing).{0,30}(?:type [12] diabetes|hypertension|COPD|heart failure|hypothyroid|adrenal insufficiency|lupus|rheumatoid arthritis|Crohn|ulcerative colitis|CKD|chronic kidney|HIV|epilepsy|multiple sclerosis)',
    r'(?:stable|controlled|uncontrolled|poorly controlled).{0,30}(?:hypertension|diabetes|COPD|asthma|heart failure|hypothyroidism|HIV|CKD|epilepsy|gout)',
    r'asthma.{0,60}(?:refill|inhaler|controller|step.?up|ICS|LABA|step.?down)',
    r'(?:refill|renewal).{0,40}(?:asthma|inhaler)',     # reverse-order: refill mentioned before asthma

    # ── Psychiatric / behavioral chronic disease management ──
    r'\bPTSD\b.{0,80}(?:treatment|medication|nightmares|hyperarousal|prazosin|SSRI|SNRI)',
    r'posttraumatic stress disorder.{0,60}(?:treatment|medication|therapy)',
    r'\bbipolar\b.{0,60}(?:treatment|medication|management|manic|lithium|mood stabilizer)',
    r'(?:major )?depression.{0,60}(?:hypomanic|antidepressant|SSRI|SNRI|ongoing|chronic)',
    r'panic disorder.{0,60}(?:treatment|medication|first.line|SSRI|therapy)',
    r'schizophrenia.{0,60}(?:treatment|antipsychotic|medication|management)',
    r'\bADHD\b.{0,60}(?:treatment|stimulant|medication|management)',
    r'opioid use disorder.{0,60}(?:methadone|buprenorphine|naltrexone|treatment|MAT)',

    # ── Specific chronic conditions by name ──
    r'\bfibromyalgia\b',
    r'\bchronic insomnia\b',
    r'venous insufficiency.{0,120}(?:management|stockings|compression|treatment)',
    r'\btinnitus\b.{0,60}(?:treatment|therapy|management|CBT)',
    r'\bMAFLD\b|\bMASLD\b|\bNAFLD\b',
    r'hidradenitis suppurativa',
    r'\banorexia nervosa\b.{0,60}(?:treatment|therapy|management|family)',
    r'infantile hemangioma.{0,40}(?:propranolol|treatment|management)',
    r'speech.{0,10}(?:language )?delay.{0,40}(?:risk factor|evaluation|referral|management)',
    r'recurrent gout.{0,60}(?:prophylaxis|management|allopurinol|febuxostat)',
    r'gout prophylaxis',
    r'immune thrombocytopenia|\bITP\b.{0,40}(?:platelet|treatment|management)',
    r'TMJ.{0,40}(?:dysfunction|treatment|management|NSAID)',
    r'chronic kidney disease.{0,60}(?:stage|edema|management|medication|screening|CKD.MBD)',
    r'\bCKD.MBD\b',
    r'post.?MI.{0,60}(?:complication|management|follow.?up|medication)',
    r'heart failure.{0,60}(?:medication|SGLT2|ejection fraction|management)',
    r'SGLT2.{0,40}(?:heart failure|HFrEF|HFpEF)',

    # ── Medication management for chronic disease (concept_summary signals) ──
    r'(?:first.line|preferred|most effective|FDA.approved).{0,60}(?:for|in treating).{0,60}(?:fibromyalgia|PTSD|chronic insomnia|panic disorder|opioid use disorder|anorexia nervosa|tinnitus|venous insufficiency|hidradenitis|MASLD|NAFLD|MAFLD|gout|ITP)',
    r'(?:first.line|preferred|most effective|FDA.approved).{0,60}(?:pharmacologic|treatment|medication|agent|therapy).{0,60}(?:chronic|ongoing|persistent|recurrent|maintenance)',
    r'in patients? with.{0,40}(?:PTSD|fibromyalgia|panic disorder|chronic insomnia|opioid use disorder|venous insufficiency|tinnitus|heart failure with|CKD|COPD|major depress)',

    # ── Ongoing medication use / titration ──
    r'has been (?:taking|on|using).{0,40}for (?:the past )?(?:\d+ )?(?:months?|years?)',
    r'currently (?:taking|on).{0,40}(?:metformin|lisinopril|atorvastatin|levothyroxine|amlodipine|metoprolol|insulin|warfarin|clopidogrel|semaglutide|prazosin)',
    r'medication.{0,20}(?:adjustment|titration|dose increase|dose decrease)',

    # ── Specific management contexts ──
    r'menopaus.{0,60}(?:symptom|management|treatment|vasomotor|HRT|hormone|estrogen)',  # matches menopause + menopausal
    r'(?:PCOS|polycystic ovary syndrome).{0,60}(?:management|fertility|ovulation|letrozole|clomiphene)',
    r'adrenal insufficiency.{0,40}(?:management|replacement|underreplacement)',
    r'osteoporosis.{0,40}(?:management|treatment|bisphosphonate|DEXA|T.score)',
    r'hyperaldosteronism.{0,40}(?:screening|management|diagnosis)',
    r'varenicline.{0,40}(?:smoking|cessation|tobacco)',
    r'smoking cessation.{0,40}(?:treatment|medication|NRT|varenicline)',

    # ── Additional chronic conditions not yet in list (from misclassification analysis) ──
    r'\bParkinson.{0,60}(?:disease|diagnosis|treatment|carbidopa|levodopa|management)',
    r'carbidopa.{0,20}levodopa',                    # first-line Parkinson's treatment
    r'\brosacea\b.{0,80}(?:treatment|management|topical|metronidazole|ivermectin|azelaic)',
    r'subclinical hypothyroidism.{0,80}(?:treat|TSH|antibody|management)',
    r'thyroid peroxidase antibod.{0,60}(?:treat|hypothyroid|subclinical)',
    r'post.?stroke.{0,80}(?:management|complication|spasticity|rehabilitation|physical therapy|anticoagul)',
    r'(?:stable|refractory) angina.{0,80}(?:management|treatment|anti.?anginal|medication|nitrate)',
    r'cannabinoid hyperemesis',
    r'complex regional pain syndrome|\bCRPS\b',
    r'\bnormal.pressure hydrocephalus\b|\bNPH\b.{0,30}(?:gait|hydrocephalus|triad)',
    r'obstructive sleep apnea.{0,80}(?:diagnosis|management|polysomnography|CPAP|treatment)',
    r'\bOSA\b.{0,30}(?:diagnosis|polysomnography|CPAP|treatment|management)',
    r'hepatitis C.{0,80}(?:treatment|antiviral|DAA|management|fibrosis|cirrhosis)',
    r'\bHCV\b.{0,40}(?:treatment|antiviral|management)',
    r'chronic urticaria.{0,80}(?:management|antihistamine|treatment|step)',
    r'dumping syndrome.{0,60}(?:management|treatment|bariatric|diet)',
    r'bariatric surgery.{0,80}(?:deficiency|thiamine|vitamin|complication|management|dumping|bypass)',
    r'male hypogonadism.{0,60}(?:symptom|testosterone|treatment|diagnosis)',
    r'loss of (?:axillary|pubic) hair',             # specific hypogonadism symptom
    r'metformin.{0,80}(?:vitamin B12|B-12|deficiency|monitoring)',
    r'testosterone supplementation.{0,60}(?:hypogonadism|deficiency|symptom)',
    r'benzodiazepine.{0,80}(?:discontinuation|taper|withdrawal|long.acting|diazepam)',
    r'(?:end.stage|hospice).{0,80}(?:symptom management|comfort care|secretion|glycopyrrolate|palliative)',
    r'glycopyrrolate.{0,40}(?:secretion|death rattle|hospice|comfort)',
    r'osteoporosis.{0,80}(?:teriparatide|anabolic|denosumab|very high fracture risk)',
]

# Acute Care and Diagnosis is the default — catches everything not matched above.

# ─── CLASSIFIER ──────────────────────────────────────────────────────────────

def extract_concept_summary(concept_tags_json):
    if not concept_tags_json:
        return ""
    try:
        ct = json.loads(concept_tags_json)
        return ct.get("concept_summary", "") or ""
    except Exception:
        return ""


# Patterns that, if matched, prevent Emergent classification for setting-based triggers.
# These are contexts where ED/hospital is mentioned but the question is follow-up or
# diagnostic knowledge — ABFM labels those Acute.
# Hard context overrides — these domains are definitively Foundations, never Emergent.
# Applied to ALL Emergent patterns (not just setting-based ones).
EMERGENT_HARD_EXCLUSIONS = [
    r'right to refuse|patient autonomy',
    r'refus(?:ed|es|ing).{0,30}(?:blood|transfusion|life.saving treatment)',
    r'competent.{0,15}(?:adult|patient).{0,30}(?:refus|declin)',
]

EMERGENT_EXCLUSIONS = [
    r'follow.?up.{0,60}(?:emergency department|ED visit|ER visit)',
    r'follow.?up.{0,30}(?:recent|prior|previous|last).{0,30}(?:visit|hospitalization)',
    r'(?:recent|prior|previous).{0,20}(?:hospitalization|hospital visit)',
    # Protect STEMI/stroke patterns from firing on post-event chronic management questions
    r'history of.{0,30}(?:STEMI|myocardial infarction|\bMI\b).{0,60}(?:follow.?up|management|presents?|sees you)',
    r'(?:post|after).{0,20}(?:MI|STEMI|myocardial infarction|stroke|appendectomy).{0,30}(?:follow.?up|management|returns?|presents?)',
]


def classify_question(question_text, concept_summary):
    """Return blueprint category string using priority-ordered rules."""
    text = question_text or ""
    summary = concept_summary or ""
    # Normalize whitespace: collapse newlines + multiple spaces so multi-line question text
    # doesn't break regex patterns that span natural sentence boundaries.
    combined = re.sub(r'\s+', ' ', f"{text} {summary}")

    # Hard exclusions: these contexts are definitively not Emergent (skip ALL patterns)
    if any(re.search(p, combined, re.IGNORECASE) for p in EMERGENT_HARD_EXCLUSIONS):
        pass  # fall through to Foundations / other checks
    else:
        # Soft exclusions — follow-up / prior-visit contexts (suppress setting-based patterns only)
        is_followup_context = any(
            re.search(p, combined, re.IGNORECASE) for p in EMERGENT_EXCLUSIONS
        )

        # Keywords that identify patterns which should be suppressed in follow-up/post-event contexts
        _FOLLOWUP_SUPPRESSIBLE = [
            'emergency department', 'admitted to', 'hospitalized',  # setting-based
            'STEMI', 'ST.elevation', 'door.to', 'primary PCI',      # post-MI chronic follow-up
            'tPA', 'alteplase', 'thrombolysis', 'tissue plasminogen',  # post-stroke follow-up
        ]

        for pat in EMERGENT_PATTERNS:
            if is_followup_context and any(kw in pat for kw in _FOLLOWUP_SUPPRESSIBLE):
                continue
            if re.search(pat, combined, re.IGNORECASE):
                return "Emergent and Urgent Care"

    for pat in FOUNDATIONS_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return "Foundations of Care"

    for pat in PREVENTIVE_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return "Preventive Care"

    for pat in CHRONIC_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return "Chronic Care Management"

    return "Acute Care and Diagnosis"


# ─── VALIDATION ──────────────────────────────────────────────────────────────

def validate_gold_standard(conn, verbose=False):
    """Run classifier against 2024/2025 Gold Standard; print accuracy report."""
    rows = conn.execute("""
        SELECT qid, exam_year, question_text, concept_tags, blueprint
        FROM questions
        WHERE exam_year IN (2024, 2025)
          AND blueprint IS NOT NULL
    """).fetchall()

    total = len(rows)
    correct = 0
    errors_by_cat = defaultdict(list)
    confusion = defaultdict(Counter)

    for qid, year, text, ct_json, gold in rows:
        concept_summary = extract_concept_summary(ct_json)
        predicted = classify_question(text, concept_summary)
        confusion[gold][predicted] += 1
        if predicted == gold:
            correct += 1
        else:
            errors_by_cat[gold].append((qid, year, predicted, (text or "")[:130]))

    acc = correct / total * 100
    print(f"\n{'='*65}")
    print(f"GOLD STANDARD VALIDATION  (n={total}, years 2024+2025)")
    print(f"{'='*65}")
    print(f"Overall accuracy: {correct}/{total}  ({acc:.1f}%)\n")

    cats = [
        "Acute Care and Diagnosis",
        "Chronic Care Management",
        "Emergent and Urgent Care",
        "Preventive Care",
        "Foundations of Care",
    ]
    short = {
        "Acute Care and Diagnosis": "Acute",
        "Chronic Care Management":  "Chronic",
        "Emergent and Urgent Care": "Emergent",
        "Preventive Care":          "Preventive",
        "Foundations of Care":      "Foundations",
    }

    print(f"{'Category':<30} {'Gold':>5} {'Corr':>5} {'Acc%':>7}  Confusion")
    print("-" * 80)
    for cat in cats:
        gold_n = sum(confusion[cat].values())
        corr_n = confusion[cat][cat]
        cat_acc = corr_n / gold_n * 100 if gold_n else 0
        others = {short[k]: v for k, v in confusion[cat].items() if k != cat and v > 0}
        others_str = "  ".join(f"{k}={v}" for k, v in sorted(others.items(), key=lambda x: -x[1]))
        print(f"  {cat:<28} {gold_n:>5} {corr_n:>5} {cat_acc:>6.1f}%  {others_str}")

    if verbose:
        print("\n\nMISCLASSIFICATIONS:")
        for cat in cats:
            errs = errors_by_cat[cat]
            if not errs:
                continue
            print(f"\n── {cat} wrongly predicted as:")
            for qid, year, pred, stem in errs[:12]:
                print(f"   [{qid} {year}] → {short[pred]}")
                print(f"   {stem.strip()}")

    return acc, confusion


# ─── PREVIEW / DRY RUN ───────────────────────────────────────────────────────

def preview_year(conn, year):
    rows = conn.execute("""
        SELECT qid, question_text, concept_tags, blueprint
        FROM questions
        WHERE exam_year = ?
        ORDER BY qid
    """, (year,)).fetchall()

    predicted_dist = Counter()
    for qid, text, ct_json, existing in rows:
        cs = extract_concept_summary(ct_json)
        pred = classify_question(text, cs)
        predicted_dist[pred] += 1

    total = len(rows)
    print(f"\nYear {year} predicted distribution (n={total}):")
    target = {"Acute Care and Diagnosis": 0.35, "Chronic Care Management": 0.25,
              "Emergent and Urgent Care": 0.20, "Preventive Care": 0.15, "Foundations of Care": 0.05}
    for cat in ["Acute Care and Diagnosis", "Chronic Care Management", "Emergent and Urgent Care",
                "Preventive Care", "Foundations of Care"]:
        cnt = predicted_dist[cat]
        pct = cnt / total * 100
        tgt = target[cat] * 100
        delta = pct - tgt
        print(f"  {cat:<35} {cnt:>4}  ({pct:.1f}%  target={tgt:.0f}%  delta={delta:+.1f})")


# ─── WRITE TO DB ─────────────────────────────────────────────────────────────

def write_classifications(conn, force=False):
    target_clause = ",".join("?" * len(TARGET_YEARS))

    if force:
        rows = conn.execute(f"""
            SELECT qid, question_text, concept_tags
            FROM questions
            WHERE exam_year IN ({target_clause})
        """, TARGET_YEARS).fetchall()
    else:
        rows = conn.execute(f"""
            SELECT qid, question_text, concept_tags
            FROM questions
            WHERE exam_year IN ({target_clause})
              AND (blueprint IS NULL OR blueprint = '')
        """, TARGET_YEARS).fetchall()

    updates = []
    dist = Counter()
    for qid, text, ct_json in rows:
        cs = extract_concept_summary(ct_json)
        pred = classify_question(text, cs)
        updates.append((pred, qid))
        dist[pred] += 1

    conn.executemany("UPDATE questions SET blueprint = ? WHERE qid = ?", updates)
    conn.commit()

    total = len(updates)
    print(f"\nWrote {total} classifications to questions.blueprint")
    target = {"Acute Care and Diagnosis": 0.35, "Chronic Care Management": 0.25,
              "Emergent and Urgent Care": 0.20, "Preventive Care": 0.15, "Foundations of Care": 0.05}
    print("Distribution vs ABFM targets:")
    for cat in ["Acute Care and Diagnosis", "Chronic Care Management", "Emergent and Urgent Care",
                "Preventive Care", "Foundations of Care"]:
        cnt = dist[cat]
        pct = cnt / total * 100
        tgt = target[cat] * 100
        print(f"  {cat:<35} {cnt:>4}  ({pct:.1f}%  target={tgt:.0f}%)")


# ─── POST-WRITE QC ───────────────────────────────────────────────────────────

def post_write_qc(conn):
    print("\nPost-write QC — blueprint population by year:")
    rows = conn.execute("""
        SELECT exam_year,
               COUNT(*) total,
               SUM(CASE WHEN blueprint IS NOT NULL AND blueprint != '' THEN 1 ELSE 0 END) filled
        FROM questions
        GROUP BY exam_year
        ORDER BY exam_year
    """).fetchall()
    for yr, total, filled in rows:
        label = "Gold Standard" if yr in GOLD_YEARS else "pseudo-label"
        print(f"  {yr}: {filled}/{total} filled  [{label}]")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ABFM Blueprint pseudo-classifier for ITE questions")
    parser.add_argument("--dry-run",  action="store_true", help="Validate against Gold Standard; no writes")
    parser.add_argument("--verbose",  action="store_true", help="Show misclassification detail in dry-run")
    parser.add_argument("--year",     type=int,            help="Preview predicted distribution for one year")
    parser.add_argument("--write",    action="store_true", help="Write classifications to DB for 2018–2023")
    parser.add_argument("--force",    action="store_true", help="With --write: overwrite existing values too")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)

    if args.dry_run or (not args.write and not args.year):
        validate_gold_standard(conn, verbose=args.verbose)

    if args.year:
        preview_year(conn, args.year)

    if args.write:
        print("Validating against Gold Standard before writing...")
        validate_gold_standard(conn, verbose=False)
        write_classifications(conn, force=args.force)
        post_write_qc(conn)

    conn.close()


if __name__ == "__main__":
    main()
