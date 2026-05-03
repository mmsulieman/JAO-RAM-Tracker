import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.io_helpers import load_csv_sample, read_uploaded_table, to_excel_bytes
from utils.planning import (
    REQUIRED_FDP_COLUMNS,
    generate_monitoring_plan,
    generate_checklist_requirements,
    compare_required_vs_achieved,
    summarize_plan,
    summarize_requirements_vs_achieved,
)
from utils.metrics import format_pct, kpi_counts


st.set_page_config(
    page_title="RAMTrack | WFP–TPM Monitoring Planner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# Styling: WFP Jijiga AO Header + RAM footer
# -------------------------
st.markdown(
    """
    <style>
    .wfp-header {
        background: linear-gradient(90deg, #005EB8 0%, #0072CE 55%, #00A3E0 100%);
        padding: 18px 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 16px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.12);
    }
    .wfp-header h1 {
        margin: 0;
        font-size: 1.7rem;
        line-height: 1.1;
    }
    .wfp-header p {
        margin: 4px 0 0 0;
        opacity: 0.96;
        font-size: 0.98rem;
    }
    .metric-card {
        background: #F7FAFC;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 14px 16px;
    }
    .ram-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background: #0B1F33;
        color: white;
        text-align: center;
        padding: 6px 10px;
        font-size: 0.78rem;
        z-index: 9999;
    }
    .small-note {
        font-size: 0.85rem;
        color: #475569;
    }
    </style>
    <div class="wfp-header">
      <h1>WFP Jijiga Area Office | RAMTrack</h1>
      <p>Joint WFP–TPM Monitoring Planning, 70/30 Allocation, Checklist Compliance and Gap Tracking App</p>
    </div>
    <div class="ram-footer">Prepared for WFP Jijiga Area Office · RAM Unit · Monitoring Planning and Checklist Compliance</div>
    """,
    unsafe_allow_html=True,
)


# -------------------------
# Data loading
# -------------------------
@st.cache_data
def load_samples():
    fdp = load_csv_sample("fdp_master_sample.csv")
    req = load_csv_sample("checklist_requirement_matrix.csv")
    sub = load_csv_sample("moda_submissions_sample.csv")
    return fdp, req, sub


sample_fdp, sample_req, sample_sub = load_samples()

with st.sidebar:
    st.markdown("## Navigation")
    page = st.radio(
        "Go to",
        [
            "Executive Dashboard",
            "Generate 70/30 Monitoring Plan",
            "Requirement vs Achieved",
            "Map & Priority Gaps",
            "Data Uploads",
            "Help & Deployment Guide",
        ],
    )

    st.markdown("---")
    st.markdown("## Help Menu")
    with st.expander("What does this app do?", expanded=False):
        st.write(
            """
            RAMTrack helps the Area Office jointly plan WFP and TPM monitoring, allocate FDPs/sites
            using a practical 70/30 logic, generate checklist requirements and compare them with
            MoDA submissions.
            """
        )
    with st.expander("Minimum checklist package", expanded=False):
        st.markdown(
            """
            **Activity 1 Relief:** 6 beneficiary contact + 6 food basket + 1 warehouse + 1 observation + 1 partner performance = **15** per FDP.

            **Activity 3 Refugees:** Same as Activity 1 = **15** per FDP/site.

            **Activity 2 Nutrition:** Suggested standard = 1 TSFP centre + 2 beneficiary contact + 2 ration/food basket + 1 observation + 1 warehouse/store + 1 partner = **8** per TSFP site.
            """
        )
    with st.expander("Data protection note", expanded=False):
        st.warning(
            "Use dummy or anonymized data for public deployments. Avoid household names, phone numbers, IDs or sensitive comments unless deployed in an approved secure environment."
        )


# Session state defaults
if "fdp_master" not in st.session_state:
    st.session_state["fdp_master"] = sample_fdp.copy()
if "requirement_matrix" not in st.session_state:
    st.session_state["requirement_matrix"] = sample_req.copy()
if "moda_submissions" not in st.session_state:
    st.session_state["moda_submissions"] = sample_sub.copy()
if "plan" not in st.session_state:
    st.session_state["plan"] = generate_monitoring_plan(sample_fdp, month="January", activity="All Activities")
if "requirements" not in st.session_state:
    st.session_state["requirements"] = generate_checklist_requirements(st.session_state["plan"], sample_req)
if "rva" not in st.session_state:
    st.session_state["rva"] = compare_required_vs_achieved(st.session_state["requirements"], sample_sub)


def render_kpis(plan, rva):
    k = kpi_counts(plan, rva)
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Planned FDPs/Sites", f"{k['planned_sites']:,}")
    c2.metric("WFP Planned", f"{k['wfp_sites']:,}")
    c3.metric("TPM Planned", f"{k['tpm_sites']:,}")
    c4.metric("Required Checklists", f"{k['required']:,}")
    c5.metric("Achieved Checklists", f"{k['achieved']:,}")
    c6.metric("Checklist Completion", format_pct(k["completion"]))
    c7.metric("Critical/Not Submitted", f"{k['critical_gaps']:,}")


def bar_allocation(plan):
    if plan.empty:
        return
    entity_col = "Final Entity" if "Final Entity" in plan.columns else "Planned Entity"
    data = plan.groupby(entity_col)["FDP/Site Name"].nunique().reset_index()
    data.columns = ["Entity", "Planned FDPs/Sites"]
    fig = px.bar(
        data,
        x="Entity",
        y="Planned FDPs/Sites",
        text="Planned FDPs/Sites",
        title="WFP vs TPM Planned Allocation",
        color="Entity",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis_title="FDPs/Sites", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)


def completion_heatmap(rva):
    if rva.empty:
        return
    mat = (
        rva.groupby(["Activity", "Checklist Type"])["Completion %"]
        .mean()
        .reset_index()
    )
    fig = px.density_heatmap(
        mat,
        x="Checklist Type",
        y="Activity",
        z="Completion %",
        text_auto=".0%",
        range_color=[0, 1],
        color_continuous_scale="RdYlGn",
        title="Checklist Completion Heatmap by Activity and Checklist Type",
    )
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)


