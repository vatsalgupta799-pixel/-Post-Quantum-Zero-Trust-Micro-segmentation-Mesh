import streamlit as st
import pandas as pd
import streamlit as st
st.markdown("""
<style>
/* Main dashboard */
.stApp {
    background-color: #0B1020;
    color: #E5E7EB;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #111827;
    border-right: 1px solid #273449;
}

/* Headings */
h1, h2, h3 {
    color: #A78BFA !important;
}

/* General text */
p, label, [data-testid="stCaptionContainer"] {
    color: #E5E7EB;
}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: #151D31;
    border: 1px solid #7C3AED;
    padding: 16px;
    border-radius: 12px;
}

/* Metric values */
[data-testid="stMetricValue"] {
    color: #C4B5FD;
}

/* Search input */
.stTextInput input {
    background-color: #151D31 !important;
    color: #F9FAFB !important;
    border: 1px solid #8B5CF6 !important;
    border-radius: 8px;
}

/* Dropdown and severity filter */
div[data-baseweb="select"] > div {
    background-color: #151D31 !important;
    border: 1px solid #8B5CF6 !important;
    color: #F9FAFB !important;
    border-radius: 8px !important;
}

div[data-baseweb="select"] span {
    color: #F9FAFB !important;
}

div[data-baseweb="select"] svg {
    fill: #C4B5FD !important;
}

/* Dropdown options */
div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li {
    background-color: #151D31 !important;
    color: #F9FAFB !important;
}

div[data-baseweb="popover"] li:hover {
    background-color: #3B2A60 !important;
}

/* Buttons */
.stButton button {
    background-color: #7C3AED;
    color: white !important;
    border: 1px solid #8B5CF6;
    border-radius: 8px;
}

.stButton button:hover {
    background-color: #6D28D9;
    border-color: #C4B5FD;
}

/* Security events table */
[data-testid="stDataFrame"] {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    overflow: hidden;
}

/* Chart containers */
[data-testid="stPlotlyChart"] {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    padding: 10px;
}

/* Dividers */
hr {
    border-color: #374151;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Main dashboard */
.stApp {
    background-color: #0B1020;
    color: #E5E7EB;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #111827;
    border-right: 1px solid #273449;
}

/* Headings */
h1, h2, h3 {
    color: #A78BFA !important;
}

/* General text */
p, label, [data-testid="stCaptionContainer"] {
    color: #E5E7EB;
}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: #151D31;
    border: 1px solid #7C3AED;
    padding: 16px;
    border-radius: 12px;
}

/* Metric values */
[data-testid="stMetricValue"] {
    color: #C4B5FD;
}

/* Search input */
.stTextInput input {
    background-color: #151D31 !important;
    color: #F9FAFB !important;
    border: 1px solid #8B5CF6 !important;
    border-radius: 8px;
}

/* Dropdown and severity filter */
div[data-baseweb="select"] > div {
    background-color: #151D31 !important;
    border: 1px solid #8B5CF6 !important;
    color: #F9FAFB !important;
    border-radius: 8px !important;
}

div[data-baseweb="select"] span {
    color: #F9FAFB !important;
}

div[data-baseweb="select"] svg {
    fill: #C4B5FD !important;
}

/* Dropdown options */
div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li {
    background-color: #151D31 !important;
    color: #F9FAFB !important;
}

div[data-baseweb="popover"] li:hover {
    background-color: #3B2A60 !important;
}

/* Buttons */
.stButton button {
    background-color: #7C3AED;
    color: white !important;
    border: 1px solid #8B5CF6;
    border-radius: 8px;
}

.stButton button:hover {
    background-color: #6D28D9;
    border-color: #C4B5FD;
}

/* Security events table */
[data-testid="stDataFrame"] {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    overflow: hidden;
}

/* Chart containers */
[data-testid="stPlotlyChart"] {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    padding: 10px;
}

/* Dividers */
hr {
    border-color: #374151;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Main dashboard */
.stApp {
    background-color: #0B1020;
    color: #E5E7EB;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #111827;
    border-right: 1px solid #273449;
}

/* Headings */
h1, h2, h3 {
    color: #A78BFA !important;
}

/* General text */
p, label, [data-testid="stCaptionContainer"] {
    color: #E5E7EB;
}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: #151D31;
    border: 1px solid #7C3AED;
    padding: 16px;
    border-radius: 12px;
}

/* Metric values */
[data-testid="stMetricValue"] {
    color: #C4B5FD;
}

/* Search input */
.stTextInput input {
    background-color: #151D31 !important;
    color: #F9FAFB !important;
    border: 1px solid #8B5CF6 !important;
    border-radius: 8px;
}

/* Dropdown and severity filter */
div[data-baseweb="select"] > div {
    background-color: #151D31 !important;
    border: 1px solid #8B5CF6 !important;
    color: #F9FAFB !important;
    border-radius: 8px !important;
}

div[data-baseweb="select"] span {
    color: #F9FAFB !important;
}

div[data-baseweb="select"] svg {
    fill: #C4B5FD !important;
}

/* Dropdown options */
div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li {
    background-color: #151D31 !important;
    color: #F9FAFB !important;
}

div[data-baseweb="popover"] li:hover {
    background-color: #3B2A60 !important;
}

/* Buttons */
.stButton button {
    background-color: #7C3AED;
    color: white !important;
    border: 1px solid #8B5CF6;
    border-radius: 8px;
}

.stButton button:hover {
    background-color: #6D28D9;
    border-color: #C4B5FD;
}

/* Security events table */
[data-testid="stDataFrame"] {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    overflow: hidden;
}

/* Chart containers */
[data-testid="stPlotlyChart"] {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    padding: 10px;
}

/* Dividers */
hr {
    border-color: #374151;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Main dashboard */
.stApp {
    background-color: #0B1020;
    color: #E5E7EB;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #111827;
    border-right: 1px solid #273449;
}

/* Headings */
h1, h2, h3 {
    color: #A78BFA !important;
}

/* General text */
p, label, [data-testid="stCaptionContainer"] {
    color: #E5E7EB;
}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: #151D31;
    border: 1px solid #7C3AED;
    padding: 16px;
    border-radius: 12px;
}

/* Metric values */
[data-testid="stMetricValue"] {
    color: #C4B5FD;
}

/* Search input */
.stTextInput input {
    background-color: #151D31 !important;
    color: #F9FAFB !important;
    border: 1px solid #8B5CF6 !important;
    border-radius: 8px;
}

/* Dropdown and severity filter */
div[data-baseweb="select"] > div {
    background-color: #151D31 !important;
    border: 1px solid #8B5CF6 !important;
    color: #F9FAFB !important;
    border-radius: 8px !important;
}

div[data-baseweb="select"] span {
    color: #F9FAFB !important;
}

div[data-baseweb="select"] svg {
    fill: #C4B5FD !important;
}

/* Dropdown options */
div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li {
    background-color: #151D31 !important;
    color: #F9FAFB !important;
}

div[data-baseweb="popover"] li:hover {
    background-color: #3B2A60 !important;
}

/* Buttons */
.stButton button {
    background-color: #7C3AED;
    color: white !important;
    border: 1px solid #8B5CF6;
    border-radius: 8px;
}

.stButton button:hover {
    background-color: #6D28D9;
    border-color: #C4B5FD;
}

/* Security events table */
[data-testid="stDataFrame"] {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    overflow: hidden;
}

/* Chart containers */
[data-testid="stPlotlyChart"] {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    padding: 10px;
}

/* Dividers */
hr {
    border-color: #374151;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Main dashboard */
.stApp {
    background-color: #0B1020;
    color: #E5E7EB;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #111827;
    border-right: 1px solid #273449;
}

/* Headings */
h1, h2, h3 {
    color: #A78BFA !important;
}

/* General text */
p, label, [data-testid="stCaptionContainer"] {
    color: #E5E7EB;
}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: #151D31;
    border: 1px solid #7C3AED;
    padding: 16px;
    border-radius: 12px;
}

/* Metric values */
[data-testid="stMetricValue"] {
    color: #C4B5FD;
}

/* Search input */
.stTextInput input {
    background-color: #151D31 !important;
    color: #F9FAFB !important;
    border: 1px solid #8B5CF6 !important;
    border-radius: 8px;
}

/* Dropdown and severity filter */
div[data-baseweb="select"] > div {
    background-color: #151D31 !important;
    border: 1px solid #8B5CF6 !important;
    color: #F9FAFB !important;
    border-radius: 8px !important;
}

div[data-baseweb="select"] span {
    color: #F9FAFB !important;
}

div[data-baseweb="select"] svg {
    fill: #C4B5FD !important;
}

/* Dropdown options */
div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li {
    background-color: #151D31 !important;
    color: #F9FAFB !important;
}

div[data-baseweb="popover"] li:hover {
    background-color: #3B2A60 !important;
}

/* Buttons */
.stButton button {
    background-color: #7C3AED;
    color: white !important;
    border: 1px solid #8B5CF6;
    border-radius: 8px;
}

.stButton button:hover {
    background-color: #6D28D9;
    border-color: #C4B5FD;
}

/* Security events table */
[data-testid="stDataFrame"] {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    overflow: hidden;
}

/* Chart containers */
[data-testid="stPlotlyChart"] {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    padding: 10px;
}

/* Dividers */
hr {
    border-color: #374151;
}
</style>
""", unsafe_allow_html=True)
st.markdown("""

<style>

/* Main dashboard */

.stApp {

    background-color: #0B1020;

    color: #E5E7EB;

}

/* Sidebar */

[data-testid="stSidebar"] {

    background-color: #111827;

    border-right: 1px solid #273449;

}

/* Headings */

h1, h2, h3 {

    color: #A78BFA !important;

}

/* General text */

p, label, [data-testid="stCaptionContainer"] {

    color: #E5E7EB;

}

/* Metric cards */

[data-testid="stMetric"] {

    background-color: #151D31;

    border: 1px solid #7C3AED;

    padding: 16px;

    border-radius: 12px;

}

/* Metric values */

[data-testid="stMetricValue"] {

    color: #C4B5FD;

}

/* Search input */

.stTextInput input {

    background-color: #151D31 !important;

    color: #F9FAFB !important;

    border: 1px solid #8B5CF6 !important;

    border-radius: 8px;

}

/* Dropdown and severity filter */

div[data-baseweb="select"] > div {

    background-color: #151D31 !important;

    border: 1px solid #8B5CF6 !important;

    color: #F9FAFB !important;

    border-radius: 8px !important;

}

div[data-baseweb="select"] span {

    color: #F9FAFB !important;

}

div[data-baseweb="select"] svg {

    fill: #C4B5FD !important;

}

/* Dropdown options */

div[data-baseweb="popover"],

div[data-baseweb="popover"] ul,

div[data-baseweb="popover"] li {

    background-color: #151D31 !important;

    color: #F9FAFB !important;

}

div[data-baseweb="popover"] li:hover {

    background-color: #3B2A60 !important;

}

/* Buttons */

.stButton button {

    background-color: #7C3AED;

    color: white !important;

    border: 1px solid #8B5CF6;

    border-radius: 8px;

}

.stButton button:hover {

    background-color: #6D28D9;

    border-color: #C4B5FD;

}

/* Security events table */

[data-testid="stDataFrame"] {

    background-color: #111827;

    border: 1px solid #374151;

    border-radius: 10px;

    overflow: hidden;

}

/* Chart containers */

[data-testid="stPlotlyChart"] {

    background-color: #111827;

    border: 1px solid #374151;

    border-radius: 10px;

    padding: 10px;

}

/* Dividers */

hr {

    border-color: #374151;

}

</style>

""", unsafe_allow_html=True)
st.set_page_config(
    page_title="Security Monitoring Dashboard",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Security Monitoring Dashboard")
st.write("Monitor security events and identify suspicious activity.")

# Sample security events for development
events = [
    {
        "Time": "2026-10-12 09:15:00",
        "Source IP": "192.168.1.15",
        "Event": "Failed Login",
        "Severity": "High"
    },
    {
        "Time": "2026-10-12 09:18:00",
        "Source IP": "192.168.1.22",
        "Event": "Successful Login",
        "Severity": "Low"
    },
    {
        "Time": "2026-10-12 09:22:00",
        "Source IP": "192.168.1.40",
        "Event": "Multiple Failed Logins",
        "Severity": "Critical"
    },
    {
        "Time": "2026-10-12 09:25:00",
        "Source IP": "192.168.1.30",
        "Event": "Port Scan Detected",
        "Severity": "Medium"
    },
    {
    "time": "2026-10-14 21:00:00",
    "source_ip": "192.168.1.99",
    "event_type": "Failed Login",
    "severity": "High"
    },
    {
    "time": "2026-10-14 21:01:00",
    "source_ip": "192.168.1.99",
    "event_type": "Failed Login",
    "severity": "High"
    },
    {
    "time": "2026-10-14 21:02:00",
    "source_ip": "192.168.1.99",
    "event_type": "Failed Login",
    "severity": "High"
}
]

df = pd.DataFrame(events)
st.subheader("System Overview")

col1, col2, col3 = st.columns(3)

col1.metric("Total Events", len(df))
col2.metric(
    "High/Critical Alerts",
    df["Severity"].isin(["High", "Critical"]).sum()
)
col3.metric("Systems Monitored", df["Source IP"].nunique())

st.subheader("Security Events")

severity_filter = st.multiselect(
    "Filter by severity",
    options=["Critical", "High", "Medium", "Low"],
    default=["Critical", "High", "Medium", "Low"]
)

search_query = st.text_input(
    "Search by IP address or event type",
    placeholder="e.g. 192.168.1.99 or Failed Login"
)

filtered_df = df[df["Severity"].isin(severity_filter)]

if search_query:
    search_mask = (
        filtered_df["Source IP"].astype(str).str.contains(
            search_query, case=False, na=False
        )
        | filtered_df["Event"].astype(str).str.contains(
            search_query, case=False, na=False
        )
    )
    filtered_df = filtered_df[search_mask]

st.dataframe(filtered_df, width="stretch", hide_index=True)

st.caption("Development mode: all displayed events are simulated sample data.")

st.subheader("Security Events by Severity")

severity_counts = df["Severity"].value_counts().reindex(
    ["Critical", "High", "Medium", "Low"],
    fill_value=0
)

st.bar_chart(severity_counts)
st.subheader("🚨 Security Alerts")

critical_events = df[df["Severity"] == "Critical"]

if not critical_events.empty:
    st.error(
        f"Warning: {len(critical_events)} critical security event(s) detected!"
    )
    st.dataframe(critical_events, width="stretch", hide_index=True)
else:
    st.success("No critical security events detected.")
    # Security Event Summary
st.subheader("Security Event Summary")
st.write("Quick overview of recorded security events.")

severity_summary = {
    "Critical": 0,
    "High": 0,
    "Medium": 0,
    "Low": 0
}

for event in events:
    severity = event.get("severity", "").title()
    if severity in severity_summary:
        severity_summary[severity] += 1

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Critical Events", severity_summary["Critical"])

with col2:
    st.metric("High Events", severity_summary["High"])

with col3:
    st.metric("Medium Events", severity_summary["Medium"])

with col4:
    st.metric("Low Events", severity_summary["Low"])
    from collections import Counter

# Count failed login attempts by IP address
failed_logins = [
    event["source_ip"]
    for event in events
    if event.get("event_type") == "Failed Login"
]

login_counts = Counter(failed_logins)

st.subheader("Repeated Failed Login Detection")

suspicious_ips = {
    ip: count
    for ip, count in login_counts.items()
    if count >= 3
}

if suspicious_ips:
    for ip, count in suspicious_ips.items():
        st.warning(
            f"{count} failed login attempts detected from {ip}"
        )
else:
    st.success("No repeated failed login attempts detected.")
