import os
from typing import Optional

import stripe
import streamlit as st

from database import update_user_plan


PLAN_PRICE_ENV = {
    "Starter": "STRIPE_STARTER_PRICE_ID",
    "Growth": "STRIPE_GROWTH_PRICE_ID",
    "Pro": "STRIPE_PRO_PRICE_ID",
}


def _configure_stripe() -> None:
    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()

    if not secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is missing from the .env file.")

    if not secret_key.startswith("sk_test_"):
        raise RuntimeError(
            "Fitzery is currently configured for Stripe sandbox testing. "
            "Use a Stripe secret key beginning with sk_test_."
        )

    stripe.api_key = secret_key


def get_price_id(plan_name: str) -> str:
    env_name = PLAN_PRICE_ENV.get(plan_name)

    if not env_name:
        raise ValueError("Invalid Fitzery plan.")

    price_id = os.getenv(env_name, "").strip()

    if not price_id:
        raise RuntimeError(f"{env_name} is missing from the .env file.")

    if not price_id.startswith("price_"):
        raise RuntimeError(f"{env_name} must begin with price_.")

    return price_id


def create_checkout_url(
    user_id: int,
    email: str,
    plan_name: str,
    base_url: str = "https://fitzery-marketing.streamlit.app",
) -> str:
    _configure_stripe()
    price_id = get_price_id(plan_name)

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        customer_email=email,
        client_reference_id=str(user_id),
        metadata={
            "fitzery_user_id": str(user_id),
            "fitzery_plan": plan_name,
        },
        subscription_data={
            "metadata": {
                "fitzery_user_id": str(user_id),
                "fitzery_plan": plan_name,
            }
        },
        success_url=(
            f"{base_url}/?checkout=success"
            "&session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=f"{base_url}/?checkout=cancelled",
    )

    if not session.url:
        raise RuntimeError("Stripe did not return a Checkout URL.")

    return session.url


def create_billing_portal_url(
    stripe_customer_id: str,
    return_url: str = "https://fitzery-marketing.streamlit.app",
) -> str:
    _configure_stripe()

    if not stripe_customer_id:
        raise RuntimeError(
            "No Stripe customer is connected to this Fitzery account yet."
        )

    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )

    if not session.url:
        raise RuntimeError("Stripe did not return a billing portal URL.")

    return session.url


def _query_value(name: str) -> Optional[str]:
    try:
        value = st.query_params.get(name)
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get(name)

    if isinstance(value, list):
        return value[0] if value else None

    return value


def clear_checkout_query() -> None:
    try:
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()


def process_checkout_return(user_id: int) -> Optional[dict]:
    checkout_status = _query_value("checkout")

    if checkout_status == "cancelled":
        clear_checkout_query()
        return {
            "status": "cancelled",
            "message": "Checkout was cancelled. No payment was made.",
        }

    if checkout_status != "success":
        return None

    session_id = _query_value("session_id")

    if not session_id:
        clear_checkout_query()
        return {
            "status": "error",
            "message": "Stripe returned without a Checkout Session ID.",
        }

    try:
        _configure_stripe()
        session = stripe.checkout.Session.retrieve(session_id)

        metadata = session.metadata or {}
        checkout_user_id = metadata["fitzery_user_id"]
        plan_name = metadata["fitzery_plan"]

        if str(checkout_user_id) != str(user_id):
            raise RuntimeError(
                "This Stripe Checkout Session does not belong to the signed-in user."
            )

        if plan_name not in PLAN_PRICE_ENV:
            raise RuntimeError("Stripe returned an invalid Fitzery plan.")

        if session.mode != "subscription":
            raise RuntimeError("The Stripe Checkout Session was not a subscription.")

        subscription_id = str(session.subscription or "")
        customer_id = str(session.customer or "")
        payment_status = session.payment_status
        session_status = session.status

        if session_status != "complete":
            raise RuntimeError("Stripe Checkout has not completed.")

        if not subscription_id:
            raise RuntimeError("Stripe did not create a subscription.")

        if not customer_id:
            raise RuntimeError("Stripe did not return a customer ID.")

        update_user_plan(
            user_id=user_id,
            plan=plan_name,
            status="active",
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
        )

        clear_checkout_query()

        return {
            "status": "success",
            "message": (
                f"Test subscription successful. Your Fitzery plan is now {plan_name}."
            ),
            "plan": plan_name,
            "payment_status": payment_status,
            "subscription_id": subscription_id,
            "customer_id": customer_id,
        }

    except KeyError:
        clear_checkout_query()
        return {
            "status": "error",
            "message": (
                "Stripe verification failed because the Checkout Session metadata "
                "was incomplete. Start a fresh checkout from Pricing Plans."
            ),
        }

    except Exception as exc:
        clear_checkout_query()
        return {
            "status": "error",
            "message": f"Stripe verification failed: {exc}",
        }
