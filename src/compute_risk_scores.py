import pandas as pd
import os

CATEGORY_WEIGHTS = {
    "DIABETES & COMPLICATIONS":             4,
    "CARDIOVASCULAR":                       4,
    "ENDOCRINOLOGY":                        3,
    "NEUROLOGY / CEREBROVASCULAR":          3,
    "NEPHROLOGY & ELECTROLYTES DISORDERS":  3,
    "PULMONOLOGY":                          2,
    "PSYCHIATRY":                           2,
    "DRUG INTERACTIONS / ADDICTION":        2,
    "GENERAL SURGERY":                      1,
    "ORTHOPEDICS & RHEUMATOLOGY":           1,
    "GYNECOLOGY & OBSTETRICS":              1,
    "TRAUMA":                               0.5,
    "MALE REPRODUCTIVE":                    0.5,
    "ENT":                                  0.5,
    "OTHER":                                0.5,
}

MULTIMORBIDITY_TIERS = {
    2: 1,
    5: 2,
    8: 3,
}

AGE_SENSITIVE_CATEGORIES = {
    "DIABETES & COMPLICATIONS",
    "CARDIOVASCULAR",
    "NEUROLOGY / CEREBROVASCULAR",
    "ENDOCRINOLOGY",
    "NEPHROLOGY & ELECTROLYTES DISORDERS",
}

AGE_MULTIPLIERS = {
    "0-40":  1.0,
    "41-65": 1.25,
    "66+":   1.5,
}

POLYPHARMACY_THRESHOLDS = {
    25:  1,
    50:  2,
    100: 3,
}

HIGH_UTILISATION_THRESHOLDS = {
    20:  1,
    50:  2,
    100: 3,
}

RECURRENCE_BONUS_THRESHOLD = 3
RECURRENCE_BONUS_SCORE     = 0.5
MEDICATION_OUTLIER_CAP     = 100
AGE_REFERENCE_DATE         = pd.Timestamp("2020-04-25")


def load_data(conditions_path, patients_path, medications_path, encounters_path):
    conditions  = pd.read_csv(conditions_path)
    patients    = pd.read_csv(patients_path)
    medications = pd.read_csv(medications_path)
    encounters  = pd.read_csv(encounters_path)
    return conditions, patients, medications, encounters


