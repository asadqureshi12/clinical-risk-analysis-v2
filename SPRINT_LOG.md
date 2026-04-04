## Sprint 1 — SNOMED Condition Mapping
**Dates:** 2026-03-29  
**Status:** Complete

### Goal
Establish the foundational condition mapping layer for the clinical risk pipeline.
All downstream modules (risk scorer, segmentation, FHIR export) depend on this sprint's output.

### User Stories
- As a data analyst, I want every patient condition mapped to a clinical category so that I can perform meaningful cohort-level analysis.
- As a clinician, I want SNOMED CT codes used as the primary terminology throughout the pipeline so that the analysis remains NHS-credible and interoperable.

### Work Completed
- Loaded and deduplicated raw Synthea conditions dataset (8,376 rows, 129 unique SNOMED codes)
- Built `outputs/snomed_conditions_universe.csv` — a curated mapping of all 129 SNOMED codes to 15 clinical categories, aligned with NHS specialty groupings
- Categories with insufficient clinical weight (DENTAL, ALLERGIC REACTION, HEMATOLOGY, DERMATOLOGY) consolidated into OTHER with documented rationale
- Saved `snomed_conditions.py` to `src/` — produces wide-format and long-format patient-level output tables
- Wide format: one row per patient, binary category flags + comorbidity count
- Long format: one row per patient-category pair for dashboard use
- Validated 100% mapping coverage — 0 unmatched condition rows

### Key Decisions
| Decision | Rationale |
|---|---|
| SNOMED throughout the pipeline | Preserves clinical granularity; ICD-10 reserved for output layer only |
| Code-based mapping (SNOMED CODE) | Eliminates ambiguity from description variation; aligns with industry standards |
| Custom CSV mapping file | Transparent and reproducible at this scale; production system would use FHIR ValueSets |
| Recurrences retained in raw data | Same condition on different dates represents a distinct clinical episode |

### Outputs
- `outputs/snomed_conditions_universe.csv` — 129 codes, 15 categories
- `outputs/patient_conditions_wide.csv` — patient-level binary flags
- `outputs/patient_conditions_long.csv` — patient-category pairs for visualisation

### Validation Results
- Condition rows processed: 8,376 — matched: 8,376 (100%)
- Unique patients: consistent across both output formats
- Average categories per patient: 4.1 (clinically plausible for a mixed-age Synthea cohort)

### Known Limitations
- Wide table currently uses binary flags (recurrence not yet reflected in risk)
- Mapping is manually maintained (not yet externalised to dynamic reference)
- No clinical weighting applied at this stage

### Next Sprint
Build `risk_scorer.py` — assign clinical risk weights to condition categories and produce a patient-level risk score.

