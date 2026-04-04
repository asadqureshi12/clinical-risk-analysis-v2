import json
import os
import re
import pandas as pd
from datetime import datetime, timezone
from collections import defaultdict

DISPLAY_CORRECTIONS = {
    "N39.0":  "Urinary tract infection, site not specified",
    "E11.9":  "Type 2 diabetes mellitus : Without complications",
    "E11.2":  "Type 2 diabetes mellitus : With renal complications",
    "E11.3":  "Type 2 diabetes mellitus : With ophthalmic complications",
    "E11.4":  "Type 2 diabetes mellitus : With neurological complications",
    "O03.9":  "Spontaneous abortion : Complete or unspecified, without complication",
    "I48.9":  "Atrial fibrillation and atrial flutter, unspecified",
    "I46.9":  "Cardiac arrest, unspecified",
    "R73.0":  "Abnormal glucose tolerance test",
    "G30.9":  "Alzheimer disease, unspecified",
    "G30.0":  "Alzheimer disease with early onset",
    "C50.9":  "Breast, unspecified",
    "S62.0":  "Fracture of navicular [scaphoid] bone of hand",
    "S63.6":  "Sprain and strain of finger(s)",
    "S93.4":  "Sprain and strain of ankle",
    "S91.3":  "Open wound of other parts of foot",
    "T50.9":  "Other and unspecified drugs, medicaments and biological substances",
    "O02.0":  "Blighted ovum and nonhydatidiform mole",
    "O36.9":  "Maternal care for fetal problem, unspecified",
}

DESCRIPTION_CORRECTIONS = {
    59621000:  "Essential hypertension (disorder)",
    403190006: "Epidermal burn of skin (disorder)",
    5602001:   "Harmful pattern of use of opioid",
    201834006: "Localized, primary osteoarthritis of the hand",
}


def safe_date(dt):
    if pd.isna(dt):
        return None
    return pd.Timestamp(dt).strftime("%Y-%m-%d")


def parse_list_col(val):
    if isinstance(val, list):
        return val
    try:
        return json.loads(val.replace("'", '"'))
    except Exception:
        return []


def strip_display(desc):
    if " - " in str(desc):
        return desc.split(" - ")[0].strip()
    return desc


def get_official_display(icd10_code, current_display):
    return DISPLAY_CORRECTIONS.get(icd10_code, current_display)


def load_data(conditions_path, patients_path, scored_segments_path, map_path, universe_path):
    encounter_merged = pd.read_csv(conditions_path, parse_dates=["START", "STOP"])
    patients         = pd.read_csv(patients_path)
    scored_segments  = pd.read_csv(scored_segments_path)
    df_map           = pd.read_csv(map_path)
    universe_ref     = pd.read_csv(universe_path)

    df_map["icd10_desc"] = df_map["icd10_desc"].str.replace("—", "-", regex=False)

    for code, desc in DESCRIPTION_CORRECTIONS.items():
        universe_ref.loc[universe_ref["CODE"] == code, "DESCRIPTION"] = desc

    df_map = df_map.merge(
        universe_ref[["CODE", "DESCRIPTION"]].rename(columns={"CODE": "snomed_code"}),
        on="snomed_code",
        how="left"
    )

    print(f"[fhir_exporter] Encounter rows loaded    : {len(encounter_merged)}")
    print(f"[fhir_exporter] Patients loaded          : {len(patients)}")
    print(f"[fhir_exporter] Scored segments loaded   : {len(scored_segments)}")
    print(f"[fhir_exporter] Mapping rows loaded      : {len(df_map)}")

    return encounter_merged, patients, scored_segments, df_map


def build_patient_resource(row):
    gender_map = {"M": "male", "F": "female", "m": "male", "f": "female"}
    gender     = gender_map.get(str(row["GENDER"]).strip(), "unknown") if pd.notna(row["GENDER"]) else "unknown"
    return {
        "resourceType": "Patient",
        "id":           row["Id"],
        "text": {
            "status": "generated",
            "div":    f"<div xmlns='http://www.w3.org/1999/xhtml'>Patient {row['Id']} | Gender: {gender} | DOB: {safe_date(pd.to_datetime(row['BIRTHDATE'], errors='coerce'))}</div>"
        },
        "gender":    gender,
        "birthDate": safe_date(pd.to_datetime(row["BIRTHDATE"], errors="coerce")),
    }