def build_scored_base(wide, merged):
    recurrence = (
        merged.groupby(["PATIENT", "CATEGORY"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    recurrence.columns = (
        ["PATIENT"] +
        [f"recurrence_{col}" for col in recurrence.columns if col != "PATIENT"]
    )
    scored = wide.merge(recurrence, on="PATIENT", how="left")
    return scored


def score_base(scored):
    category_cols = [col for col in scored.columns if col in CATEGORY_WEIGHTS]
    weight_vector = pd.Series({col: CATEGORY_WEIGHTS[col] for col in category_cols})
    scored["base_score"] = scored[category_cols].dot(weight_vector)
    return scored


def score_multimorbidity(scored):
    def multimorbidity_tier_bonus(category_count):
        bonus = 0
        for threshold, score in sorted(MULTIMORBIDITY_TIERS.items()):
            if category_count >= threshold:
                bonus = score
        return bonus
    scored["multimorbidity_tier_bonus"] = scored["category_count"].apply(multimorbidity_tier_bonus)
    return scored


def score_age(scored, patients):
    patients_clean = patients.copy()
    patients_clean["age"] = (
        AGE_REFERENCE_DATE - pd.to_datetime(patients_clean["BIRTHDATE"])
    ).dt.days // 365

    def get_age_band(age):
        if age <= 40:
            return "0-40"
        elif age <= 65:
            return "41-65"
        else:
            return "66+"

    patients_clean["age_band"] = patients_clean["age"].apply(get_age_band)
    scored = scored.merge(
        patients_clean[["Id", "age", "age_band"]].rename(columns={"Id": "PATIENT"}),
        on="PATIENT",
        how="left"
    )
    age_adjustment = pd.Series(0.0, index=scored.index)
    for col in AGE_SENSITIVE_CATEGORIES:
        if col in scored.columns and col in CATEGORY_WEIGHTS:
            base_weight = CATEGORY_WEIGHTS[col]
            for band, multiplier in AGE_MULTIPLIERS.items():
                mask = (scored["age_band"] == band) & (scored[col] == 1)
                age_adjustment[mask] += base_weight * (multiplier - 1.0)
    scored["age_adjustment"] = age_adjustment.round(2)
    return scored


def score_polypharmacy_utilisation(scored, medications, encounters):
    med_counts = (
        medications.groupby("PATIENT")
        .size()
        .reset_index(name="medication_count")
    )
    med_counts["medication_count"] = med_counts["medication_count"].clip(upper=MEDICATION_OUTLIER_CAP)
    enc_counts = (
        encounters.groupby("PATIENT")
        .size()
        .reset_index(name="encounter_count")
    )
    scored = scored.merge(med_counts, on="PATIENT", how="left")
    scored = scored.merge(enc_counts, on="PATIENT", how="left")
    scored["medication_count"] = scored["medication_count"].fillna(0)
    scored["encounter_count"]  = scored["encounter_count"].fillna(0)

    def polypharmacy_bonus(med_count):
        bonus = 0
        for threshold, score in sorted(POLYPHARMACY_THRESHOLDS.items()):
            if med_count >= threshold:
                bonus = score
        return bonus

    def utilisation_bonus(enc_count):
        bonus = 0
        for threshold, score in sorted(HIGH_UTILISATION_THRESHOLDS.items()):
            if enc_count >= threshold:
                bonus = score
        return bonus

    scored["polypharmacy_bonus"] = scored["medication_count"].apply(polypharmacy_bonus)
    scored["utilisation_bonus"]  = scored["encounter_count"].apply(utilisation_bonus)
    return scored


def score_recurrence(scored):
    for col in AGE_SENSITIVE_CATEGORIES:
        rec_col = f"recurrence_{col}"
        if rec_col in scored.columns:
            scored[f"{col}_rec_bonus"] = (scored[rec_col] >= RECURRENCE_BONUS_THRESHOLD) * RECURRENCE_BONUS_SCORE
    recurrence_bonus_cols = [col for col in scored.columns if col.endswith("_rec_bonus")]
    scored["recurrence_bonus"] = scored[recurrence_bonus_cols].sum(axis=1)
    return scored


def assign_tier(score):
    if score >= 27:
        return "Critical"
    elif score >= 17:
        return "High"
    elif score >= 5:
        return "Medium"
    else:
        return "Low"


def calculate_final_score(scored):
    scored["risk_score"] = (
        scored["base_score"] +
        scored["multimorbidity_tier_bonus"] +
        scored["age_adjustment"] +
        scored["polypharmacy_bonus"] +
        scored["utilisation_bonus"] +
        scored["recurrence_bonus"]
    ).round(2)
    scored["risk_tier"] = scored["risk_score"].apply(assign_tier)
    return scored


def run(wide, merged, patients, medications, encounters, output_dir="outputs"):
    os.makedirs(output_dir, exist_ok=True)

    scored = build_scored_base(wide, merged)
    scored = score_base(scored)
    scored = score_multimorbidity(scored)
    scored = score_age(scored, patients)
    scored = score_polypharmacy_utilisation(scored, medications, encounters)
    scored = score_recurrence(scored)
    scored = calculate_final_score(scored)

    print(f"[risk_scorer] Patients scored        : {len(scored)}")
    print(f"[risk_scorer] Risk score range       : {scored['risk_score'].min()} – {scored['risk_score'].max()}")
    print(f"[risk_scorer] Mean score             : {scored['risk_score'].mean():.2f}")
    print()

    tier_counts = scored["risk_tier"].value_counts().reindex(["Critical", "High", "Medium", "Low"])
    tier_pct    = (tier_counts / len(scored) * 100).round(1)
    for tier in ["Critical", "High", "Medium", "Low"]:
        print(f"[risk_scorer] {tier:<10} : {tier_counts[tier]:>4} patients ({tier_pct[tier]}%)")

    output_path = os.path.join(output_dir, "patient_risk_scores.csv")
    scored.to_csv(output_path, index=False)
    print(f"\n[risk_scorer] Exported : {output_path}")

    return scored