```## Sprint 2 — Clinical Risk Scoring
**Dates:** 2026-03-31  
**Status:** Complete

### Goal
Build a transparent, multi-layered risk scoring engine that assigns each patient a numeric risk score and four-tier classification, using all four Synthea datasets. All scoring logic is documented, auditable, and aligned with NHS clinical priorities.

### User Stories
- As a clinician, I want each patient assigned a risk tier so that I can prioritise outreach and intervention.
- As a data analyst, I want scoring weights to reflect NHS priority conditions so that the model is clinically credible and defensible.
- As a reviewer, I want all scoring assumptions documented so that the methodology is transparent and reproducible.

### Work Completed
- Loaded all four Synthea datasets: conditions, patients, medications, encounters
- Defined all scoring parameters in a single parameters cell — weights, thresholds, age bands, and bonuses
- Built a six-layer scoring engine:
  - Layer 1 — Base score: category weights aligned with NHS Long Term Plan priorities
  - Layer 2 — Multimorbidity tier: graduated bonus at 2, 5, and 8 condition categories
  - Layer 3 — Age adjustment: upweights high-burden categories for patients aged 41–65 (×1.25) and 66+ (×1.5)
  - Layer 4 — Polypharmacy bonus: tiered at 25, 50, and 100 medications (capped at 100)
  - Layer 5 — Utilisation bonus: tiered at 20, 50, and 100 encounters
  - Layer 6 — Recurrence bonus: +0.5 per age-sensitive category with 3+ episodes
- Validated score distribution — 0 NaN, 0 negative scores
- Calibrated tier thresholds against observed score distribution using percentile cut-points
- Produced summary tables for dashboard and portfolio use
- Exported three output files to outputs/

### Key Decisions
| Decision | Rationale |
|---|---|
| Six scoring layers | Each layer captures a distinct clinical signal — no single proxy measure is sufficient |
| Multimorbidity tier replaces binary comorbidity bonus | Graduated scale reflects increasing complexity more accurately than a binary threshold |
| CVS + diabetes interaction bonus removed | Captured implicitly through high individual weights of both categories |
| Recurrence limited to age-sensitive categories | Recurrence only signals poorly controlled disease in chronic high-burden conditions |
| Medication outlier cap at 100 | 7.9% of patients exceeded this threshold — values above are cumulative historical prescriptions, not concurrent medications |
| Age reference date set to 2020-04-25 | Derived from the latest condition record in the dataset — ensures age is consistent with the observation window |
| Tier thresholds set at rounded percentiles | Empirically derived from observed score distribution rather than arbitrary fixed values |

### Outputs
- `outputs/patient_risk_scores.csv` — full scored patient table including all scoring layers and risk tier
- `outputs/tier_summary.csv` — patient counts and percentages per risk tier
- `outputs/category_by_tier.csv` — top condition categories per tier

### Validation Results
- NaN scores: 0 — PASSED
- Negative scores: 0 — PASSED
- Score range: 0.5 – 42.5
- Mean score: 11.44

### Tier Distribution
| Tier | Patients | % |
|---|---|---|
| Critical | 56 | 4.9% |
| High | 227 | 19.7% |
| Medium | 605 | 52.5% |
| Low | 264 | 22.9% |

### Known Limitations
- Scoring uses binary category flags — severity within a category is not captured
- Medication counts reflect cumulative prescriptions rather than active concurrent medications
- Recurrence bonus is limited to age-sensitive categories — other chronic conditions with high recurrence are not rewarded
- Age adjustment uses fixed multipliers — a continuous age function would be more precise
- Tier thresholds are empirically derived from this cohort and may not generalise to other populations

### Next Sprint
Build `segmentation.py` — group patients into clinically meaningful cohorts based on risk tier, condition profile, and demographic characteristics for targeted intervention planning.

```markdown
## Sprint 3 — Patient Segmentation
**Dates:** 2026-04-01  
**Status:** Complete

### Goal
Assign each patient to clinically meaningful segments based on condition profile, demographics, risk tier, and acute burden. Each patient receives a primary segment for operational reporting and a full multi-label list for analytical use.

### User Stories
- As a clinician, I want patients grouped into actionable segments so that I can tailor intervention strategies to specific cohort needs.
- As a data analyst, I want multi-label segment data so that patients with overlapping clinical signals are not misrepresented by a single classification.
- As a service planner, I want segment-level age and risk distributions so that I can prioritise resources across different patient groups.

### Work Completed
- Derived five segment flags: CARDIO_METABOLIC, MULTIMORBID_FRAIL, MIDLIFE_ESCALATION, ACUTE_OVERLAY, and LOW_RISK_STABLE
- Conducted multi-segment overlap analysis before finalising priority hierarchy
- Assigned each patient a primary segment using a documented priority hierarchy
- Added `all_segments` column preserving all qualifying segments per patient for multi-label analytics
- Produced visualisations: gender breakdown by segment, age vs risk score scatter, stacked risk tier bars, pairwise overlap chart, medication distribution
- Validated segment assignment — 0 unassigned patients, patient count consistent throughout
- Exported `patient_segments.csv` and `segment_summary.csv` to `outputs/`

