import streamlit as st

from database import get_user_plan
from stripe_checkout import (create_billing_portal_url,create_checkout_url,get_subscription_details,)


PLANS = {
    "Starter": {
        "price": "$59/month",
        "description": "For solo business owners getting started.",
        "features": [
            "Dashboard and CEO Advisor",
            "Marketing, email, sales, reviews, and SEO tools",
            "Up to 50 CRM leads",
            "10 generated plans per month",
            "Basic saved reports",
        ],
    },
    "Growth": {
        "price": "$99/month",
        "description": "For businesses actively building sales and marketing.",
        "features": [
            "Everything in Starter",
            "Unlimited CRM leads",
            "50 generated plans per month",
            "Advanced follow-up and analytics",
            "PDF report exports",
            "Priority support",
        ],
    },
    "Pro": {
        "price": "$199/month",
        "description": "For established businesses and growing teams.",
        "features": [
            "Everything in Growth",
            "Unlimited generated plans",
            "Advanced reporting",
            "Customer and lead data exports",
            "Team and multi-location features when released",
            "Fastest support",
        ],
    },
}


def _apply_pricing_styles():
    st.markdown(
        """
        <style>
        div[data-testid="stLinkButton"] a {
            background: linear-gradient(90deg, #35b31f, #74df32) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,.18) !important;
            font-weight: 800 !important;
            min-height: 46px !important;
        }

        div[data-testid="stLinkButton"] a:hover {
            color: #ffffff !important;
            filter: brightness(1.08);
        }

        div[data-testid="stLinkButton"] a p,
        div[data-testid="stLinkButton"] a span {
            color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _checkout_button(plan_name: str, current_plan: str, plan_status: str):
    is_current_active = current_plan == plan_name and plan_status == "active"

    if is_current_active:
        st.button(
            f"{plan_name} — Active",
            key=f"active_{plan_name}",
            disabled=True,
            use_container_width=True,
        )
        return

    label = (
        f"Test checkout — {plan_name}"
        if plan_status != "active"
        else f"Change to {plan_name}"
    )

    if st.button(
        label,
        key=f"checkout_{plan_name}",
        use_container_width=True,
    ):
        try:
            checkout_url = create_checkout_url(
                user_id=st.session_state.user["id"],
                email=st.session_state.user["email"],
                plan_name=plan_name,
            )

            st.session_state[f"stripe_url_{plan_name}"] = checkout_url

        except Exception as exc:
            st.error(f"Could not start Stripe Checkout: {exc}")

    checkout_url = st.session_state.get(f"stripe_url_{plan_name}")

    if checkout_url:
        st.link_button(
            f"Continue to Stripe — {plan_name}",
            checkout_url,
            use_container_width=True,
        )

def _subscription_management(current: dict):

    st.markdown("### Subscription Status")

    plan_status = current.get("plan_status", "inactive")

    subscription_id = current.get("stripe_subscription_id", "")

    stripe_details = {

        "status": plan_status,

        "cancel_at_period_end": False,

        "current_period_end": None,

    }

    if subscription_id:

        try:

            stripe_details = get_subscription_details(subscription_id)

        except Exception as exc:

            st.warning(

                "Fitzery could not refresh the latest Stripe status. "

                f"Showing the saved account status instead. Details: {exc}"

            )

    stripe_status = stripe_details.get("status", plan_status)

    canceling = stripe_details.get("cancel_at_period_end", False)

    period_end = stripe_details.get("current_period_end")

    end_date = None

    if period_end:

        from datetime import datetime

        try:

            end_date = datetime.fromtimestamp(period_end).strftime(

                "%B %d, %Y"

            )

        except (TypeError, ValueError, OSError):

            end_date = None

    if canceling:

        if end_date:

            st.warning(

                f"🟡 Canceling on {end_date}\n\n"

                "Your subscription remains active until that date "

                "and will not renew."

            )

        else:

            st.warning(

                "🟡 Canceling at the end of the billing period.\n\n"

                "Your subscription remains active until then."

            )

    elif stripe_status == "active":

        st.success(

            "🟢 Active\n\n"

            "Your subscription is active and will renew automatically."

        )

    elif stripe_status == "trialing":

        if end_date:

            st.info(f"⚪ Trial active until {end_date}.")

        else:

            st.info("⚪ Trial subscription active.")

    elif stripe_status in {"past_due", "unpaid"}:

        st.warning(

            "🟠 Payment issue\n\n"

            "Stripe could not successfully process the latest payment. "

            "Update the payment method to prevent service interruption."

        )

    elif stripe_status in {"canceled", "cancelled", "inactive"}:

        st.error(

            "🔴 Subscription inactive\n\n"

            "Choose a plan to restore paid access."

        )

    else:

        st.info(

            f"Subscription status: {stripe_status.replace('_', ' ').title()}"

        )

    st.markdown("### Manage Subscription")

    if not subscription_id:

        st.info(

            "Complete a Stripe subscription before using "

            "subscription management."

        )

        return

    st.write(

        "Open Stripe's secure billing portal to update your payment "

        "method, view your subscription, or cancel it."

    )

    if st.button(

        "Open Stripe Billing Portal",

        key="open_billing_portal",

        use_container_width=True,

    ):

        try:

            portal_url = create_billing_portal_url(

                current["stripe_customer_id"]

            )

            st.session_state.stripe_portal_url = portal_url

        except Exception as exc:

            st.error(f"Could not open Stripe Billing Portal: {exc}")

    portal_url = st.session_state.get("stripe_portal_url")

    if portal_url:

        st.link_button(

            "Continue to Subscription Management",

            portal_url,

            use_container_width=True,

        )

    st.caption(

        "Sandbox mode only. Changes here affect test subscriptions, "

        "not real money."

    )

def render_pricing_page():
    _apply_pricing_styles()

    user_id = st.session_state.user["id"]
    current = get_user_plan(user_id)
    current_plan = current["plan"]
    plan_status = current["plan_status"]

    st.markdown(
        """
        <div class="hero">
            <h1>Pricing Plans</h1>
            <p>Choose the Fitzery plan that matches your business growth stage.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.warning(
        "Stripe Sandbox Mode: use only Stripe test cards. "
        "No real money will be charged."
    )

    columns = st.columns(3)

    for column, (plan_name, plan) in zip(columns, PLANS.items()):
        with column:
            is_current = current_plan == plan_name
            status_text = (
                "Active subscription"
                if is_current and plan_status == "active"
                else "Current test plan"
                if is_current
                else "Available"
            )

            features_html = "".join(
                f"<p>✓ {feature}</p>" for feature in plan["features"]
            )

            st.markdown(
                f"""
                <div class="metric-card" style="min-height: 420px;">
                    <div class="metric-label">{status_text}</div>
                    <div class="metric-value">{plan_name}</div>
                    <div class="metric-note" style="font-size:1.05rem;">
                        {plan['price']}
                    </div>
                    <p style="margin-top:16px;">{plan['description']}</p>
                    <hr style="border-color:rgba(255,255,255,.12);">
                    {features_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

            _checkout_button(plan_name, current_plan, plan_status)

    st.markdown("### Current Subscription")

    if plan_status == "active":
        st.success(
            f"**Plan:** {current_plan}\n\n"
            "**Status:** Active Stripe sandbox subscription\n\n"
            "This is still a test subscription and does not move real money."
        )
    else:
        st.info(
            f"**Plan:** {current_plan}\n\n"
            f"**Status:** {plan_status.title()}"
        )

    _subscription_management(current)

    st.markdown("### Stripe test card")

    st.code(
        "Card number: 4242 4242 4242 4242\n"
        "Expiration: any future date\n"
        "CVC: any 3 digits\n"
        "ZIP: any valid ZIP code",
        language="text",
    )
