import math
import numpy as np
import pandas as pd

REQUIRED_FDP_COLUMNS = [
    "Activity", "Modality", "Sub-office", "Zone", "Woreda", "FDP/Site Name",
    "Partner", "Active Status", "Priority Level", "Latitude", "Longitude"
]

OUTPUT_PLAN_COLUMNS = [
    "Month", "Activity", "Modality", "Sub-office", "Zone", "Woreda",
    "FDP/Site Name", "Planned Entity", "Assignment Type", "Planned Visit",
    "Partner", "Priority Level", "Latitude", "Longitude", "GPS",
    "Manual Override Entity", "Override Reason", "Final Entity"
]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def validate_columns(df: pd.DataFrame, required_cols: list[str]) -> list[str]:
    cols = set(df.columns)
    return [c for c in required_cols if c not in cols]


def generate_monitoring_plan(
    fdp_master: pd.DataFrame,
    month: str,
    activity: str | None = None,
    tpm_target: float = 0.70,
    large_threshold: int = 35,
    split_large_woredas: bool = True,
    priority_to_wfp: bool = True,
    active_only: bool = True,
) -> pd.DataFrame:
    """Generate a FDP/site-level monitoring plan using a practical 70/30 WFP-TPM logic.

    Rules:
    - Target is TPM 70%, WFP 30% by FDP/site count.
    - Normal woredas are assigned as a block to simplify field planning.
    - Woredas above the large_threshold can be split FDP-by-FDP.
    - Priority/high-risk sites can be assigned to WFP first.
    """
    df = normalize_columns(fdp_master)
    missing = validate_columns(df, REQUIRED_FDP_COLUMNS)
    if missing:
        raise ValueError(f"FDP master list is missing required columns: {missing}")

    df = df.copy()
    if active_only and "Active Status" in df.columns:
        df = df[df["Active Status"].astype(str).str.lower().eq("active")].copy()

    if activity and activity != "All Activities":
        df = df[df["Activity"].eq(activity)].copy()

    if df.empty:
        return pd.DataFrame(columns=OUTPUT_PLAN_COLUMNS)

    # Make sure coordinates are numeric when possible
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    total_sites = len(df)
    tpm_target_n = int(round(total_sites * tpm_target))
    wfp_target_n = total_sites - tpm_target_n

    df["FDP Count in Woreda"] = df.groupby(["Activity", "Woreda"])["FDP/Site Name"].transform("count")
    df["Assignment Type"] = np.where(
        df["FDP Count in Woreda"] > large_threshold,
        "Split large woreda",
        "Full woreda"
    )
    df["Planned Entity"] = ""

    # Optional: priority/high-risk sites first to WFP.
    priority_mask = df["Priority Level"].astype(str).str.lower().isin(["high", "critical", "priority", "management priority"])
    if priority_to_wfp and priority_mask.any():
        priority_indices = df[priority_mask].index.tolist()
        df.loc[priority_indices, "Planned Entity"] = "WFP"

    current_wfp = int((df["Planned Entity"] == "WFP").sum())
    current_tpm = int((df["Planned Entity"] == "TPM").sum())

    # Allocate by activity and woreda to preserve operational logic.
    for (act, woreda), group in df.groupby(["Activity", "Woreda"], sort=True):
        remaining = group[group["Planned Entity"].eq("")]
        if remaining.empty:
            continue

        idx = remaining.index.tolist()
        woreda_count = len(idx)

        if split_large_woredas and group["FDP Count in Woreda"].iloc[0] > large_threshold:
            # Balance inside large woredas, while considering overall target.
            # Sort by site name for reproducibility.
            sorted_idx = remaining.sort_values("FDP/Site Name").index.tolist()
            for i in sorted_idx:
                # Assign to the entity that is furthest below its target.
                tpm_gap = tpm_target_n - current_tpm
                wfp_gap = wfp_target_n - current_wfp
                if wfp_gap >= tpm_gap:
                    df.at[i, "Planned Entity"] = "WFP"
                    current_wfp += 1
                else:
                    df.at[i, "Planned Entity"] = "TPM"
                    current_tpm += 1
        else:
            # Assign the whole woreda to the entity that best preserves 70/30.
            tpm_gap = tpm_target_n - current_tpm
            wfp_gap = wfp_target_n - current_wfp
            if tpm_gap >= wfp_gap:
                entity = "TPM"
                current_tpm += woreda_count
            else:
                entity = "WFP"
                current_wfp += woreda_count
            df.loc[idx, "Planned Entity"] = entity

    # Safety: fill any remaining blanks by balance.
    for i in df[df["Planned Entity"].eq("")].index:
        if current_tpm < tpm_target_n:
            df.at[i, "Planned Entity"] = "TPM"
            current_tpm += 1
        else:
            df.at[i, "Planned Entity"] = "WFP"
            current_wfp += 1

    df["Month"] = month
    df["Planned Visit"] = 1
    df["GPS"] = df["Latitude"].round(6).astype(str) + ", " + df["Longitude"].round(6).astype(str)
    df["Manual Override Entity"] = ""
    df["Override Reason"] = ""
    df["Final Entity"] = df["Planned Entity"]

    return df[OUTPUT_PLAN_COLUMNS].sort_values(["Activity", "Woreda", "FDP/Site Name"]).reset_index(drop=True)


