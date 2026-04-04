import pandas as pd
import os

def load_data(conditions_path, universe_path):
    conditions = pd.read_csv(conditions_path)
    universe   = pd.read_csv(universe_path)
    return conditions, universe

def map_conditions(conditions, universe):
    merged = conditions.merge(
        universe[["CODE", "CATEGORY"]],
        on="CODE",
        how="left"
    )
    total     = len(conditions)
    matched   = merged["CATEGORY"].notna().sum()
    unmatched = total - matched
    print(f"[snomed_conditions] Condition rows total     : {total}")
    print(f"[snomed_conditions] Matched to category      : {matched} ({matched/total*100:.1f}%)")
    print(f"[snomed_conditions] Unmatched (out of scope) : {unmatched} ({unmatched/total*100:.1f}%)")
    merged["CATEGORY"] = merged["CATEGORY"].fillna("OTHER")
    return merged

def build_wide(merged):
    wide = (
        merged.groupby(["PATIENT", "CATEGORY"])
        .size()
        .unstack(fill_value=0)
        .clip(upper=1)
        .reset_index()
    )
    wide["category_count"] = wide.drop(columns="PATIENT").sum(axis=1)
    return wide

def build_long(merged):
    long = (
        merged[["PATIENT", "CATEGORY"]]
        .drop_duplicates()
        .sort_values(["PATIENT", "CATEGORY"])
        .reset_index(drop=True)
    )
    return long

def run(conditions_path, universe_path, output_dir="outputs"):
    os.makedirs(output_dir, exist_ok=True)
    conditions, universe = load_data(conditions_path, universe_path)
    merged               = map_conditions(conditions, universe)
    wide                 = build_wide(merged)
    long                 = build_long(merged)
    wide_path = os.path.join(output_dir, "patient_conditions_wide.csv")
    long_path = os.path.join(output_dir, "patient_conditions_long.csv")
    wide.to_csv(wide_path, index=False)
    long.to_csv(long_path, index=False)
    print(f"\n[snomed_conditions] Wide format saved : {wide_path}")
    print(f"[snomed_conditions] Long format saved : {long_path}")
    print(f"[snomed_conditions] Patients in wide  : {len(wide)}")
    print(f"[snomed_conditions] Rows in long      : {len(long)}")
    return wide, long, merged
