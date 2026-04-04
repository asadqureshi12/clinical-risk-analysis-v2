# Clinical Methodology

## Overview
This pipeline was designed around a core principle: clinical reasoning drives architecture. Every structural decision — terminology layering, scoring weights, segmentation criteria — was made by a clinician and documented with explicit rationale. The pipeline is not a black box; every output is traceable to a documented decision.

---

## Terminology Architecture
SNOMED CT is used as the native clinical terminology throughout the entire analytical engine. ICD-10 is applied exclusively at the output layer for administrative reporting and FHIR export compatibility.

This separation is deliberate and clinically important. SNOMED CT carries the granularity required for meaningful risk analysis — distinguishing, for example, proliferative from non-proliferative diabetic retinopathy, or E. coli UTI from recurrent UTI. ICD-10 at this level of specificity would collapse these into the same code, losing the clinical signal entirely.

UK ICD-10 5th Edition is used throughout — not ICD-10-CM (US standard). This distinction matters for any NHS-facing deployment.

---

## Risk Scoring Philosophy
The six-layer scoring model was designed to capture distinct clinical signals that no single proxy measure can represent alone:

- **Condition burden** (base score) — what conditions does the patient have, and how serious are they
- **Multimorbidity** (tier bonus) — the non-linear complexity of managing multiple concurrent conditions
- **Age** (adjustment) — applied selectively to conditions where age is a clinically established risk amplifier
- **Polypharmacy** (bonus) — an independent risk marker for adverse events and care complexity
- **Utilisation** (bonus) — a proxy for disease instability and unmet need
- **Recurrence** (bonus) — distinguishes active recurring conditions from resolved historical ones

Weights are clinician-defined and intentionally transparent. This is not a statistically derived model — it is a clinically reasoned one, designed to be auditable and defensible in an NHS context.

---

## Segmentation Philosophy
Risk scores quantify severity. Segments identify the clinical pattern driving that severity. The two dimensions are designed to be read together — a segment label without a risk tier is incomplete, and a risk tier without a segment label is non-specific.

The five segments were designed to map onto recognisable NHS care pathway categories:
- **Cardio-Metabolic** — cardiovascular and diabetes co-management pathway
- **Multimorbid Frail** — frailty and complex care pathway
- **Midlife Escalation** — primary prevention and long-term condition management
- **Acute Overlay** — acute and urgent care pathway
- **Low Risk Stable** — routine primary care

Priority-based assignment ensures every patient receives the most clinically specific label available. The `all_segments` column preserves all qualifying segments for analytical use — no clinical information is discarded by the priority hierarchy.

---

## ICD-10 Mapping Philosophy
The SNOMED-to-ICD-10 mapping is explicit and manually curated — one row per SNOMED code, with clinical annotation in the description field. Where multiple SNOMED codes share a single ICD-10 code, clinical granularity is preserved at the SNOMED layer and the ICD-10 code carries only the precision that the UK 5th Edition standard supports.

SNOMED category assignments deliberately do not mirror ICD-10 chapter structure. A condition is assigned to the category that best represents its clinical risk relevance to the pipeline — not its administrative classification in ICD-10.

---

## FHIR Export Philosophy
The FHIR R4 bundle is designed as a reporting artefact, not a server transaction. Bundle type `collection` is correct for this use case. Every Condition resource carries dual coding — SNOMED CT as the primary clinical terminology (`userSelected: true`) and UK ICD-10 as the administrative layer (`userSelected: false`) — consistent with NHS-recommended dual-coding patterns.

The bundle was validated iteratively against the official HL7 FHIR Validator R4 across eight rounds, achieving a 97.7% error reduction. Remaining issues are fully documented in `docs/sprint_5_log.md` and are either intentional clinical decisions or terminology server version mismatches — not structural errors.