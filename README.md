# RAMTrack: WFP–TPM Monitoring Planning and Checklist Compliance App

**Prepared for:** WFP Jijiga Area Office  
**Footer label:** RAM Unit  
**Purpose:** Joint monitoring planning, 70/30 WFP–TPM allocation, checklist requirement generation, MoDA submission tracking and gap analysis.

## Main Features

- WFP Jijiga Area Office header and RAM Unit footer
- Help menu and deployment guide
- Upload FDP/site master list, checklist requirement matrix and MoDA submissions
- Generate FDP/site-level monitoring plan on a practical 70/30 TPM/WFP basis
- Split large woredas above a configurable FDP threshold
- Assign high-priority sites to WFP first
- Manual override for operational exceptions
- Automatically generate checklist requirements
- Compare required versus achieved checklist submissions
- Dashboard with KPI cards, allocation charts, heatmaps, maps and priority gap lists
- Export generated plan, requirement matrix and gap tracker to Excel

## Minimum Checklist Requirements

### Activity 1 Relief

| Checklist Type | Requirement per FDP |
|---|---:|
| Beneficiary Contact Monitoring | 6 |
| Food Basket Monitoring | 6 |
| Warehouse Monitoring | 1 |
| Distribution Observation | 1 |
| Partner Performance Monitoring | 1 |

Total = **15 forms per FDP**

### Activity 3 Refugee Operations

Same as Activity 1: **15 forms per FDP/site**

### Activity 2 Nutrition

Suggested configurable standard:

| Checklist Type | Requirement per TSFP Site |
|---|---:|
| TSFP Centre-Level Monitoring | 1 |
| Beneficiary Contact Monitoring | 2 |
| TSFP Food Basket / Ration Verification | 2 |
| Distribution Observation | 1 |
| Warehouse / Store Monitoring | 1 |
| Partner Performance Monitoring | 1 |

Total = **8 forms per TSFP site**

## Local Run

```bash
cd ramtrack_streamlit_app
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Streamlit Cloud Deployment

1. Create a GitHub repository.
2. Upload the contents of this folder.
3. Go to Streamlit Community Cloud.
4. Create a new app and select `streamlit_app.py`.
5. Deploy.

Use dummy or anonymized data for public deployments.

## Docker Run

```bash
docker build -t ramtrack .
docker run -p 8501:8501 ramtrack
```

## Required FDP Master Columns

- Activity
- Modality
- Sub-office
- Zone
- Woreda
- FDP/Site Name
- Partner
- Active Status
- Priority Level
- Latitude
- Longitude

## Data Protection Note

Do not deploy identifiable beneficiary data publicly. Avoid household names, phone numbers, beneficiary IDs, token numbers, or sensitive free-text comments unless the app is hosted in an approved secure environment.