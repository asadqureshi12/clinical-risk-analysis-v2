import pandas as pd
import os

SEGMENT_PRIORITY = [
    "CARDIO_METABOLIC",
    "MULTIMORBID_FRAIL",
    "MIDLIFE_ESCALATION",
    "ACUTE_OVERLAY",
]

SEGMENT_LABELS = {
    "CARDIO_METABOLIC":    "Cardio-Metabolic",
    "MULTIMORBID_FRAIL":   "Multimorbid Frail",
    "MIDLIFE_ESCALATION":  "Midlife Escalation",
    "ACUTE_OVERLAY":       "Acute Overlay",
}

ACUTE_OVERLAY_THRESHOLD      = 5
MULTIMORBID_FRAIL_AGE        = 66
MULTIMORBID_FRAIL_CATEGORIES = 3
MIDLIFE_ESCALATION_ENCOUNTERS = 50


def load_universe(universe_path):
    universe = pd.read_csv(universe_path)
    acute_codes = set(universe[universe["is_acute"] == 1]["CODE"])
    print(f"[segmentation] Acute SNOMED codes loaded : {len(acute_codes)}")
    return acute_codes


def flag_acute_overlay(scored, conditions, acute_codes):
    acute_condition_counts = (
        conditions[conditions["CODE"].isin(acute_codes)]
        .groupby("PATIENT")["CODE"]
        .nunique()
        .reset_index(name="acute_condition_count")
    )
    scored = scored.merge(acute_condition_counts, on="PATIENT", how="left")
    scored["acute_condition_count"] = scored["acute_condition_count"].fillna(0)
    scored["ACUTE_OVERLAY"] = (
        scored["acute_condition_count"] >= ACUTE_OVERLAY_THRESHOLD
    ).astype(int)
    print(f"[segmentation] Acute Overlay eligible    : {scored['ACUTE_OVERLAY'].sum()} ({scored['ACUTE_OVERLAY'].mean()*100:.1f}%)")
    return scored


def flag_cardio_metabolic(scored):
    scored["CARDIO_METABOLIC"] = (
        (scored["CARDIOVASCULAR"] == 1) &
        (scored["DIABETES & COMPLICATIONS"] == 1)
    ).astype(int)
    print(f"[segmentation] Cardio-Metabolic eligible : {scored['CARDIO_METABOLIC'].sum()} ({scored['CARDIO_METABOLIC'].mean()*100:.1f}%)")
    return scored


def flag_multimorbid_frail(scored):
    scored["MULTIMORBID_FRAIL"] = (
        (scored["age"] >= MULTIMORBID_FRAIL_AGE) &
        (scored["category_count"] >= MULTIMORBID_FRAIL_CATEGORIES) &
        (scored["CARDIO_METABOLIC"] == 0)
    ).astype(int)
    print(f"[segmentation] Multimorbid Frail eligible : {scored['MULTIMORBID_FRAIL'].sum()} ({scored['MULTIMORBID_FRAIL'].mean()*100:.1f}%)")
    return scored


def flag_midlife_escalation(scored):
    scored["MIDLIFE_ESCALATION"] = (
        (scored["age_band"] == "41-65") &
        (scored["encounter_count"] > MIDLIFE_ESCALATION_ENCOUNTERS)
    ).astype(int)
    print(f"[segmentation] Midlife Escalation eligible: {scored['MIDLIFE_ESCALATION'].sum()} ({scored['MIDLIFE_ESCALATION'].mean()*100:.1f}%)")
    return scored


def assign_segments(scored):
    def get_primary_segment(row):
        for seg in SEGMENT_PRIORITY:
            if row.get(seg, 0) == 1:
                return SEGMENT_LABELS[seg]
        return "Low Risk Stable"

    def get_all_segments(row):
        qualifying = [
            SEGMENT_LABELS[seg]
            for seg in SEGMENT_PRIORITY
            if row.get(seg, 0) == 1
        ]
        return ", ".join(qualifying) if qualifying else "Low Risk Stable"

    scored["primary_segment"] = scored.apply(get_primary_segment, axis=1)
    scored["all_segments"]    = scored.apply(get_all_segments, axis=1)
    return scored


def validate(scored):
    assert scored["primary_segment"].isna().sum() == 0, "WARNING: unassigned patients found"
    assert len(scored) == 1152, "WARNING: patient count mismatch"
    print(f"[segmentation] Validation PASSED — {len(scored)} patients, 0 unassigned")


def run(scored, conditions, universe_path, output_dir="outputs"):
    os.makedirs(output_dir, exist_ok=True)

    acute_codes = load_universe(universe_path)
    scored      = flag_cardio_metabolic(scored)
    scored      = flag_multimorbid_frail(scored)
    scored      = flag_midlife_escalation(scored)
    scored      = flag_acute_overlay(scored, conditions, acute_codes)
    scored      = assign_segments(scored)

    validate(scored)

    segment_summary = (
        scored.groupby("primary_segment")
        .agg(patient_count=("primary_segment", "count"))
        .reset_index()
    )
    segment_summary["percent"] = (
        100 * segment_summary["patient_count"] / len(scored)
    ).round(1)

    segments_path = os.path.join(output_dir, "patient_segments.csv")
    summary_path  = os.path.join(output_dir, "segment_summary.csv")
    scored.to_csv(segments_path, index=False)
    segment_summary.to_csv(summary_path, index=False)

    print(f"\n[segmentation] Exported : {segments_path}")
    print(f"[segmentation] Exported : {summary_path}")
    print()
    print("── Segment Summary ──────────────────────────────────")
    for _, row in segment_summary.iterrows():
        print(f"  {row['primary_segment']:<22} : {row['patient_count']:>4} patients ({row['percent']}%)")

    return scored, segment_summary
