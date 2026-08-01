import os

import streamlit as st
from dotenv import load_dotenv

from admin_page import render_admin_dashboard
from auth import auth_screen, logout_button
from database import get_user_plan, initialize_database
from pages import (
    render_dashboard,
    render_ceo_advisor,
    render_marketing,
    render_social,
    render_email,
    render_sales,
    render_reviews,
    render_seo,
    render_crm,
    render_reports,
    render_settings,
)
from pricing_page import render_pricing_page
from stripe_checkout import process_checkout_return
from styles import apply_styles

load_dotenv()

st.set_page_config(
    page_title="Fitzery Marketing V5",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_database()
apply_styles()

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    auth_screen()
    st.stop()

checkout_result = process_checkout_return(st.session_state.user["id"])

if checkout_result:
    if checkout_result["status"] == "success":
        st.success(checkout_result["message"])
        st.balloons()
    elif checkout_result["status"] == "cancelled":
        st.warning(checkout_result["message"])
    else:
        st.error(checkout_result["message"])

current_email = str(st.session_state.user.get("email", "")).strip().lower()
admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
is_admin = bool(admin_email) and current_email == admin_email

plan_info = get_user_plan(st.session_state.user["id"])
current_plan = plan_info["plan"]
plan_status = plan_info["plan_status"]

navigation = [
    "Dashboard",
    "CEO Advisor",
    "Pricing Plans",
    "Marketing Strategy",
    "Social Media",
    "Email Campaigns",
    "Sales Assistant",
    "Review Manager",
    "SEO",
    "CRM",
    "Reports",
    "Business Settings",
]

if is_admin:
    navigation.insert(1, "Admin Dashboard")

with st.sidebar:
    st.markdown("# Fitzery Marketing")
    st.caption("Business Growth Platform • V5")
    st.divider()

    page = st.radio(
        "Navigation",
        navigation,
        label_visibility="collapsed",
    )

    st.divider()
    st.caption(f"Plan: {current_plan}")
    st.caption(f"Subscription: {plan_status.title()}")
    st.caption(f"Signed in as {st.session_state.user['email']}")

    if is_admin:
        st.success("Administrator account")

    logout_button()

page_map = {
    "Dashboard": render_dashboard,
    "CEO Advisor": render_ceo_advisor,
    "Pricing Plans": render_pricing_page,
    "Marketing Strategy": render_marketing,
    "Social Media": render_social,
    "Email Campaigns": render_email,
    "Sales Assistant": render_sales,
    "Review Manager": render_reviews,
    "SEO": render_seo,
    "CRM": render_crm,
    "Reports": render_reports,
    "Business Settings": render_settings,
}

if page == "Admin Dashboard":
    if not is_admin:
        st.error("Administrator access is required.")
        st.stop()
    render_admin_dashboard()
else:
    page_map[page]()
