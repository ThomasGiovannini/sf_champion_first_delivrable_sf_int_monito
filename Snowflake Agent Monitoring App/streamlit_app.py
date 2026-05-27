import os
from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Snowflake Intelligence Monitoring",
    page_icon=":material/monitoring:",
    layout="wide",
)

st.title("Snowflake Intelligence Monitoring")

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))


@st.cache_data(ttl=300)
def load_daily_spend():
    return conn.query(
        "SELECT USER_NAME, USAGE_DATE, SPEND_USD "
        "FROM MONITORING_DB.AI_OBSERVABILITY.FACT_SNOWFLAKE_INTELLIGENCE_DAY_USER_AGG "
        "ORDER BY USAGE_DATE DESC"
    )


@st.cache_data(ttl=300)
def load_requests():
    return conn.query(
        "SELECT REQUEST_ID, REQUEST_SOURCE, USAGE_DATE, USER_NAME, ROLE_NAME, "
        "AGENT_NAME, STATUS, DURATION, CORTEX_ANALYST_FLAG, CORTEX_SEARCH_FLAG, "
        "CORTEX_CHART_FLAG, CUSTOM_TOOLS_FLAG, FEEDBACK, FEEDBACK_MESSAGE "
        "FROM MONITORING_DB.AI_OBSERVABILITY.SNOWFLAKE_INTELLIGENCE_REQUESTS "
        "ORDER BY USAGE_DATE DESC"
    )


@st.cache_data(ttl=300)
def load_request_details():
    return conn.query(
        "SELECT REQUEST_ID, USAGE_DATE, USER_NAME, REQUEST_TYPE, LLM, "
        "TOKENS_INPUT, TOKENS_OUTPUT, TOKENS_READ_INPUT, TOKENS_WRITE_INPUT, "
        "CREDITS_INPUT, CREDITS_OUTPUT, CREDITS_READ_INPUT, CREDITS_WRITE_INPUT "
        "FROM MONITORING_DB.AI_OBSERVABILITY.FACT_SNOWFLAKE_INTELLIGENCE_REQUESTS_DETAILS "
        "ORDER BY USAGE_DATE DESC"
    )


if st.button("Refresh Data", type="secondary"):
    load_daily_spend.clear()
    load_requests.clear()
    load_request_details.clear()
    st.rerun()

with st.spinner("Loading data..."):
    df_spend = load_daily_spend()
    df_requests = load_requests()
    df_details = load_request_details()

