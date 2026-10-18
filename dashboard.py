
from pathlib import Path

import pandas as pd
import streamlit as st

from analyzer import DATA_FILE, REPORT_DIR, analyze_readings

st.set_page_config(
    page_title="Semiconductor Process Analyzer",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 Semiconductor Process Data Analyzer")
st.caption(
    "Process monitoring, wafer quality analysis "
    "and data-quality review"
)

st.info(
    "Demonstration project: configured limits are illustrative "
    "and are not validated semiconductor factory specifications."
)

REQUIRED_COLUMNS = [
    "lot_id",
    "wafer_id",
    "temperature_c",
    "pressure_kpa",
    "defect_count",
]


@st.cache_data
def load_and_analyze(file_path, modified_time):
    raw_df = pd.read_csv(file_path)
    return analyze_readings(raw_df)


if not DATA_FILE.is_file():
    st.error(
        f"Input CSV not found: {DATA_FILE}. "
        "Check data/process_data.csv."
    )
    st.stop()

try:
    df = load_and_analyze(
        str(DATA_FILE),
        DATA_FILE.stat().st_mtime,
    )

except (ValueError, pd.errors.ParserError,
        pd.errors.EmptyDataError, OSError) as exc:
    st.error(f"Could not load or validate process data: {exc}")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")

lots = sorted(df["lot_id"].astype(str).unique().tolist())

selected_lots = st.sidebar.multiselect(
    "Select lot IDs",
    options=lots,
    default=lots,
)

show_flagged_only = st.sidebar.checkbox(
    "Show flagged readings only",
    value=False,
)

filtered = df[
    df["lot_id"].astype(str).isin(selected_lots)
].copy()

if filtered.empty:
    st.warning(
        "No readings match your selected lots. "
        "Select at least one lot to continue."
    )
    st.stop()

# Calculate KPIs using the selected lots
flagged = filtered["abnormal"].astype(bool)
flagged_count = int(flagged.sum())
review_rate = flagged_count / len(filtered) * 100

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Readings", len(filtered))
c2.metric("Flagged Readings", flagged_count)
c3.metric(
    "Average Temperature",
    f"{filtered['temperature_c'].mean():.2f} °C",
)
c4.metric(
    "Average Pressure",
    f"{filtered['pressure_kpa'].mean():.2f} kPa",
)

st.caption(
    f"Flagged review rate: {review_rate:.1f}% "
    f"({flagged_count} of {len(filtered)} readings)"
)

st.divider()

# Data quality summary
st.subheader("Data Quality & Review")

q1, q2, q3 = st.columns(3)

q1.metric(
    "Missing Values After Validation",
    int(filtered[REQUIRED_COLUMNS].isna().sum().sum()),
)

q2.metric(
    "Lots Selected",
    filtered["lot_id"].nunique(),
)

q3.metric(
    "Unique Wafers",
    filtered["wafer_id"].nunique(),
)

# Trend charts
st.subheader("Process Trends")

chart_data = filtered[
    ["temperature_c", "pressure_kpa", "defect_count"]
].copy()

chart_data.insert(
    0,
    "Reading",
    range(1, len(chart_data) + 1),
)

tab1, tab2, tab3 = st.tabs(
    ["Temperature", "Pressure", "Defect Count"]
)

with tab1:
    st.line_chart(
        chart_data.set_index("Reading")[["temperature_c"]],
        y_label="Temperature (°C)",
    )

with tab2:
    st.line_chart(
        chart_data.set_index("Reading")[["pressure_kpa"]],
        y_label="Pressure (kPa)",
    )

with tab3:
    st.bar_chart(
        chart_data.set_index("Reading")[["defect_count"]],
        y_label="Defect Count",
    )

# Wafer readings
st.subheader("Wafer Readings")

display_df = filtered.copy()
display_df["review_status"] = display_df["abnormal"].map(
    {True: "REVIEW", False: "WITHIN DEMO LIMITS"}
)

if show_flagged_only:
    display_df = display_df[display_df["abnormal"]].copy()

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)

# Review details
st.subheader("Readings Flagged for Review")

flagged_df = filtered[filtered["abnormal"]].copy()

if flagged_df.empty:
    st.success("No readings are flagged in the selected lots.")
else:
    st.dataframe(
        flagged_df[
            [
                "lot_id",
                "wafer_id",
                "temperature_c",
                "pressure_kpa",
                "defect_count",
                "abnormal_reasons",
                "status",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

# Download selected readings
st.subheader("Export Reports")

download_df = filtered.copy()
download_df["review_status"] = download_df["abnormal"].map(
    {True: "REVIEW", False: "WITHIN DEMO LIMITS"}
)

csv_data = download_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Filtered CSV",
    data=csv_data,
    file_name="filtered_readings.csv",
    mime="text/csv",
)

st.caption(
    f"Source: {DATA_FILE.relative_to(DATA_FILE.parent.parent)}"
)
st.caption(
    f"Generated reports directory: {REPORT_DIR}"
)