# -------------------------
# Pages
# -------------------------
if page == "Executive Dashboard":
    st.subheader("Executive Dashboard")
    plan = st.session_state["plan"]
    rva = st.session_state["rva"]
    render_kpis(plan, rva)

    col1, col2 = st.columns([1, 1])
    with col1:
        bar_allocation(plan)
    with col2:
        summary = summarize_requirements_vs_achieved(rva)
        if not summary.empty:
            fig = px.bar(
                summary,
                x="Activity",
                y=["Required", "Achieved"],
                barmode="group",
                color_discrete_sequence=["#94A3B8", "#0072CE"],
                title="Required vs Achieved Checklists by Activity",
            )
            st.plotly_chart(fig, use_container_width=True)

    completion_heatmap(rva)

    st.markdown("### Priority Gaps")
    if rva.empty:
        st.info("No requirement-vs-achieved data available yet.")
    else:
        gaps = rva[rva["Status"].isin(["Critical Gap", "Not Submitted"])].sort_values(["Activity", "Entity", "Woreda"]).head(25)
        st.dataframe(gaps, use_container_width=True)


elif page == "Generate 70/30 Monitoring Plan":
    st.subheader("Generate Monitoring Plan on 70/30 Basis")

    fdp = st.session_state["fdp_master"]
    req = st.session_state["requirement_matrix"]

    left, right = st.columns([1, 1])
    with left:
        month = st.selectbox("Reporting month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        activity_options = ["All Activities"] + sorted(fdp["Activity"].dropna().unique().tolist())
        activity = st.selectbox("Activity", activity_options)
        target_tpm = st.slider("TPM target share", min_value=0.50, max_value=0.90, value=0.70, step=0.05)
    with right:
        large_threshold = st.number_input("Large woreda threshold", min_value=1, max_value=200, value=35)
        split_large = st.checkbox("Split large woredas between WFP and TPM", value=True)
        priority_to_wfp = st.checkbox("Assign high-priority sites to WFP first", value=True)

    st.markdown(
        "<p class='small-note'>The allocation uses whole-woreda assignment where practical. Woredas above the threshold can be split FDP-by-FDP. The plan can be manually adjusted using the editor below.</p>",
        unsafe_allow_html=True,
    )

    if st.button("Generate 70/30 Monitoring Plan", type="primary"):
        plan = generate_monitoring_plan(
            fdp,
            month=month,
            activity=activity,
            tpm_target=target_tpm,
            large_threshold=int(large_threshold),
            split_large_woredas=split_large,
            priority_to_wfp=priority_to_wfp,
        )
        st.session_state["plan"] = plan
        st.session_state["requirements"] = generate_checklist_requirements(plan, req)
        st.session_state["rva"] = compare_required_vs_achieved(st.session_state["requirements"], st.session_state["moda_submissions"])
        st.success("Monitoring plan generated and checklist requirements updated.")

    plan = st.session_state["plan"]
    render_kpis(plan, st.session_state["rva"])

    st.markdown("### Generated Monitoring Plan")
    edited = st.data_editor(
        plan,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Manual Override Entity": st.column_config.SelectboxColumn(
                "Manual Override Entity",
                options=["", "WFP", "TPM"],
                help="Use only when an operational exception is agreed."
            ),
            "Final Entity": st.column_config.SelectboxColumn(
                "Final Entity",
                options=["WFP", "TPM"],
                help="Final assignment used for checklist requirement generation."
            ),
        },
        key="plan_editor",
    )
    if st.button("Apply Manual Overrides and Refresh Requirements"):
        if "Manual Override Entity" in edited.columns:
            edited["Final Entity"] = np.where(
                edited["Manual Override Entity"].astype(str).str.len() > 0,
                edited["Manual Override Entity"],
                edited["Planned Entity"],
            )
        st.session_state["plan"] = edited
        st.session_state["requirements"] = generate_checklist_requirements(edited, req)
        st.session_state["rva"] = compare_required_vs_achieved(st.session_state["requirements"], st.session_state["moda_submissions"])
        st.success("Manual overrides applied.")

    col1, col2 = st.columns([1, 1])
    with col1:
        bar_allocation(st.session_state["plan"])
    with col2:
        req_summary = (
            st.session_state["requirements"]
            .groupby(["Activity", "Entity"])["Required Count"]
            .sum()
            .reset_index()
        )
        if not req_summary.empty:
            fig = px.bar(req_summary, x="Activity", y="Required Count", color="Entity", barmode="group", text="Required Count", title="Generated Checklist Requirements")
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

    xls = to_excel_bytes({
        "Generated Monitoring Plan": st.session_state["plan"],
        "Checklist Requirements": st.session_state["requirements"],
        "Requirement_vs_Achieved": st.session_state["rva"],
    })
    st.download_button("Download Generated Plan and Requirements", data=xls, file_name="Generated_WFP_TPM_Monitoring_Plan.xlsx")


