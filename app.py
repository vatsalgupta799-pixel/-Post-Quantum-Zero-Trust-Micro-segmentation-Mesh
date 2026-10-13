import streamlit as st
import pandas as pd

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

filtered_df = df[df["Severity"].isin(severity_filter)]

st.dataframe(filtered_df, use_container_width=True, hide_index=True)

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
    st.dataframe(critical_events, use_container_width=True, hide_index=True)
else:
    st.success("No critical security events detected.")