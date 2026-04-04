## Sprint 1 — SNOMED Condition Mapping
**Dates:** 2026-03-29
**Status:** Complete ✓

### Goal
Establish the foundational condition mapping layer for the clinical risk pipeline.
All downstream modules (risk scorer, segmentation, ICD-10 mapping, FHIR export) depend on this sprint's output.

### User Stories
- As a data analyst, I want every patient condition mapped to a clinical category so that I can perform meaningful cohort-level analysis.
- As a clinician, I want SNOMED CT codes used as the primary terminology throughout the pipeline so that the analysis remains NHS-credible and interoperable.

### Work Completed
- Loaded and deduplicated raw Synthea conditions dataset — 8,376 rows, 129 unique SNOMED codes
- Built `outputs/snomed_conditions_universe.csv` — a curated mapping of all 129 SNOMED codes to 15 clinical categories, aligned with NHS specialty groupings
- Categories with insufficient clinical weight (DENTAL, ALLERGIC REACTION, HEMATOLOGY, DERMATOLOGY) consolidated into OTHER with documented rationale
- PSYCHIATRY and DRUG INTERACTIONS / ADDICTION retained as distinct categories despite low code counts (3 each) due to independent clinical significance
- Category name corrected from DIABETES COMPLICATIONS to DIABETES & COMPLICATIONS — the original name implied complications only; the corrected name accurately reflects the full diabetes domain including primary diagnosis codes
- Added `is_acute` binary flag to universe CSV — consumed in Sprint 3 for Acute Overlay segment definition
- Saved `src/build_snomed_universe.py` — produces wide-format and long-format patient-level output tables
- Wide format: one row per patient, binary category flags + category count
- Long format: one row per patient-category pair for dashboard use
- Identified and fixed a latent merge bug: an earlier implementation joined on both CODE and DESCRIPTION — this caused 302 silent unmatched rows for Hypertension (SNOMED 59621000) due to a display name discrepancy between Synthea and the universe CSV. Fixed to code-only merge.
- Validated 100% mapping coverage — 0 unmatched condition rows

### Key Decisions
| Decision | Rationale |
|---|---|
| SNOMED throughout the pipeline | Preserves clinical granularity — ICD-10 reserved for output layer only |
| Code-based mapping (SNOMED CODE integer) | Eliminates ambiguity from description variation — a description-based merge caused 302 silent failures for Hypertension |
| Custom CSV mapping file | Transparent and auditable at this scale — production system would use NHS TRUD terminology service |
| DIABETES & COMPLICATIONS category name | Corrected from DIABETES COMPLICATIONS — the full category covers primary diabetes diagnosis codes, not only end-organ complications |
| Recurrences retained in raw data | Same condition on different dates represents a distinct clinical episode |

### Outputs
- `outputs/snomed_conditions_universe.csv` — 129 codes, 15 categories, is_acute flag
- `outputs/patient_conditions_wide.csv` — patient-level binary category flags
- `outputs/patient_conditions_long.csv` — patient-category pairs for visualisation

### Validation Results
- Condition rows processed : 8,376
- Matched to category     : 8,376 (100%)
- Unmatched rows          : 0
- Average categories per patient : 4.1 (clinically plausible for a mixed-age Synthea cohort)

### Known Limitations
- Wide table uses binary presence flags — recurrence within a category is not captured at this layer (addressed in Sprint 2 recurrence bonus)
- Mapping table is manually curated — a production system would use the NHS TRUD SNOMED CT UK Clinical Edition with dynamic FHIR ValueSet queries
- No clinical severity weighting within categories at this stage — severity is handled by category weights in Sprint 2

### Next Sprint
Build `compute_risk_scores.py` — assign clinical risk weights to condition categories and produce a patient-level composite risk score across six scoring layers.