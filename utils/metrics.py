import numpy as np
import pandas as pd


def format_pct(x):
    if pd.isna(x):
        return "N/A"
    return f"{x:.0%}"


def kpi_counts(plan, rva):
    if plan is None or plan.empty:
        total_sites = wfp = tpm = 0
    else:
        entity_col = "Final Entity" if "Final Entity" in plan.columns else "Planned Entity"
        total_sites = plan["FDP/Site Name"].nunique()
        wfp = plan[plan[entity_col].eq("WFP")]["FDP/Site Name"].nunique()
        tpm = plan[plan[entity_col].eq("TPM")]["FDP/Site Name"].nunique()

    required = int(rva["Required Count"].sum()) if rva is not None and not rva.empty and "Required Count" in rva else 0
    achieved = int(rva["Achieved"].sum()) if rva is not None and not rva.empty and "Achieved" in rva else 0
    completion = achieved / required if required else 0
    critical = int(rva["Status"].isin(["Critical Gap", "Not Submitted"]).sum()) if rva is not None and not rva.empty and "Status" in rva else 0

    return {
        "planned_sites": total_sites,
        "wfp_sites": wfp,
        "tpm_sites": tpm,
        "required": required,
        "achieved": achieved,
        "completion": completion,
        "critical_gaps": critical,
    }