### Segment Definitions
| Segment | Definition | Rationale |
|---|---|---|
| Cardio-Metabolic | CARDIOVASCULAR = 1 AND DIABETES COMPLICATIONS = 1 | Highest-acuity chronic cohort — strict definition requiring confirmed end-organ involvement |
| Multimorbid Frail | Age ≥66 AND category_count ≥3 AND not Cardio-Metabolic | Frailty defined by multimorbidity, not age alone — reflects NHS complex care thresholds |
| Midlife Escalation | Age 41–65 AND risk tier Medium or High | Prevention window — patients approaching high-risk burden where intervention is most effective |
| Acute Overlay | ≥5 distinct acute SNOMED condition types | Recurring acute presentations across multiple domains — threshold set empirically at 14.9% of cohort |
| Low Risk Stable | No qualifying segment | Minimal chronic burden — 41.9% of cohort, confirming scoring engine does not over-stratify |

### Key Decisions
| Decision | Rationale |
|---|---|
| Primary + multi-label architecture | Single best-fit for reporting; all qualifying segments preserved for analytics |
| Cardio-Metabolic uses strict definition | CARDIOVASCULAR + DIABETES COMPLICATIONS only — more clinically precise than including broad endocrinology |
| Multimorbid Frail excludes Cardio-Metabolic | Ensures mutual exclusivity between the two highest-priority segments |
| Acute Overlay threshold set at ≥5 | Empirically derived — lower thresholds captured >50% of cohort, making them analytically insufficient |
| Utilisation signals embedded in Midlife Escalation definition |
| Age distribution validated per segment | Confirms segment definitions produce clinically coherent demographic profiles |

### Outputs
- `outputs/patient_segments.csv` — full patient table with primary_segment and all_segments columns
- `outputs/segment_summary.csv` — patient counts and percentages per primary segment

### Validation Results
- Unassigned patients: 0 — PASSED
- Total patients: 1,152 — consistent throughout
- Patients with 2+ actionable segments: 109 (9.5%)

### Segment Distribution
| Segment | Patients | % |
|---|---|---|
| Low Risk Stable | 483 | 41.9% |
| Midlife Escalation | 314 | 27.3% |
| Multimorbid Frail | 230 | 20.0% |
| Acute Overlay | 72 | 6.2% |
| Cardio-Metabolic | 53 | 4.6% |

### Key Insights
- Multimorbid Frail patients with concurrent acute conditions score an average of 19.0 — placing them in the High tier and validating their priority position in the segment hierarchy
- Midlife Escalation patients with acute overlay score 15.9 on average — a 3.1 point gap confirming the priority ordering is clinically justified
- Acute Overlay patients average 22.4 years — significantly younger than other segments, reflecting acute presentations such as injuries, infections, and obstetric complications rather than chronic disease
- Low Risk Stable average age of 23.2 confirms the scoring engine does not over-stratify younger, healthier patients

### Known Limitations
- Cardio-Metabolic segment is small (53 patients, 4.6%) due to strict definition — a broader definition including endocrinology would capture 33.4% but at the cost of clinical precision
- Acute condition codes are maintained via an `is_acute` flag in the SNOMED universe reference table rather than a dedicated terminology service — in a production NHS system this would be managed through a validated acute care ValueSet or SNOMED CT sub-hierarchy query
- Segment definitions are cohort-specific and may require recalibration for different populations
- No temporal segmentation — patients are classified on lifetime condition burden, not current clinical status

