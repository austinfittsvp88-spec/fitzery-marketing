import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


DATABASE_PATH = Path(__file__).resolve().parent / "fitzery.db"


def _connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection, table_name):
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _columns(connection, table_name):
    if not _table_exists(connection, table_name):
        return []

    return [
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    ]


def _safe_count(connection, table_name):
    if not _table_exists(connection, table_name):
        return 0

    return int(
        connection.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()["total"]
    )


def _load_table(connection, table_name):
    if not _table_exists(connection, table_name):
        return pd.DataFrame()

    return pd.read_sql_query(f"SELECT * FROM {table_name}", connection)


def _find_table(connection, possible_names):
    for table_name in possible_names:
        if _table_exists(connection, table_name):
            return table_name
    return None


def _money(value):
    try:
        return f"${float(value or 0):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def _user_summary(connection):
    users_table = _find_table(connection, ["users", "user"])
    if not users_table:
        return pd.DataFrame()

    users = _load_table(connection, users_table)
    if users.empty:
        return users

    user_columns = _columns(connection, users_table)
    id_column = "id" if "id" in user_columns else user_columns[0]

    leads_table = _find_table(connection, ["leads", "crm_leads"])
    outputs_table = _find_table(connection, ["saved_outputs", "outputs", "reports"])
    profiles_table = _find_table(connection, ["business_profiles", "profiles", "business_settings"])

    leads = _load_table(connection, leads_table) if leads_table else pd.DataFrame()
    outputs = _load_table(connection, outputs_table) if outputs_table else pd.DataFrame()
    profiles = _load_table(connection, profiles_table) if profiles_table else pd.DataFrame()

    summary_rows = []

    for _, user in users.iterrows():
        user_id = user.get(id_column)

        user_leads = pd.DataFrame()
        if not leads.empty and "user_id" in leads.columns:
            user_leads = leads[leads["user_id"] == user_id]

        user_outputs = pd.DataFrame()
        if not outputs.empty and "user_id" in outputs.columns:
            user_outputs = outputs[outputs["user_id"] == user_id]

        user_profile = pd.DataFrame()
        if not profiles.empty and "user_id" in profiles.columns:
            user_profile = profiles[profiles["user_id"] == user_id]

        active_leads = 0
        pipeline = 0.0

        if not user_leads.empty:
            if "status" in user_leads.columns:
                active_mask = ~user_leads["status"].isin(["Closed Won", "Closed Lost"])
                active_leads = int(active_mask.sum())
                active_rows = user_leads[active_mask]
            else:
                active_leads = len(user_leads)
                active_rows = user_leads

            value_column = None
            for candidate in ["value", "potential_value", "pipeline_value"]:
                if candidate in user_leads.columns:
                    value_column = candidate
                    break

            if value_column:
                pipeline = pd.to_numeric(
                    active_rows[value_column],
                    errors="coerce",
                ).fillna(0).sum()

        business_name = ""
        monthly_revenue = 0.0
        monthly_goal = 0.0

        if not user_profile.empty:
            profile_row = user_profile.iloc[0]

            if "business_name" in user_profile.columns:
                business_name = profile_row.get("business_name", "") or ""

            if "monthly_revenue" in user_profile.columns:
                monthly_revenue = profile_row.get("monthly_revenue", 0) or 0

            if "monthly_goal" in user_profile.columns:
                monthly_goal = profile_row.get("monthly_goal", 0) or 0

        created_at = ""
        for candidate in ["created_at", "created", "date_created"]:
            if candidate in users.columns:
                created_at = user.get(candidate, "") or ""
                break

        summary_rows.append(
            {
                "User ID": user_id,
                "Email": user.get("email", ""),
                "Plan": user.get("plan", "Starter") or "Starter",
                "Plan status": user.get("plan_status", "test") or "test",
                "Business": business_name,
                "Active leads": active_leads,
                "Pipeline": float(pipeline),
                "Saved reports": len(user_outputs),
                "Monthly revenue": float(monthly_revenue or 0),
                "Monthly goal": float(monthly_goal or 0),
                "Created": created_at,
            }
        )

    return pd.DataFrame(summary_rows)


def render_admin_dashboard():
    st.markdown(
        """
        <div class="hero">
            <h1>Admin Dashboard</h1>
            <p>Manage Fitzery users, plans, activity, leads, reports, and platform growth.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not DATABASE_PATH.exists():
        st.error("The Fitzery database file could not be found.")
        return

    with _connect() as connection:
        users_table = _find_table(connection, ["users", "user"])
        leads_table = _find_table(connection, ["leads", "crm_leads"])
        outputs_table = _find_table(connection, ["saved_outputs", "outputs", "reports"])

        users_count = _safe_count(connection, users_table) if users_table else 0
        leads_count = _safe_count(connection, leads_table) if leads_table else 0
        reports_count = _safe_count(connection, outputs_table) if outputs_table else 0

        won_count = 0
        pipeline_value = 0.0

        if leads_table:
            lead_columns = _columns(connection, leads_table)

            if "status" in lead_columns:
                won_count = int(
                    connection.execute(
                        f"SELECT COUNT(*) AS total FROM {leads_table} WHERE status = ?",
                        ("Closed Won",),
                    ).fetchone()["total"]
                )

            value_column = None
            for candidate in ["value", "potential_value", "pipeline_value"]:
                if candidate in lead_columns:
                    value_column = candidate
                    break

            if value_column:
                if "status" in lead_columns:
                    row = connection.execute(
                        f"""
                        SELECT COALESCE(SUM({value_column}), 0) AS total
                        FROM {leads_table}
                        WHERE status NOT IN (?, ?)
                        """,
                        ("Closed Won", "Closed Lost"),
                    ).fetchone()
                else:
                    row = connection.execute(
                        f"SELECT COALESCE(SUM({value_column}), 0) AS total FROM {leads_table}"
                    ).fetchone()

                pipeline_value = float(row["total"] or 0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Registered Users", users_count)
        c2.metric("Total Leads", leads_count)
        c3.metric("Open Pipeline", _money(pipeline_value))
        c4.metric("Saved Reports", reports_count)

        users = _user_summary(connection)

        st.markdown("### Plan Breakdown")
        if users.empty:
            st.info("No registered customer accounts were found.")
        else:
            plan_counts = (
                users["Plan"]
                .fillna("Starter")
                .value_counts()
                .rename_axis("Plan")
                .reset_index(name="Customers")
            )
            st.dataframe(plan_counts, use_container_width=True, hide_index=True)

        st.markdown("### Customer Accounts")
        if users.empty:
            st.info("No registered customer accounts were found.")
        else:
            search = st.text_input(
                "Search customers",
                placeholder="Email, business name, or plan",
            ).strip().lower()

            filtered = users.copy()

            if search:
                filtered = filtered[
                    filtered["Email"].astype(str).str.lower().str.contains(search, na=False)
                    | filtered["Business"].astype(str).str.lower().str.contains(search, na=False)
                    | filtered["Plan"].astype(str).str.lower().str.contains(search, na=False)
                ]

            display_users = filtered.copy()
            display_users["Pipeline"] = display_users["Pipeline"].map(_money)
            display_users["Monthly revenue"] = display_users["Monthly revenue"].map(_money)
            display_users["Monthly goal"] = display_users["Monthly goal"].map(_money)

            st.dataframe(
                display_users,
                use_container_width=True,
                hide_index=True,
            )

            csv_data = filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download customer list",
                data=csv_data,
                file_name=f"fitzery_customers_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.info(
        "Plan selection is currently in testing mode. No customer is charged until Stripe is connected."
    )
