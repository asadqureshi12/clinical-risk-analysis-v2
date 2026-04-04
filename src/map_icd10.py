import pandas as pd
import json
import os

FALLBACK_ICD10_CODE = "Z99.9"
FALLBACK_ICD10_DESC = "Unknown SNOMED code - not in mapping table"
HYPERTENSION_SNOMED_CODE = 59621000
HYPERTENSION_CORRECT_DESC = "Essential hypertension (disorder)"


def load_mapping(map_path):
    df_map = pd.read_csv(map_path)
    print(f"[icd10_mapper] Mapping rows loaded       : {len(df_map)}")
    return df_map


def enrich_universe(universe, df_map, universe_path):
    for col in ["icd10_code", "icd10_desc"]:
        if col in universe.columns:
            universe = universe.drop(columns=[col])

    universe = universe.merge(
        df_map[["snomed_code", "icd10_code", "icd10_desc"]].rename(columns={"snomed_code": "CODE"}),
        on="CODE",
        how="left"
    )

    universe.loc[universe["CODE"] == HYPERTENSION_SNOMED_CODE, "DESCRIPTION"] = HYPERTENSION_CORRECT_DESC

    universe.to_csv(universe_path, index=False)
    print(f"[icd10_mapper] Universe enriched         : {len(universe)} codes")
    print(f"[icd10_mapper] Codes with ICD-10         : {universe['icd10_code'].notna().sum()}")
    print(f"[icd10_mapper] Codes without ICD-10      : {universe['icd10_code'].isna().sum()}")
    return universe


def map_conditions(conditions, universe):
    conditions_mapped = conditions.merge(
        universe[["CODE", "DESCRIPTION", "CATEGORY", "icd10_code", "icd10_desc"]],
        on=["CODE", "DESCRIPTION"],
        how="left"
    )

    unmapped = conditions_mapped["icd10_code"].isna().sum()
    if unmapped > 0:
        print(f"[icd10_mapper] WARNING: {unmapped} rows unmapped — applying {FALLBACK_ICD10_CODE} fallback")
        conditions_mapped["icd10_code"] = conditions_mapped["icd10_code"].fillna(FALLBACK_ICD10_CODE)
        conditions_mapped["icd10_desc"] = conditions_mapped["icd10_desc"].fillna(FALLBACK_ICD10_DESC)
    else:
        print(f"[icd10_mapper] Unmapped fallback check   : PASSED — all codes mapped")

    print(f"[icd10_mapper] Condition rows mapped     : {len(conditions_mapped)}")
    return conditions_mapped


def build_patient_summary(conditions_mapped, scored):
    patient_icd10_summary = (
        conditions_mapped.groupby("PATIENT")["icd10_code"]
        .apply(lambda x: sorted(x.dropna().unique().tolist()))
        .reset_index()
        .rename(columns={"icd10_code": "icd10_codes_all"})
    )

    scored_with_icd10 = scored.merge(patient_icd10_summary, on="PATIENT", how="left")
    print(f"[icd10_mapper] Patients with ICD-10 summary : {len(scored_with_icd10)}")
    return scored_with_icd10


def run(conditions, universe, universe_path, map_path, scored, output_dir="outputs"):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("data/reference", exist_ok=True)

    df_map = load_mapping(map_path)
    universe = enrich_universe(universe, df_map, universe_path)
    conditions_mapped = map_conditions(conditions, universe)
    scored_with_icd10 = build_patient_summary(conditions_mapped, scored)

    conditions_path = os.path.join(output_dir, "conditions_icd10_mapped.csv")
    conditions_mapped.to_csv(conditions_path, index=False)

    scored_export = scored_with_icd10.copy()
    scored_export["icd10_codes_all"] = scored_export["icd10_codes_all"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) else x
    )
    scores_path = os.path.join(output_dir, "patient_risk_scores.csv")
    scored_export.to_csv(scores_path, index=False)

    print(f"\n[icd10_mapper] Exported : {conditions_path}")
    print(f"[icd10_mapper] Exported : {scores_path}")

    return conditions_mapped, scored_with_icd10, universe