### Next Sprint
Build `icd10_mapper.py` — map SNOMED condition categories to ICD-10 group codes at the output layer for reporting and dashboard compatibility.
```
## Sprint 4 — ICD-10 Mapping
**Dates:** 2026-04-02  
**Status:** Complete

### Goal
Translate SNOMED CT condition codes to UK ICD-10 codes at the output layer, producing a clinically accurate and auditable terminology crosswalk. ICD-10 codes are applied for reporting and dashboard compatibility whilst SNOMED CT remains the primary terminology throughout the analytical engine.

### User Stories
- As a data analyst, I want each condition mapped to a UK ICD-10 code so that outputs are compatible with NHS administrative reporting systems.
- As a clinical coder, I want SNOMED-to-ICD-10 mappings to preserve diagnostic nuance so that conditions sharing an ICD-10 code are still distinguishable at the SNOMED level.
- As a reviewer, I want the mapping table stored as a versioned reference file so that the crosswalk is auditable and reproducible.

### Work Completed
- Built a UK ICD-10 reference table (`data/reference/uk_icd10_reference.csv`) containing all ICD-10 codes used in the project, aligned with UK ICD-10 5th Edition conventions
- Built an explicit SNOMED-to-ICD-10 mapping table (`data/reference/snomed_to_icd10_map.csv`) — one row per SNOMED code with a clinically specific ICD-10 description preserving diagnostic nuance
- Saved mapping table in JSON format (`data/reference/snomed_to_icd10_map.json`) for programmatic use in the FHIR export pipeline
- Applied mapping to `snomed_conditions_universe.csv` — all 129 SNOMED codes mapped, 0 unmatched
- Applied mapping to raw conditions dataset — all 8,376 condition rows mapped, 0 unmatched
- Exported `outputs/conditions_icd10_mapped.csv` — condition-level table with SNOMED and ICD-10 codes alongside
- Updated `outputs/patient_risk_scores.csv` — ICD-10 code list appended per patient as a sorted list for FHIR compatibility

### Key Decisions
| Decision | Rationale |
|---|---|
| ICD-10 applied at output layer only | SNOMED CT preserved throughout the analytical engine — ICD-10 is for reporting, not clinical logic |
| Explicit mapping table over simple dictionary | Preserves SNOMED-level clinical nuance even where multiple SNOMED codes share one ICD-10 code |
| UK ICD-10 conventions over ICD-10-CM | Portfolio targets NHS roles — UK ICD-10 5th Edition is the correct standard |
| JSON + CSV dual format for mapping table | CSV for human audit, JSON for programmatic use in FHIR export |
| Patient-level ICD-10 stored as list in memory | Enables direct iteration in FHIR export without string parsing |
| TNM stage codes simplified to C34.9 | UK ICD-10 does not encode TNM staging — unspecified bronchus and lung code used |
| ICD-10-CM sub-classifications not used | UK ICD-10 uses fewer decimal places — CM-specific trailing digits removed throughout |

### Reference Standards
ICD-10 codes are aligned with UK ICD-10 5th Edition conventions. Where UK ICD-10 and ICD-10-CM differ, UK conventions are applied. For enterprise deployment this module is designed to integrate with the NHS TRUD API for live SNOMED-to-ICD-10 mapping, replacing the static crosswalk with a dynamically validated terminology service.

### Outputs
- `data/reference/uk_icd10_reference.csv` — 115 unique UK ICD-10 codes used in the project
- `data/reference/snomed_to_icd10_map.csv` — 129-row explicit SNOMED-to-ICD-10 mapping table
- `data/reference/snomed_to_icd10_map.json` — same mapping in JSON format for FHIR pipeline
- `outputs/conditions_icd10_mapped.csv` — 8,376 condition rows with SNOMED and ICD-10 codes
- `outputs/patient_risk_scores.csv` — updated with patient-level ICD-10 code list

### Validation Results
- SNOMED codes in universe mapped to ICD-10 : 129 / 129 (100%)
- Condition rows mapped to ICD-10            : 8,376 / 8,376 (100%)
- Unmatched codes                            : 0

### Known Limitations
- Mapping table is manually curated — not validated against a live terminology service
- UK ICD-10 does not support TNM staging — lung cancer codes simplified to C34.9
- Some ICD-10 codes are shared across multiple SNOMED concepts — clinical nuance preserved at SNOMED level only
- Smoking coded as F17.1 (nicotine dependence) — UK ICD-10 does not distinguish daily from occasional tobacco use

### Next Sprint
Build FHIR export — produce patient-level FHIR R4 RiskAssessment JSON resources carrying SNOMED condition codes, ICD-10 group codes, risk scores, and segment assignments.


## Sprint 5 — FHIR R4 Export
**Dates:** 2026-04-01  
**Status:** Complete

### Goal
Export the full patient cohort as a FHIR R4 compliant Bundle resource, carrying SNOMED CT 
condition codes, UK ICD-10 administrative codes, risk scores, and segment assignments in a 
standard clinical interoperability format. Validate the bundle against both a custom Python 
structural validation layer and the official HL7 FHIR Validator R4.

### User Stories
- As a system integrator, I want patient risk data exported in FHIR R4 format so that it 
  can be consumed by NHS clinical systems without transformation.
- As a clinical coder, I want SNOMED CT and ICD-10 codes carried separately in each 
  Condition resource so that clinical and administrative coding systems can each consume 
  the appropriate terminology.
- As a reviewer, I want the FHIR bundle structurally validated so that conformance with 
  the R4 specification is demonstrable.

### Resource Design Decisions

**Why these four resource types:**

| Resource | Decision | Rationale |
|---|---|---|
| Patient | Included | Anchor resource — all other resources reference back to it |
| Encounter | Included | Enables Condition resources to reference their originating visit — mirrors real NHS FHIR implementations |
| Condition | Included | Core clinical payload — carries SNOMED CT and ICD-10 together |
| RiskAssessment | Included | Analytical output of the pipeline expressed in standard FHIR format |
| CarePlan / CareTeam | Excluded | Requires practitioner data not present in Synthea |
| Observation | Excluded | No lab or vitals data in the Synthea conditions file |

**Why Bundle type `collection`:**
A `collection` bundle is correct for file-based export. Bundle type `transaction` requires 
a live FHIR server to process — not appropriate for a portfolio file export.

**Why SNOMED CT as primary coding (`userSelected: true`):**
SNOMED CT drives clinical logic throughout the pipeline. ICD-10 is an administrative output 
derived at the output layer. The `userSelected` flag signals this distinction to any receiving 
system, consistent with NHS-recommended dual-coding patterns for Condition resources.

**Why URL-style fullUrl instead of UUID format:**
FHIR fullUrl can be any valid URI. URL-style fullUrls 
(`http://clinical-risk-pipeline/ResourceType/id`) provide explicit resource type namespacing 
without requiring valid UUID format for derived IDs such as encounter-date composites.

