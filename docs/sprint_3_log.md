## Sprint 3 — Patient Segmentation
**Dates:** 2026-04-01
**Status:** Complete ✓

### Goal
Assign each patient to a clinically meaningful segment based on condition profile, demographics, risk tier, and acute burden. Each patient receives a primary segment for operational reporting and a full multi-label list for analytical use.

### User Stories
- As a clinician, I want patients grouped into actionable segments so that I can tailor intervention strategies to specific cohort needs.
- As a data analyst, I want multi-label segment data so that patients with overlapping clinical signals are not misrepresented by a single classification.
- As a service planner, I want segment-level age and risk distributions so that I can prioritise resources across different patient groups.

### Work Completed
- Derived five segment flags: CARDIO_METABOLIC, MULTIMORBID_FRAIL, MIDLIFE_ESCALATION, ACUTE_OVERLAY, LOW_RISK_STABLE
- Conducted multi-segment overlap analysis before finalising priority hierarchy
- Assigned each patient a primary segment using a documented priority hierarchy
- Added `all_segments` column preserving all qualifying segments per patient for multi-label analytics
- Produced visualisations: gender breakdown by segment, age vs risk score scatter, age vs risk tier scatter, pairwise overlap chart
- Validated segment assignment — 0 unassigned patients, patient count consistent throughout
- Exported `patient_segments.csv` and `segment_summary.csv` to `outputs/`
- Saved `src/assign_segments.py`

### Segment Definitions
| Segment | Priority | Definition | Rationale |
|---|---|---|---|
| Cardio-Metabolic | 1 | CARDIOVASCULAR = 1 AND DIABETES & COMPLICATIONS = 1 | Highest-acuity chronic cohort — co-occurrence of CVS and diabetes is one of the most clinically significant combinations in NHS practice |
| Multimorbid Frail | 2 | Age ≥66 (third age band from Sprint 2) AND category_count ≥3 AND NOT Cardio-Metabolic | Targets the NHS frailty cohort — multimorbidity in the oldest age band exceeds the capacity of condition-specific care pathways |
| Midlife Escalation | 3 | Age band 41–65 (second age band from Sprint 2) AND encounter_count >50 | Identifies opportunities for primary prevention and LTC management — high utilisation in this age band signals accumulating complexity before frailty-tier severity |
| Acute Overlay | 4 | ≥5 distinct acute SNOMED codes present | Captures patients with high acute burden regardless of chronic disease — a different risk profile requiring different management |
| Low Risk Stable | Default | No qualifying segment | Minimal burden — appropriate for standard primary care management |

### Key Decisions
| Decision | Rationale |
|---|---|
| Primary + multi-label architecture | Single best-fit label for reporting; all qualifying segments preserved in all_segments for analytics |
| Multimorbid Frail excludes Cardio-Metabolic | Ensures the more specific label takes precedence — a 70-year-old with CVS + diabetes is better described as Cardio-Metabolic than Multimorbid Frail |
| Age bands derived from Sprint 2 scoring system | Not arbitrary thresholds — directly corresponds to the age band definitions used in risk scoring |
| Midlife Escalation uses encounter_count >50 | Total encounter count is the most reliable utilisation proxy in Synthea — acknowledged as a synthetic data limitation in production would filter to unplanned/condition-related encounters |
| Acute Overlay threshold at ≥5 distinct codes | Lower thresholds captured too broad a proportion of the cohort — 5 distinct acute codes reflects a genuine pattern of multi-domain acute presentation |
| Only two pairwise overlaps reported | Only Multimorbid Frail + Acute Overlay (41 patients, 3.6%) and Midlife Escalation + Acute Overlay (24 patients, 2.1%) produced clinically significant counts — other combinations negligible |

### Reading Segments with Risk Tiers
Segments and risk tiers are designed to be read together. A Multimorbid Frail patient in Critical or High tier warrants proactive intervention. The same segment in Medium or Low tier likely reflects minor category inflation. This two-dimensional view provides the clinical precision that either dimension alone cannot deliver.

### Outputs
- `outputs/patient_segments.csv` — full patient table with primary_segment and all_segments columns
- `outputs/segment_summary.csv` — patient counts and percentages per primary segment

### Validation Results
- Unassigned patients : 0 — PASSED
- Total patients      : 1,152 — consistent throughout

### Segment Distribution
| Segment | Patients | % |
|---|---|---|
| Low Risk Stable | 483 | 41.9% |
| Midlife Escalation | 314 | 27.3% |
| Multimorbid Frail | 230 | 20.0% |
| Acute Overlay | 72 | 6.2% |
| Cardio-Metabolic | 53 | 4.6% |

### Key Insights
- Multimorbid Frail patients with concurrent acute overlay score an average of 19.0 — placing them in the High tier and validating their priority position in the segment hierarchy
- Midlife Escalation patients with acute overlay score 15.9 on average — a 3.1 point gap confirming the priority ordering is clinically justified
- Low Risk Stable average age of 23.2 confirms the scoring engine does not over-stratify younger, healthier patients

### Known Limitations
- Cardio-Metabolic segment is small (53 patients, 4.6%) due to strict definition — a broader definition including endocrinology would inflate the segment at the cost of clinical precision
- Acute condition codes are maintained via an `is_acute` flag in the SNOMED universe reference table — in a production NHS system this would be managed through a validated SNOMED CT sub-hierarchy query or acute care ValueSet
- Segment definitions are cohort-specific and may require recalibration for different populations
- No temporal segmentation — patients are classified on lifetime condition burden, not current clinical status
- `category_count` includes all 15 categories equally — minor categories such as MALE REPRODUCTIVE and ENT count toward the Multimorbid Frail threshold. Patients qualifying on minor categories alone will have low risk tiers; the correct interpretation requires reading segment alongside risk tier.

### Next Sprint
Build `map_icd10.py` — map SNOMED condition codes to UK ICD-10 5th Edition codes at the output layer for reporting and FHIR export compatibility.