def build_encounter_resource(enc_row):
    enc_id = f"{enc_row['ENCOUNTER']}-{pd.Timestamp(enc_row['START']).strftime('%Y%m%d')}"
    period = {"start": safe_date(enc_row["START"])}
    if pd.notna(enc_row["STOP"]):
        period["end"] = safe_date(enc_row["STOP"])
    return {
        "resourceType": "Encounter",
        "id":           enc_id,
        "text": {
            "status": "generated",
            "div":    f"<div xmlns='http://www.w3.org/1999/xhtml'>Encounter on {safe_date(enc_row['START'])} for patient {enc_row['PATIENT']}</div>"
        },
        "status": "finished",
        "class": {
            "system":  "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code":    "AMB",
            "display": "ambulatory"
        },
        "subject": {"reference": f"Patient/{enc_row['PATIENT']}"},
        "period":  period
    }


def build_condition_resources(enc_row, df_map):
    snomed_codes = parse_list_col(enc_row["snomed_codes"])
    icd10_codes  = parse_list_col(enc_row["icd10_codes"])
    descriptions = parse_list_col(enc_row["descriptions"])
    conditions   = []
    enc_id       = f"{enc_row['ENCOUNTER']}-{pd.Timestamp(enc_row['START']).strftime('%Y%m%d')}"

    for i, snomed_code in enumerate(snomed_codes):
        snomed_str = str(snomed_code)
        match      = df_map[df_map["snomed_code"].astype(str) == snomed_str]

        if not match.empty:
            icd10_code  = match.iloc[0]["icd10_code"]
            icd10_desc  = get_official_display(icd10_code, strip_display(match.iloc[0]["icd10_desc"]))
            snomed_desc = match.iloc[0]["DESCRIPTION"] if "DESCRIPTION" in match.columns else (descriptions[i] if i < len(descriptions) else "Unknown")
        else:
            icd10_code  = icd10_codes[i] if i < len(icd10_codes) else "Unknown"
            icd10_desc  = get_official_display(icd10_code, "Unknown")
            snomed_desc = descriptions[i] if i < len(descriptions) else "Unknown"

        cond_id   = f"{enc_id}-{i}"
        condition = {
            "resourceType": "Condition",
            "id":           cond_id,
            "text": {
                "status": "generated",
                "div":    f"<div xmlns='http://www.w3.org/1999/xhtml'>{snomed_desc} (SNOMED: {snomed_str} | ICD-10: {icd10_code})</div>"
            },
            "subject":       {"reference": f"Patient/{enc_row['PATIENT']}"},
            "encounter":     {"reference": f"Encounter/{enc_id}"},
            "onsetDateTime": safe_date(enc_row["START"]),
            "code": {
                "coding": [
                    {
                        "system":       "http://snomed.info/sct",
                        "code":         snomed_str,
                        "display":      snomed_desc,
                        "userSelected": True
                    },
                    {
                        "system":       "http://hl7.org/fhir/sid/icd-10",
                        "code":         icd10_code,
                        "display":      icd10_desc,
                        "userSelected": False
                    }
                ],
                "text": snomed_desc
            },
            "clinicalStatus": {
                "coding": [{
                    "system":  "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code":    "active" if pd.isna(enc_row["STOP"]) else "resolved",
                    "display": "Active" if pd.isna(enc_row["STOP"]) else "Resolved"
                }]
            }
        }
        conditions.append(condition)
    return conditions