**Why encounter IDs are appended with START date:**
Seven encounters in the Synthea dataset share the same ENCOUNTER ID but have different START 
dates — a known Synthea data quality issue. Appending the START date guarantees fullUrl 
uniqueness across all 18,337 resources without requiring deduplication in the export pipeline.

**Why ICD-10 display names are corrected at runtime:**
A `DISPLAY_CORRECTIONS` dictionary applies official ICD-10 display names at export time 
rather than modifying the source mapping table. This separates clinical mapping decisions 
from FHIR formatting concerns and makes future corrections trivial.

**Why `Diabetes` SNOMED display was retained from Synthea:**
SNOMED code 44054006 is stored in the Synthea dataset as `Diabetes` without type 
specification. The HL7 validator rejects this in favour of `Type 2 diabetes mellitus`. 
However, the Synthea description does not confirm type — replacing it would introduce a 
clinical assumption not supported by the source data. The description has been intentionally 
preserved.

### Work Completed
- Loaded and cleaned the ICD-10 mapped conditions file — validated required columns, 
  removed duplicates, parsed dates
- Built encounter-level merge grouping by PATIENT, ENCOUNTER, and START date — 7,657 
  unique encounters from 8,376 condition rows
- 560 encounters contained 2+ SNOMED codes — manually verified as clinically valid 
  co-diagnoses (e.g. anaemia during pregnancy, pathological fracture with osteoporosis)
- Built FHIR R4 Bundle containing four resource types with narrative text blocks, 
  correct clinicalStatus logic, and dual SNOMED/ICD-10 coding separation
- Applied `DISPLAY_CORRECTIONS` map at runtime to align ICD-10 display names with 
  official terminology server expectations
- Applied runtime SNOMED display corrections for four codes with deprecated display strings
- Ran HL7 FHIR Validator R4 iteratively across 8 rounds, resolving issues progressively
- Validated all 18,337 resources against comprehensive Python structural validation suite
- Cross-validated FHIR bundle against all source analytical tables — 8 checks, all passed

### Validation Results
- Resources validated              : 18,337
- Structural Python validation     : ALL CHECKS PASSED
- Date format validation           : PASSED — all dates ISO 8601 YYYY-MM-DD
- Subject reference validation     : PASSED — all references match a Patient resource
- fullUrl uniqueness               : PASSED — 0 duplicates
- Cross-validation against source  : PASSED — patients, encounters, conditions, 
  RiskAssessments, SNOMED codes, patient IDs, risk scores, and segments all matched
