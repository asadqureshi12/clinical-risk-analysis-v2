## Sprint 4 — ICD-10 Mapping
**Dates:** 2026-04-02
**Status:** Complete ✓

### Goal
Translate SNOMED CT condition codes to UK ICD-10 5th Edition codes at the output layer, producing a clinically accurate and auditable terminology crosswalk. ICD-10 codes are applied for reporting and FHIR compatibility whilst SNOMED CT remains the primary terminology throughout the analytical engine.

### User Stories
- As a data analyst, I want each condition mapped to a UK ICD-10 code so that outputs are compatible with NHS administrative reporting systems.
- As a clinical coder, I want SNOMED-to-ICD-10 mappings to preserve diagnostic nuance so that conditions sharing an ICD-10 code are still distinguishable at the SNOMED level.
- As a reviewer, I want the mapping table stored as a versioned reference file so that the crosswalk is auditable and reproducible.

### Work Completed
- Built a UK ICD-10 reference table (`data/reference/uk_icd10_reference.csv`) — 107 codes aligned with UK ICD-10 5th Edition conventions
- Built an explicit SNOMED-to-ICD-10 mapping table (`data/reference/snomed_to_icd10_map.csv`) — one row per SNOMED code, with clinical annotation in the description field preserving diagnostic nuance
- Saved mapping table in JSON format (`data/reference/snomed_to_icd10_map.json`) for programmatic use in the FHIR export pipeline
- Applied mapping to `snomed_conditions_universe.csv` — all 129 SNOMED codes mapped, 0 unmatched
- Applied mapping to raw conditions dataset — all 8,376 condition rows mapped, 0 unmatched
- Exported `outputs/conditions_icd10_mapped.csv` — condition-level table with SNOMED and ICD-10 codes alongside
- Updated `outputs/patient_risk_scores.csv` — ICD-10 code list appended per patient as a sorted list for FHIR compatibility
- Corrected Hypertension SNOMED description to canonical preferred term "Essential hypertension (disorder)" — Synthea uses the shortened display name "Hypertension" which caused silent merge failure on the description-key join used in Sprint 5
- Saved `src/map_icd10.py`


### Key Decisions
| Decision | Rationale |
|---|---|
| ICD-10 applied at output layer only | SNOMED CT preserved throughout the analytical engine — ICD-10 is for reporting, not clinical logic |
| UK ICD-10 5th Edition | NHS standard — not ICD-10-CM (US). The editions differ in code structure and preferred terminology; using the wrong edition would signal unfamiliarity with NHS coding practice |
| Explicit mapping table over simple dictionary | Preserves SNOMED-level clinical nuance even where multiple SNOMED codes share one ICD-10 code |
| Merge on CODE + DESCRIPTION | Intentional — multiple SNOMED codes map to the same ICD-10 code; description-level join preserves specificity at the SNOMED layer |
| JSON + CSV dual format for mapping table | CSV for human audit and version control; JSON for programmatic use in FHIR export |
| SNOMED category assignments do not mirror ICD-10 chapter structure | Hyperlipidaemia (E78.5) sits in ICD-10 Chapter IV but is assigned to CARDIOVASCULAR in the SNOMED layer as a cardiovascular risk factor — the two layers serve different purposes |
| Tobacco use assigned to PULMONOLOGY | Coded as F17.1 in ICD-10 (mental and behavioural disorder) but assigned to PULMONOLOGY in the SNOMED layer as a pulmonary risk factor — ICD-10 chapter placement does not override clinical categorisation logic |
| Z99.9 fallback row included | Defensive coding practice — triggered zero times, confirmed by validation check |

### Outputs
- `data/reference/uk_icd10_reference.csv` — 107 unique UK ICD-10 codes
- `data/reference/snomed_to_icd10_map.csv` — 129-row explicit SNOMED-to-ICD-10 mapping table
- `data/reference/snomed_to_icd10_map.json` — same mapping in JSON format for FHIR pipeline
- `outputs/conditions_icd10_mapped.csv` — 8,376 condition rows with SNOMED and ICD-10 codes
- `outputs/patient_risk_scores.csv` — updated with patient-level ICD-10 code list

### Validation Results
- SNOMED codes mapped to ICD-10  : 129 / 129 (100%)
- Condition rows mapped to ICD-10 : 8,376 / 8,376 (100%)
- Unmatched codes                 : 0 — PASSED (Z99.9 fallback never triggered)

### Known Limitations
- Mapping table is manually curated — not validated against a live terminology service. For enterprise deployment this module is designed to integrate with the NHS TRUD API for live SNOMED-to-ICD-10 mapping
- UK ICD-10 does not support TNM staging — lung cancer codes simplified to C34.9 (malignant neoplasm of bronchus and lung, unspecified)
- Some ICD-10 codes are shared across multiple SNOMED concepts — clinical nuance preserved at SNOMED level only
- Tobacco use coded as F17.1 — UK ICD-10 does not distinguish daily from occasional tobacco use at this code level

### Next Sprint
Build `build_fhir_bundle.py` — produce a FHIR R4 compliant Bundle resource carrying Patient, Encounter, Condition, and RiskAssessment resources with dual SNOMED and ICD-10 coding.