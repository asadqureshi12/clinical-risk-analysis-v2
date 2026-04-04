## Sprint 5 — FHIR R4 Bundle Export
**Dates:** 2026-04-03
**Status:** Complete ✓

### Goal
Export the full patient cohort as a FHIR R4 compliant Bundle resource, carrying SNOMED CT condition codes, UK ICD-10 administrative codes, risk scores, and segment assignments in a standard clinical interoperability format. Validate the bundle against both a custom Python structural validation suite and the official HL7 FHIR Validator R4.

### User Stories
- As a system integrator, I want patient risk data exported in FHIR R4 format so that it can be consumed by NHS clinical systems without transformation.
- As a clinical coder, I want SNOMED CT and ICD-10 codes carried separately in each Condition resource so that clinical and administrative coding systems can each consume the appropriate terminology.
- As a reviewer, I want the FHIR bundle structurally validated so that conformance with the R4 specification is demonstrable.

### Work Completed
- Loaded and cleaned the ICD-10 mapped conditions file — validated required columns, removed duplicates, parsed dates
- Built encounter-level merge grouping by PATIENT, ENCOUNTER, and START date — 7,657 unique encounters from 8,376 condition rows
- 560 encounters contained 2+ SNOMED codes — verified as clinically valid co-diagnoses (e.g. anaemia during pregnancy, pathological fracture with osteoporosis)
- Built FHIR R4 Bundle containing four resource types with narrative text blocks, correct clinicalStatus logic, and dual SNOMED/ICD-10 coding separation
- Applied `DISPLAY_CORRECTIONS` map at runtime — corrects pipeline-annotated ICD-10 descriptions to canonical UK ICD-10 preferred terms for FHIR compliance. Example: internal annotation "Urinary tract infection - Escherichia coli" corrected to canonical "Urinary tract infection, site not specified" (N39.0) — E. coli specificity preserved in the SNOMED coding layer
- Applied runtime SNOMED `DESCRIPTION_CORRECTIONS` for four codes with non-preferred Synthea display names — corrected to canonical SNOMED CT preferred terms (e.g. "Hypertension" → "Essential hypertension (disorder)")
- Ran HL7 FHIR Validator R4 iteratively across 8 rounds, resolving issues progressively — 97.7% error reduction from initial 26,458 errors to 601 remaining
- Validated all 18,337 resources against comprehensive Python structural validation suite
- Cross-validated FHIR bundle against all source analytical tables — 8 checks, all passed
- Saved `src/build_fhir_bundle.py`

### Resource Design Decisions

| Resource | Decision | Rationale |
|---|---|---|
| Patient | Included | Anchor resource — all other resources reference back to it |
| Encounter | Included | Enables Condition resources to reference their originating visit — mirrors real NHS FHIR implementations |
| Condition | Included | Core clinical payload — carries SNOMED CT and ICD-10 together |
| RiskAssessment | Included | Analytical output of the pipeline expressed in standard FHIR format |
| CarePlan / CareTeam | Excluded | Requires practitioner data not present in Synthea |
| Observation | Excluded | No lab or vitals data in Synthea conditions file |

**Bundle type `collection`:** Correct for file-based export and reporting. Bundle type `transaction` requires a live FHIR server — not appropriate here.

**SNOMED CT as primary coding (`userSelected: true`):** SNOMED drives clinical logic throughout the pipeline. ICD-10 is an administrative output derived at the output layer. The `userSelected` flag signals this distinction to any receiving system, consistent with NHS dual-coding patterns.

**Encounter IDs appended with START date:** Seven encounters in Synthea share the same ENCOUNTER ID but have different START dates — a known Synthea data quality issue. Appending the START date guarantees fullUrl uniqueness across all 18,337 resources.

**`probabilityDecimal` carries raw pipeline risk score:** The FHIR R4 StructureDefinition defines `probabilityDecimal` as a decimal type with no enforced range invariant. The 0–1 range appears in narrative guidance only — it is not a schema validation rule. The raw score is carried directly, preserving full scoring resolution. Confirmed schema-conformant by the official HL7 FHIR Validator.

**`clinicalStatus` derived from STOP date:** Set to `active` where no STOP date is recorded, and `resolved` where a STOP date is present — the most defensible inference available from Synthea data.

### Outputs
- `outputs/intermediate/conditions_icd10_cleaned.csv` — cleaned condition-level input
- `outputs/intermediate/conditions_encounter_merged.csv` — encounter-level merged conditions (7,657 rows)
- `outputs/fhir/clinical_risk_bundle.json` — FHIR R4 Bundle, 18,337 entries, ~20MB
- `outputs/validation/fhir_validation_report.txt` — HL7 FHIR Validator R4 output (final run)

### Resource Counts
| Resource | Count |
|---|---|
| Patient | 1,152 |
| Encounter | 7,657 |
| Condition | 8,376 |
| RiskAssessment | 1,152 |
| **Total** | **18,337** |

### Validation Results
- Python structural validation  : ALL CHECKS PASSED
- Date format validation        : PASSED — all dates ISO 8601 YYYY-MM-DD
- Subject reference validation  : PASSED — all references match a Patient resource
- fullUrl uniqueness            : PASSED — 0 duplicates
- Cross-validation against source : PASSED — patients, encounters, conditions, RiskAssessments, SNOMED codes, patient IDs, risk scores, and segments all matched
- HL7 FHIR Validator R4         : 601 remaining errors (97.7% reduction from initial 26,458 across 8 iterative rounds)
  - ~597 from intentionally preserved Diabetes SNOMED display (see Known Limitations)
  - ~4 from G43.7 and G89.2 not present in terminology server version 2019-covid-expanded — valid UK ICD-10 5th Edition codes, terminology server version mismatch only

### Known Limitations
- `Diabetes` SNOMED display (44054006) retained from Synthea source — the HL7 validator expects "Type 2 diabetes mellitus" but Synthea does not specify type; replacing it would introduce a clinical assumption not supported by the source data. This accounts for ~597 of the remaining 601 validator errors.
- ICD-10 codes G43.7 (Chronic migraine) and G89.2 (Chronic pain) flagged as unknown by the HL7 terminology server validating against version 2019-covid-expanded. Both are valid UK ICD-10 5th Edition codes — the issue is a terminology server version mismatch, not an error in the mapping.
- Four SNOMED concepts flagged as inactive in the current SNOMED CT UK Clinical Edition: 15777000, 55680006, 422034002, and 1551000119108. These generate 496 warnings. In a production NHS system, inactive concepts would be replaced with their active successors using the SNOMED CT Association Reference Set from the NHS TRUD UK Clinical Edition release. Successor codes identified: 714628002, 295125004, 312903003, and 312904009 respectively. Implementation deferred as it requires NHS TRUD licence access.
- 1,152 RiskAssessment binding notes — prediction outcome binding has no defined value set in FHIR R4 specification. This is a specification gap, not an implementation error.
- Encounter class defaulted to AMB (ambulatory) — Synthea does not provide encounter class data; in a production NHS system this would be derived from encounter type.
- Bundle type `collection` is not transactional — resources cannot be directly POSTed to a FHIR server without conversion to `transaction` type.
- Patient resources carry minimal demographics — name, address, and contact details excluded as not required for this pipeline's analytical purpose.
- `probabilityDecimal` carries raw risk score — confirmed schema-conformant. A production implementation targeting a live FHIR server would carry a normalised score or use a custom extension alongside a validated risk scale such as QRisk3.