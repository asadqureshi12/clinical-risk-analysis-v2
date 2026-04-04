import pandas as pd
import src.build_snomed_universe as step1
import src.compute_risk_scores   as step2
import src.assign_segments       as step3
import src.map_icd10             as step4
import src.build_fhir_bundle     as step5

CONDITIONS_PATH  = "data/conditions.csv"
PATIENTS_PATH    = "data/patients.csv"
MEDICATIONS_PATH = "data/medications.csv"
ENCOUNTERS_PATH  = "data/encounters.csv"
UNIVERSE_PATH    = "outputs/snomed_conditions_universe.csv"
MAP_PATH         = "data/reference/snomed_to_icd10_map.csv"
ENCOUNTER_PATH   = "outputs/intermediate/conditions_encounter_merged.csv"
SEGMENTS_PATH    = "outputs/patient_segments.csv"
OUTPUT_DIR       = "outputs"

def main():
    print("══ Clinical Risk Analysis Pipeline v2 ══════════════")

    print("\n── Sprint 1 : SNOMED Condition Mapping ───────────────")
    conditions = pd.read_csv(CONDITIONS_PATH)
    universe   = pd.read_csv(UNIVERSE_PATH)
    wide, long, merged = step1.run(
        conditions_path=CONDITIONS_PATH,
        universe_path=UNIVERSE_PATH,
        output_dir=OUTPUT_DIR
    )

    print("\n── Sprint 2 : Risk Scoring ───────────────────────────")
    patients    = pd.read_csv(PATIENTS_PATH)
    medications = pd.read_csv(MEDICATIONS_PATH)
    encounters  = pd.read_csv(ENCOUNTERS_PATH)
    scored = step2.run(
        wide=wide,
        merged=merged,
        patients=patients,
        medications=medications,
        encounters=encounters,
        output_dir=OUTPUT_DIR
    )

    print("\n── Sprint 3 : Patient Segmentation ───────────────────")
    scored, segment_summary = step3.run(
        scored=scored,
        conditions=conditions,
        universe_path=UNIVERSE_PATH,
        output_dir=OUTPUT_DIR
    )

    print("\n── Sprint 4 : ICD-10 Mapping ─────────────────────────")
    conditions_mapped, scored_with_icd10, universe = step4.run(
        conditions=conditions,
        universe=universe,
        universe_path=UNIVERSE_PATH,
        map_path=MAP_PATH,
        scored=scored,
        output_dir=OUTPUT_DIR
    )

    print("\n── Sprint 5 : FHIR R4 Bundle Export ──────────────────")
    bundle = step5.run(
        conditions_path=ENCOUNTER_PATH,
        patients_path=PATIENTS_PATH,
        scored_segments_path=SEGMENTS_PATH,
        map_path=MAP_PATH,
        universe_path=UNIVERSE_PATH,
        output_dir=OUTPUT_DIR
    )

    print("\n══ Pipeline complete ══════════════════════════════════")

if __name__ == "__main__":
    main()