- HL7 FHIR Validator R4            : 601 errors, 496 warnings, 1,152 notes
  - 97.7% error reduction from initial 26,458 across 8 iterative validation rounds
  - Remaining 601 errors: ~597 from intentionally preserved Diabetes SNOMED display, 
    ~4 from G43.7 and G89.2 not present in terminology server version 2019-covid-expanded
  - Remaining 496 warnings: inactive SNOMED concepts — all documented
  - 1,152 notes: RiskAssessment binding has no source in FHIR R4 spec — not fixable

### Resource Structure
| Resource | Count | Content |
|---|---|---|
| Patient | 1,152 | ID, gender, birthDate, narrative |
| Encounter | 7,657 | Status, class, subject reference, period, narrative |
| Condition | 8,376 | SNOMED CT + ICD-10 separated, encounter reference, clinicalStatus, onsetDateTime, narrative |
| RiskAssessment | 1,152 | Risk score, tier, primary segment, all segments, narrative |
| **Total** | **18,337** | |

### Outputs
- `outputs/conditions_icd10_cleaned.csv` — cleaned condition-level input
- `outputs/conditions_encounter_merged.csv` — encounter-level merged conditions (7,657 rows)
- `outputs/fhir/clinical_risk_bundle.json` — FHIR R4 Bundle, 18,337 entries, ~20MB
- `outputs/fhir/fhir_validation_report.txt` — HL7 FHIR Validator R4 output (final run)

### Known Limitations
- `Diabetes` SNOMED display (44054006) retained from Synthea source — validator expects 
  `Type 2 diabetes mellitus` but the Synthea description does not specify type; replacing 
  it would introduce a clinical assumption not supported by the source data. This accounts 
  for ~597 of the remaining 601 errors.
- ICD-10 codes G43.7 (Chronic migraine) and G89.2 (Chronic pain) flagged as unknown by 
  the HL7 terminology server validating against version 2019-covid-expanded. Both are valid 
  UK ICD-10 5th Edition codes — the issue is a terminology server version mismatch, not an 
  error in the mapping.
- ICD-10 codes J30.9 (Allergic rhinitis), S61.4 (Open wound of hand), and R91.8 (Abnormal 
  findings on imaging) also flagged as unknown in the 2019-covid-expanded version for the 
  same reason.
- Four SNOMED concepts in the Synthea dataset are flagged as inactive in the current SNOMED 
  CT UK Clinical Edition: 15777000 (Prediabetes), 55680006 (Drug overdose), 422034002 
  (Diabetic retinopathy associated with type II diabetes), and 1551000119108 
  (Nonproliferative diabetic retinopathy due to type 2 diabetes). These generate 496 
  warnings. In a production NHS system, inactive concepts would be replaced with their 
  active successors using the SNOMED CT Association Reference Set from the NHS TRUD UK 
  Clinical Edition release. Successor codes identified: 714628002, 295125004, 312903003, 
  and 312904009 respectively. Implementation deferred as it requires NHS TRUD licence access.
- SNOMED concept 156073000 description retained as Fetus with unknown complication. The 
  validator suggests Complete miscarriage but these are clinically distinct conditions — the 
  Synthea description has been preserved to reflect the source data accurately.
- 1,152 RiskAssessment binding notes — prediction outcome binding has no defined value set 
  in the FHIR R4 specification and cannot be validated. This is a specification gap, not an 
  implementation error.
- Encounter class defaulted to AMB (ambulatory) — Synthea does not provide encounter class 
  data; in a production NHS system this would be derived from the encounter type.
- Bundle type `collection` is not transactional — resources cannot be directly POSTed to a 
  FHIR server without conversion to `transaction` type.
- Patient resources carry minimal demographics — name, address, and contact details excluded.
- RiskAssessment uses `probabilityDecimal` for risk score — in a production system this 
  would map to a validated risk scale such as QRisk3.

### Next Sprint
Write README, clinical problem log, and finalise GitHub repository for portfolio submission.