# Known Limitations

## Synthetic Data
All outputs are derived from Synthea-generated synthetic EHR data. The clinical distributions, risk scores, and segment assignments reflect synthetic population patterns — not real NHS epidemiology. This pipeline is not validated for clinical use and should not be used in any clinical decision-making context.

---

## Sprint 1 — SNOMED Condition Mapping
- Mapping table is manually curated — not validated against a live terminology service. A production system would use the NHS TRUD SNOMED CT UK Clinical Edition with dynamic FHIR ValueSet queries.
- Wide table uses binary presence flags — recurrence within a category is not captured at this layer.

---

## Sprint 2 — Risk Scoring
- Scoring uses binary category presence flags — severity within a category is not captured.
- Medication counts reflect cumulative historical prescriptions rather than active concurrent medications.
- Recurrence bonus is limited to five age-sensitive categories — other chronic conditions with high recurrence are not rewarded.
- Age adjustment uses fixed band multipliers — a continuous age function would be more precise.
- Tier thresholds are empirically derived from this cohort and may not generalise to other populations.
- Scoring weights are clinician-defined — not statistically validated against clinical outcomes.

---

## Sprint 3 — Patient Segmentation
- Midlife Escalation uses total encounter count — in Synthea this includes routine wellness visits and administrative contacts. A real NHS implementation would filter to unplanned or condition-related encounters using SUS data.
- `category_count` includes all 15 categories equally, including minor ones such as MALE REPRODUCTIVE and ENT. A patient qualifying on minor categories alone will have a low risk tier. The correct clinical interpretation requires reading segment alongside risk tier.
- Segment definitions are cohort-specific and may require recalibration for different populations.
- No temporal segmentation — patients are classified on lifetime condition burden, not current clinical status.
- Cardio-Metabolic segment is small (53 patients, 4.6%) due to strict definition — a broader definition including endocrinology would inflate the segment at the cost of clinical precision.

---

## Sprint 4 — ICD-10 Mapping
- Mapping table is manually curated — not validated against a live terminology service. For enterprise deployment this module is designed to integrate with the NHS TRUD API.
- UK ICD-10 does not support TNM staging — lung cancer codes simplified to C34.9.
- Some ICD-10 codes are shared across multiple SNOMED concepts — clinical nuance preserved at SNOMED level only.
- Tobacco use coded as F17.1 — UK ICD-10 does not distinguish daily from occasional tobacco use at this code level.

---

## Sprint 5 — FHIR Export
- `Diabetes` SNOMED display (44054006) retained from Synthea source — the HL7 validator expects "Type 2 diabetes mellitus" but Synthea does not specify type; replacing it would introduce a clinical assumption not supported by the source data. This accounts for ~597 of the remaining 601 validator errors.
- Four SNOMED concepts flagged as inactive in the current SNOMED CT UK Clinical Edition: 15777000, 55680006, 422034002, and 1551000119108. Active successor codes identified but implementation requires NHS TRUD licence access.
- ICD-10 codes G43.7 and G89.2 flagged as unknown by the HL7 terminology server — valid UK ICD-10 5th Edition codes, terminology server version mismatch only.
- Encounter class defaulted to AMB (ambulatory) — Synthea does not provide encounter class data.
- Bundle type `collection` is not transactional — resources cannot be directly POSTed to a FHIR server without conversion to `transaction` type.
- Patient resources carry minimal demographics — name, address, and contact details excluded.
- `probabilityDecimal` carries raw risk score — confirmed schema-conformant by HL7 FHIR Validator. A production implementation would use a validated risk scale such as QRisk3.
- 1,152 RiskAssessment binding notes — prediction outcome binding has no defined value set in FHIR R4 specification. This is a specification gap, not an implementation error.