if df_spend.empty and df_requests.empty:
    st.warning("No data found. Ensure you have access to MONITORING_DB.AI_OBSERVABILITY views.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    min_date = df_spend["USAGE_DATE"].min() if not df_spend.empty else date.today() - timedelta(days=30)
    max_date = df_spend["USAGE_DATE"].max() if not df_spend.empty else date.today()
    date_range = st.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    all_users = sorted(df_requests["USER_NAME"].dropna().unique().tolist()) if not df_requests.empty else []
    selected_users = st.multiselect("Users", all_users, default=all_users)

    all_agents = sorted(df_requests["AGENT_NAME"].dropna().unique().tolist()) if not df_requests.empty else []
    selected_agents = st.multiselect("Agents", all_agents, default=all_agents)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

mask_spend = (
    (df_spend["USAGE_DATE"] >= start_date)
    & (df_spend["USAGE_DATE"] <= end_date)
    & (df_spend["USER_NAME"].isin(selected_users))
)
df_spend_filtered = df_spend[mask_spend]

mask_requests = (
    (df_requests["USAGE_DATE"] >= start_date)
    & (df_requests["USAGE_DATE"] <= end_date)
    & (df_requests["USER_NAME"].isin(selected_users))
    & (df_requests["AGENT_NAME"].isin(selected_agents))
)
df_requests_filtered = df_requests[mask_requests]

mask_details = (
    (df_details["USAGE_DATE"] >= start_date)
    & (df_details["USAGE_DATE"] <= end_date)
    & (df_details["USER_NAME"].isin(selected_users))
)
df_details_filtered = df_details[mask_details]

tab_overview, tab_cost, tab_usage, tab_feedback, tab_details = st.tabs(
    ["Overview", "Cost Analysis", "Usage by User/Agent", "Feedback", "Request Details"]
)

with tab_overview:
    total_spend = df_spend_filtered["SPEND_USD"].sum()
    total_requests = len(df_requests_filtered)
    unique_users = df_requests_filtered["USER_NAME"].nunique()
    unique_agents = df_requests_filtered["AGENT_NAME"].nunique()
    avg_duration = df_requests_filtered["DURATION"].mean() if not df_requests_filtered.empty else 0

    with st.container(horizontal=True):
        st.metric("Total Spend (USD)", f"${total_spend:,.2f}", border=True)
        st.metric("Total Requests", f"{total_requests:,}", border=True)
        st.metric("Unique Users", unique_users, border=True)
        st.metric("Unique Agents", unique_agents, border=True)
        st.metric("Avg Duration (ms)", f"{avg_duration:,.0f}", border=True)

    if not df_spend_filtered.empty:
        daily_total = df_spend_filtered.groupby("USAGE_DATE")["SPEND_USD"].sum().reset_index()
        chart = (
            alt.Chart(daily_total)
            .mark_area(opacity=0.4, line=True)
            .encode(
                x=alt.X("USAGE_DATE:T", title="Date"),
                y=alt.Y("SPEND_USD:Q", title="Spend (USD)"),
            )
            .properties(height=300)
        )
        with st.container(border=True):
            st.subheader("Daily Spend Trend")
            st.altair_chart(chart, use_container_width=True)

    if not df_requests_filtered.empty:
        status_counts = df_requests_filtered["STATUS"].value_counts().reset_index()
        status_counts.columns = ["STATUS", "COUNT"]
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.subheader("Requests by Status")
                st.bar_chart(status_counts, x="STATUS", y="COUNT")
        with col2:
            tool_usage = pd.DataFrame({
                "Tool": ["Cortex Analyst", "Cortex Search", "Cortex Chart", "Custom Tools"],
                "Count": [
                    df_requests_filtered["CORTEX_ANALYST_FLAG"].sum(),
                    df_requests_filtered["CORTEX_SEARCH_FLAG"].sum(),
                    df_requests_filtered["CORTEX_CHART_FLAG"].sum(),
                    df_requests_filtered["CUSTOM_TOOLS_FLAG"].sum(),
                ],
            })
            with st.container(border=True):
                st.subheader("Tool Usage")
                st.bar_chart(tool_usage, x="Tool", y="Count")

with tab_cost:
    if not df_spend_filtered.empty:
        user_spend = df_spend_filtered.groupby("USER_NAME")["SPEND_USD"].sum().reset_index().sort_values("SPEND_USD", ascending=False)
        with st.container(border=True):
            st.subheader("Spend by User")
            st.bar_chart(user_spend.head(20), x="USER_NAME", y="SPEND_USD")

    if not df_details_filtered.empty:
        type_spend = df_details_filtered.groupby("REQUEST_TYPE").agg(
            CREDITS_TOTAL=("CREDITS_INPUT", "sum"),
            TOKENS_TOTAL=("TOKENS_INPUT", "sum"),
        ).reset_index().sort_values("CREDITS_TOTAL", ascending=False)
        with st.container(border=True):
            st.subheader("Credits by Request Type")
            st.dataframe(type_spend, hide_index=True, use_container_width=True)

        llm_spend = df_details_filtered.groupby("LLM").agg(
            TOKENS_INPUT=("TOKENS_INPUT", "sum"),
            TOKENS_OUTPUT=("TOKENS_OUTPUT", "sum"),
            REQUEST_COUNT=("REQUEST_ID", "count"),
        ).reset_index().sort_values("TOKENS_INPUT", ascending=False)
        with st.container(border=True):
            st.subheader("Token Usage by LLM")
            st.dataframe(llm_spend, hide_index=True, use_container_width=True)

with tab_usage:
    if not df_requests_filtered.empty:
        user_requests = df_requests_filtered.groupby("USER_NAME").size().reset_index(name="REQUEST_COUNT").sort_values("REQUEST_COUNT", ascending=False)
        with st.container(border=True):
            st.subheader("Requests by User")
            st.bar_chart(user_requests.head(20), x="USER_NAME", y="REQUEST_COUNT")

        agent_requests = df_requests_filtered.groupby("AGENT_NAME").size().reset_index(name="REQUEST_COUNT").sort_values("REQUEST_COUNT", ascending=False)
        with st.container(border=True):
            st.subheader("Requests by Agent")
            st.bar_chart(agent_requests, x="AGENT_NAME", y="REQUEST_COUNT")

        daily_requests = df_requests_filtered.groupby("USAGE_DATE").size().reset_index(name="REQUEST_COUNT")
        chart = (
            alt.Chart(daily_requests)
            .mark_line(point=True)
            .encode(
                x=alt.X("USAGE_DATE:T", title="Date"),
                y=alt.Y("REQUEST_COUNT:Q", title="Requests"),
            )
            .properties(height=300)
        )
        with st.container(border=True):
            st.subheader("Daily Request Volume")
            st.altair_chart(chart, use_container_width=True)

with tab_feedback:
    if not df_requests_filtered.empty:
        feedback_df = df_requests_filtered[df_requests_filtered["FEEDBACK"].notna()]
        if not feedback_df.empty:
            feedback_counts = feedback_df["FEEDBACK"].value_counts().reset_index()
            feedback_counts.columns = ["FEEDBACK", "COUNT"]

            with st.container(horizontal=True):
                total_feedback = len(feedback_df)
                positive = len(feedback_df[feedback_df["FEEDBACK"].str.lower() == "positive"])
                negative = len(feedback_df[feedback_df["FEEDBACK"].str.lower() == "negative"])
                st.metric("Total Feedback", total_feedback, border=True)
                st.metric("Positive", positive, border=True)
                st.metric("Negative", negative, border=True)
                if total_feedback > 0:
                    st.metric("Satisfaction Rate", f"{positive / total_feedback * 100:.1f}%", border=True)

            with st.container(border=True):
                st.subheader("Feedback Distribution")
                st.bar_chart(feedback_counts, x="FEEDBACK", y="COUNT")

            negative_feedback = feedback_df[
                (feedback_df["FEEDBACK"].str.lower() == "negative")
                & (feedback_df["FEEDBACK_MESSAGE"].notna())
            ][["USAGE_DATE", "USER_NAME", "AGENT_NAME", "FEEDBACK_MESSAGE"]]
            if not negative_feedback.empty:
                with st.container(border=True):
                    st.subheader("Negative Feedback Messages")
                    st.dataframe(negative_feedback, hide_index=True, use_container_width=True)
        else:
            st.info("No feedback data available for the selected filters.")

with tab_details:
    if not df_requests_filtered.empty:
        with st.container(border=True):
            st.subheader("Request Log")
            st.dataframe(
                df_requests_filtered[
                    ["USAGE_DATE", "USER_NAME", "AGENT_NAME", "STATUS", "DURATION", "FEEDBACK"]
                ],
                hide_index=True,
                use_container_width=True,
            )

    if not df_details_filtered.empty:
        with st.container(border=True):
            st.subheader("Token & Credit Details")
            st.dataframe(
                df_details_filtered[
                    ["USAGE_DATE", "USER_NAME", "REQUEST_TYPE", "LLM",
                     "TOKENS_INPUT", "TOKENS_OUTPUT", "CREDITS_INPUT", "CREDITS_OUTPUT"]
                ],
                hide_index=True,
                use_container_width=True,
            )