elif page == "Requirement vs Achieved":
    st.subheader("Checklist Requirement vs Achieved")
    rva = st.session_state["rva"]
    render_kpis(st.session_state["plan"], rva)

    if rva.empty:
        st.info("No data available.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            activity_filter = st.multiselect("Activity", sorted(rva["Activity"].dropna().unique()), default=sorted(rva["Activity"].dropna().unique()))
        with col2:
            entity_filter = st.multiselect("Entity", sorted(rva["Entity"].dropna().unique()), default=sorted(rva["Entity"].dropna().unique()))
        with col3:
            status_filter = st.multiselect("Status", sorted(rva["Status"].dropna().unique()), default=sorted(rva["Status"].dropna().unique()))

        filtered = rva[
            rva["Activity"].isin(activity_filter) &
            rva["Entity"].isin(entity_filter) &
            rva["Status"].isin(status_filter)
        ].copy()

        completion_heatmap(filtered)

        st.markdown("### Requirement vs Achieved Detail")
        show = filtered.copy()
        show["Completion %"] = show["Completion %"].map(lambda x: f"{x:.0%}" if pd.notna(x) else "")
        st.dataframe(show, use_container_width=True)

        xls = to_excel_bytes({"Requirement_vs_Achieved": filtered, "Summary": summarize_requirements_vs_achieved(filtered)})
        st.download_button("Download filtered gap tracker", data=xls, file_name="Requirement_vs_Achieved_Gap_Tracker.xlsx")


elif page == "Map & Priority Gaps":
    st.subheader("Map & Priority Gaps")
    rva = st.session_state["rva"]
    if rva.empty:
        st.info("No gap data available.")
    else:
        gap = rva[rva["Status"].isin(["Critical Gap", "Not Submitted", "Moderate Gap"])].copy()
        gap["Latitude"] = pd.to_numeric(gap["Latitude"], errors="coerce")
        gap["Longitude"] = pd.to_numeric(gap["Longitude"], errors="coerce")
        gap_map = gap.dropna(subset=["Latitude", "Longitude"])

        if not gap_map.empty:
            fig = px.scatter_mapbox(
                gap_map,
                lat="Latitude",
                lon="Longitude",
                hover_name="FDP/Site Name",
                hover_data=["Activity", "Entity", "Woreda", "Checklist Type", "Status", "Gap"],
                color="Status",
                zoom=6,
                height=520,
                title="Map of FDP/Site Checklist Gaps",
            )
            fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":45,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No coordinates available for current gap records.")

        st.markdown("### Priority Gap List")
        st.dataframe(gap.sort_values(["Status", "Activity", "Entity", "Woreda"]), use_container_width=True)