def build_risk_assessment(patient_id, scored_row):
    return {
        "resourceType": "RiskAssessment",
        "id":           patient_id,
        "text": {
            "status": "generated",
            "div":    f"<div xmlns='http://www.w3.org/1999/xhtml'>Risk tier: {scored_row['risk_tier']} | Score: {scored_row['risk_score']} | Segment: {scored_row['primary_segment']}</div>"
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "status":  "final",
        "prediction": [
            {
                "outcome": {
                    "coding": [{
                        "system":  "http://snomed.info/sct",
                        "code":    "225338004",
                        "display": "Risk assessment"
                    }]
                },
                "probabilityDecimal": float(scored_row["risk_score"]),
            }
        ],
        "note": [
            {
                "text": (
                    f"Risk tier: {scored_row['risk_tier']} | "
                    f"Primary segment: {scored_row['primary_segment']} | "
                    f"All segments: {scored_row['all_segments']}"
                )
            }
        ]
    }


def build_bundle(encounter_merged, patients, scored_segments, df_map, output_dir="outputs"):
    os.makedirs(os.path.join(output_dir, "fhir"), exist_ok=True)

    bundle = {
        "resourceType": "Bundle",
        "id":           f"clinical-risk-bundle-{datetime.today().strftime('%Y-%m-%d')}",
        "type":         "collection",
        "timestamp":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "entry":        []
    }

    scored_index   = scored_segments.set_index("PATIENT")
    enc_by_patient = encounter_merged.groupby("PATIENT")

    patient_count   = 0
    condition_count = 0
    encounter_count = 0
    risk_count      = 0

    for _, pat_row in patients.iterrows():
        patient_id = pat_row["Id"]

        if patient_id not in scored_index.index:
            continue

        scored_row = scored_index.loc[patient_id]

        bundle["entry"].append({
            "fullUrl":  f"http://clinical-risk-pipeline/Patient/{pat_row['Id']}",
            "resource": build_patient_resource(pat_row)
        })
        patient_count += 1

        if patient_id in enc_by_patient.groups:
            for _, enc_row in enc_by_patient.get_group(patient_id).iterrows():
                enc_resource = build_encounter_resource(enc_row)
                bundle["entry"].append({
                    "fullUrl":  f"http://clinical-risk-pipeline/Encounter/{enc_resource['id']}",
                    "resource": enc_resource
                })
                encounter_count += 1

                for cond in build_condition_resources(enc_row, df_map):
                    bundle["entry"].append({
                        "fullUrl":  f"http://clinical-risk-pipeline/Condition/{cond['id']}",
                        "resource": cond
                    })
                    condition_count += 1

        bundle["entry"].append({
            "fullUrl":  f"http://clinical-risk-pipeline/RiskAssessment/{patient_id}",
            "resource": build_risk_assessment(patient_id, scored_row)
        })
        risk_count += 1

    return bundle, patient_count, encounter_count, condition_count, risk_count


def run(conditions_path, patients_path, scored_segments_path, map_path, universe_path, output_dir="outputs"):
    encounter_merged, patients, scored_segments, df_map = load_data(
        conditions_path, patients_path, scored_segments_path, map_path, universe_path
    )

    bundle, patient_count, encounter_count, condition_count, risk_count = build_bundle(
        encounter_merged, patients, scored_segments, df_map, output_dir
    )

    output_path = os.path.join(output_dir, "fhir", "clinical_risk_bundle.json")
    with open(output_path, "w") as f:
        json.dump(bundle, f, indent=2, default=str, ensure_ascii=False)

    print(f"\n[fhir_exporter] ── Bundle Export ────────────────────────")
    print(f"[fhir_exporter] Output file        : {output_path}")
    print(f"[fhir_exporter] Total entries      : {len(bundle['entry'])}")
    print(f"[fhir_exporter]   Patient          : {patient_count}")
    print(f"[fhir_exporter]   Encounter        : {encounter_count}")
    print(f"[fhir_exporter]   Condition        : {condition_count}")
    print(f"[fhir_exporter]   RiskAssessment   : {risk_count}")
    print(f"[fhir_exporter] File size          : {os.path.getsize(output_path) / 1024:.1f} KB")

    return bundle
