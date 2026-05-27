# Snowflake Intelligence Monitoring

A Streamlit in Snowflake app to monitor Snowflake Intelligence and Cortex Agent usage, costs, and user feedback.

## Prerequisites

- A Snowflake account with access to:
  - `SNOWFLAKE.ACCOUNT_USAGE.SNOWFLAKE_INTELLIGENCE_USAGE_HISTORY`
  - `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY`
  - `SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES`
  - `SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS`
- A role with `IMPORTED PRIVILEGES` on the `SNOWFLAKE` database
- A warehouse (e.g. `SANDBOX_WH`)

## Setup

### 1. Create the database and views

Run the SQL script in `setup/01_create_views.sql` using a role with ACCOUNTADMIN or equivalent privileges:

```sql
-- Execute all statements in setup/01_create_views.sql
```

This creates:

| Schema | View |
|--------|------|
| `MONITORING_DB.USAGE_MONITORING` | `STG_ROLE_TAGS` |
| `MONITORING_DB.USAGE_MONITORING` | `STG_SNOWFLAKE_INTELLIGENCE` |
| `MONITORING_DB.USAGE_MONITORING` | `STG_CORTEX_AGENT` |
| `MONITORING_DB.AI_OBSERVABILITY` | `STG_SNOWFLAKE_INTELLIGENCE_OBSERVABILITY` |
| `MONITORING_DB.AI_OBSERVABILITY` | `SNOWFLAKE_INTELLIGENCE_REQUESTS` |
| `MONITORING_DB.AI_OBSERVABILITY` | `FACT_SNOWFLAKE_INTELLIGENCE_REQUESTS_DETAILS` |
| `MONITORING_DB.AI_OBSERVABILITY` | `FACT_SNOWFLAKE_INTELLIGENCE_DAY_USER_AGG` |

### 2. Grant access

Run `setup/02_grant_access.sql` after replacing `<YOUR_ROLE>` with the role that will run the Streamlit app:

```sql
-- Execute all statements in setup/02_grant_access.sql
```

### 3. Preview the app (Workspace)

1. Copy the contents of `streamlit/` into a new Workspace folder
2. Set the app role to your granted role in **App Settings**
3. Click **Run** to preview the app in development mode

### 4. Deploy as a Streamlit app

Once you've validated the app in preview, deploy it as a permanent Streamlit app:

**Option A — Via Snowsight UI:**

1. In your Workspace, click **Deploy** (top-right)
2. Choose the target database and schema (e.g. `MONITORING_DB.AI_OBSERVABILITY`)
3. Set the app title (e.g. `Snowflake Intelligence Monitoring`)
4. Assign the query warehouse and role
5. Click **Deploy**

**Option B — Via Snow CLI:**

```bash
cd streamlit
snow streamlit deploy --database MONITORING_DB --schema AI_OBSERVABILITY
```

**Option C — Via SQL:**

```sql
CREATE STREAMLIT MONITORING_DB.AI_OBSERVABILITY.SNOWFLAKE_INTELLIGENCE_MONITORING
    FROM 'snow://workspace/<YOUR_WORKSPACE>/versions/live/streamlit'
    MAIN_FILE = 'streamlit_app.py'
    QUERY_WAREHOUSE = 'SANDBOX_WH'
    TITLE = 'Snowflake Intelligence Monitoring';
```

## App Features

| Tab | Description |
|-----|-------------|
| **Overview** | KPIs (total spend, requests, users, agents) + daily spend trend chart |
| **Cost Analysis** | Spend by user, credits by request type, token usage by LLM |
| **Usage by User/Agent** | Request volume breakdown by user and agent over time |
| **Feedback** | Satisfaction rate, positive/negative counts, negative feedback messages |
| **Request Details** | Full request log and token/credit detail tables |

## Project Structure

```
snowflake-intelligence-monitoring/
├── README.md
├── setup/
│   ├── 01_create_views.sql
│   └── 02_grant_access.sql
└── streamlit/
    ├── .streamlit/
    │   └── config.toml
    ├── snowflake.yml
    ├── pyproject.toml
    └── streamlit_app.py
```

## Data Sources

The views are built on top of these Snowflake system tables:

| Source | Description |
|--------|-------------|
| `SNOWFLAKE.ACCOUNT_USAGE.SNOWFLAKE_INTELLIGENCE_USAGE_HISTORY` | Token and credit usage for Snowflake Intelligence |
| `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY` | Token and credit usage for Cortex Agents |
| `SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS` | Agent observability spans (status, tools, feedback) |
| `SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES` | Role tags for cost attribution |

## Notes

- The `SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS` table requires `IMPORTED PRIVILEGES` on the `SNOWFLAKE` database.