def generate_checklist_requirements(plan: pd.DataFrame, requirement_matrix: pd.DataFrame) -> pd.DataFrame:
    """Expand a plan into expected checklist records using the requirement matrix."""
    plan = normalize_columns(plan)
    req = normalize_columns(requirement_matrix)
    required = []
    if plan.empty:
        return pd.DataFrame(columns=[
            "Month", "Activity", "Modality", "Entity", "Woreda", "FDP/Site Name",
            "Checklist Type", "Required Count", "Latitude", "Longitude", "GPS"
        ])

    entity_col = "Final Entity" if "Final Entity" in plan.columns else "Planned Entity"
    for _, site in plan.iterrows():
        activity = site["Activity"]
        activity_req = req[req["Activity"].eq(activity)].copy()
        for _, row in activity_req.iterrows():
            required.append({
                "Month": site["Month"],
                "Activity": site["Activity"],
                "Modality": site.get("Modality", ""),
                "Entity": site[entity_col],
                "Woreda": site["Woreda"],
                "FDP/Site Name": site["FDP/Site Name"],
                "Checklist Type": row["Checklist Type"],
                "Required Count": int(row["Requirement per FDP/Site"]),
                "Latitude": site.get("Latitude", None),
                "Longitude": site.get("Longitude", None),
                "GPS": site.get("GPS", ""),
            })
    return pd.DataFrame(required)


def compare_required_vs_achieved(requirements: pd.DataFrame, submissions: pd.DataFrame) -> pd.DataFrame:
    req = normalize_columns(requirements)
    sub = normalize_columns(submissions)

    if req.empty:
        return pd.DataFrame()

    # Harmonize expected columns in submissions.
    needed = ["Month", "Activity", "Entity", "Woreda", "FDP/Site Name", "Checklist Type"]
    for c in needed:
        if c not in sub.columns:
            sub[c] = ""

    group_cols = ["Month", "Activity", "Entity", "Woreda", "FDP/Site Name", "Checklist Type"]
    achieved = (
        sub.groupby(group_cols, dropna=False)
        .size()
        .reset_index(name="Achieved")
    )

    out = req.merge(achieved, on=group_cols, how="left")
    out["Achieved"] = out["Achieved"].fillna(0).astype(int)
    out["Gap"] = out["Required Count"] - out["Achieved"]
    out["Completion %"] = np.where(out["Required Count"] > 0, out["Achieved"] / out["Required Count"], np.nan)
    out["Completion %"] = out["Completion %"].clip(upper=1)

    def status(row):
        p = row["Completion %"]
        if pd.isna(p):
            return "No requirement"
        if p >= 1:
            return "Complete"
        if p >= 0.75:
            return "Partial"
        if p >= 0.50:
            return "Moderate Gap"
        if p > 0:
            return "Critical Gap"
        return "Not Submitted"

    out["Status"] = out.apply(status, axis=1)
    return out


def summarize_plan(plan: pd.DataFrame) -> pd.DataFrame:
    if plan.empty:
        return pd.DataFrame(columns=["Entity", "Planned FDPs", "Share"])
    entity_col = "Final Entity" if "Final Entity" in plan.columns else "Planned Entity"
    summary = plan.groupby(entity_col)["FDP/Site Name"].nunique().reset_index()
    summary.columns = ["Entity", "Planned FDPs"]
    total = summary["Planned FDPs"].sum()
    summary["Share"] = summary["Planned FDPs"] / total if total else 0
    return summary


def summarize_requirements_vs_achieved(rva: pd.DataFrame) -> pd.DataFrame:
    if rva.empty:
        return pd.DataFrame(columns=["Month", "Activity", "Entity", "Required", "Achieved", "Gap", "Completion %"])
    out = (
        rva.groupby(["Month", "Activity", "Entity"], dropna=False)
        .agg(
            Required=("Required Count", "sum"),
            Achieved=("Achieved", "sum"),
            Gap=("Gap", "sum"),
        )
        .reset_index()
    )
    out["Completion %"] = np.where(out["Required"] > 0, out["Achieved"] / out["Required"], np.nan).clip(max=1)
    return out