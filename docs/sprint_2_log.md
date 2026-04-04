## Sprint 2 — Clinical Risk Scoring
**Dates:** 2026-03-31
**Status:** Complete ✓

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
  - Layer 1 — Base score: category weights reflecting NHS resource burden and clinical severity
  - Layer 2 — Multimorbidity tier: graduated bonus at 2, 5, and 8 condition categories
  - Layer 3 — Age adjustment: upweights five high-burden categories for patients aged 41–65 (×1.25) and 66+ (×1.50)
  - Layer 4 — Polypharmacy bonus: tiered at 25, 50, and 100 medications (capped at 100)
  - Layer 5 — Utilisation bonus: tiered at 20, 50, and 100 total encounters
  - Layer 6 — Recurrence bonus: +0.5 per age-sensitive category with 3+ episodes within that category
- Validated score distribution — 0 NaN scores, 0 negative scores
- Calibrated tier thresholds against observed score distribution using 75th and 95th percentile cut-points
- Produced summary tables and score distribution visualisation
- Exported three output files to `outputs/`
- Saved `src/compute_risk_scores.py`

### Key Decisions
| Decision | Rationale |
|---|---|
| Six scoring layers | Each layer captures a distinct clinical signal — no single proxy measure is sufficient |
| Weights clinician-defined | Derived from clinical intuition and NHS resource burden — not statistically derived; intentionally transparent and auditable |
| Multimorbidity tier bonus | Graduated scale reflects non-linear complexity of multiple concurrent conditions — aligned with NICE multimorbidity guidance |
| Age adjustment limited to five categories | Age amplifies risk for serious systemic conditions only — applying it to ENT or TRAUMA would be clinically inappropriate |
| Recurrence limited to age-sensitive categories | Recurrence signals poorly controlled disease in chronic high-burden conditions — less meaningful for episodic or minor categories |
| Medication outlier cap at 100 | A small number of patients exceeded 100 medications — these represent cumulative historical prescriptions, not concurrent medications; cap prevents score distortion |
| Age reference date set to 2020-04-25 | Derived from the latest condition record in the dataset — ensures age is consistent with the observation window and reproducible |
| Tier thresholds at 75th and 95th percentiles | Empirically derived from observed score distribution — Critical (>95th) is intentionally small to reflect genuinely high-complexity patients |

### Outputs
- `outputs/patient_risk_scores.csv` — full scored patient table including all scoring layers and risk tier
- `outputs/tier_summary.csv` — patient counts and percentages per risk tier
- `outputs/category_by_tier.csv` — top condition categories per tier

### Validation Results
- NaN scores    : 0 — PASSED
- Negative scores : 0 — PASSED
- Score range   : 0.5 – 42.5
- Mean score    : 11.44

### Tier Distribution
| Tier | Threshold | Patients | % |
|---|---|---|---|
| Critical | ≥ 27 (> 95th percentile) | 56 | 4.9% |
| High | ≥ 17 (> 75th percentile) | 227 | 19.7% |
| Medium | ≥ 5 | 605 | 52.5% |
| Low | < 5 | 264 | 22.9% |

### Known Limitations
- Scoring uses binary category presence flags — severity within a category is not captured
- Medication counts reflect cumulative historical prescriptions rather than active concurrent medications
- Recurrence bonus is limited to five age-sensitive categories — other chronic conditions with high recurrence are not rewarded
- Age adjustment uses fixed band multipliers — a continuous age function would be more precise
- Tier thresholds are empirically derived from this cohort and may not generalise to other populations

### Next Sprint
Build `assign_segments.py` — group patients into clinically meaningful cohorts based on condition profile, demographics, and acute burden for targeted intervention planning.