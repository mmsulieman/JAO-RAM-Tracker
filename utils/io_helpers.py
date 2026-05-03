from io import BytesIO
from pathlib import Path
import pandas as pd
import streamlit as st


def load_csv_sample(filename: str) -> pd.DataFrame:
    path = Path(__file__).resolve().parents[1] / "sample_data" / filename
    return pd.read_csv(path)


def read_uploaded_table(uploaded_file, default_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Read CSV or Excel uploaded to Streamlit. Fall back to default_df when None."""
    if uploaded_file is None:
        return default_df.copy() if default_df is not None else pd.DataFrame()

    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    st.warning("Unsupported file type. Please upload CSV or Excel.")
    return default_df.copy() if default_df is not None else pd.DataFrame()


def to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for sheet_name, df in sheets.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
            workbook = writer.book
            worksheet = writer.sheets[safe_name]
            header_fmt = workbook.add_format({
                "bold": True, "bg_color": "#0B4F71", "font_color": "white",
                "border": 1, "text_wrap": True, "valign": "top"
            })
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
                width = max(12, min(32, max(len(str(value)), int(df[value].astype(str).str.len().quantile(0.8)) if not df.empty else 12)))
                worksheet.set_column(col_num, col_num, width)
            worksheet.freeze_panes(1, 0)
    return output.getvalue()