elif page == "Data Uploads":
    st.subheader("Data Uploads")
    st.markdown("Upload your FDP master list, checklist requirement matrix and MoDA submissions. If no files are uploaded, the app uses built-in dummy data.")

    c1, c2, c3 = st.columns(3)
    with c1:
        fdp_file = st.file_uploader("Upload FDP master list", type=["csv", "xlsx", "xls"])
    with c2:
        req_file = st.file_uploader("Upload checklist requirement matrix", type=["csv", "xlsx", "xls"])
    with c3:
        sub_file = st.file_uploader("Upload MoDA submissions", type=["csv", "xlsx", "xls"])

    if st.button("Load Uploaded Data"):
        fdp = read_uploaded_table(fdp_file, sample_fdp)
        req = read_uploaded_table(req_file, sample_req)
        sub = read_uploaded_table(sub_file, sample_sub)

        missing = [c for c in REQUIRED_FDP_COLUMNS if c not in fdp.columns]
        if missing:
            st.error(f"FDP master list is missing required columns: {missing}")
        else:
            st.session_state["fdp_master"] = fdp
            st.session_state["requirement_matrix"] = req
            st.session_state["moda_submissions"] = sub
            st.session_state["plan"] = generate_monitoring_plan(fdp, month="January", activity="All Activities")
            st.session_state["requirements"] = generate_checklist_requirements(st.session_state["plan"], req)
            st.session_state["rva"] = compare_required_vs_achieved(st.session_state["requirements"], sub)
            st.success("Data loaded successfully. A default January plan has been generated.")

    st.markdown("### Current FDP Master List")
    st.dataframe(st.session_state["fdp_master"].head(100), use_container_width=True)
    st.markdown("### Current Checklist Requirement Matrix")
    st.dataframe(st.session_state["requirement_matrix"], use_container_width=True)
    st.markdown("### Current MoDA Submissions")
    st.dataframe(st.session_state["moda_submissions"].head(100), use_container_width=True)


elif page == "Help & Deployment Guide":
    st.subheader("Help & Deployment Guide")

    st.markdown(
        """
        ### Recommended workflow

        1. Upload/update the **FDP master list** with active FDPs/sites and coordinates.
        2. Review or edit the **Checklist Requirement Matrix**.
        3. Use **Generate 70/30 Monitoring Plan** to assign sites to WFP and TPM.
        4. Apply manual overrides for operational exceptions.
        5. Export the generated monitoring plan.
        6. After field monitoring, upload the MoDA submission export.
        7. Use **Requirement vs Achieved** to identify checklist gaps.
        8. Use the gap tracker in monthly RAM/Programme/TPM follow-up meetings.

        ### Required FDP master fields

        `Activity`, `Modality`, `Sub-office`, `Zone`, `Woreda`, `FDP/Site Name`,
        `Partner`, `Active Status`, `Priority Level`, `Latitude`, `Longitude`

        ### Checklist requirement principle

        The app separates three layers:

        - **Planning layer:** which FDP/site is planned and who is responsible.
        - **Requirement layer:** what checklist package is required for each planned FDP/site.
        - **Achievement layer:** what was actually submitted in MoDA.

        ### Deployment options

        **Local deployment**
        ```bash
        pip install -r requirements.txt
        streamlit run streamlit_app.py
        ```

        **Streamlit Cloud prototype**
        - Push the folder to GitHub.
        - Create a new Streamlit app.
        - Select `streamlit_app.py` as the main file.
        - Use dummy or anonymized data only unless internal clearance is obtained.

        **Internal deployment**
        - Deploy on an approved WFP/server environment.
        - Avoid storing sensitive beneficiary-level data unless the environment is approved.
        - Prefer aggregated outputs for reports and management dashboards.
        """
    )