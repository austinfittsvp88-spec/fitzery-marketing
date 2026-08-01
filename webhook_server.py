import os
import sqlite3
from pathlib import Path

import stripe
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

app = Flask(__name__)

DB_PATH = Path(__file__).with_name("fitzery.db")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()

PRICE_TO_PLAN = {
    os.getenv("STRIPE_STARTER_PRICE_ID", "").strip(): "Starter",
    os.getenv("STRIPE_GROWTH_PRICE_ID", "").strip(): "Growth",
    os.getenv("STRIPE_PRO_PRICE_ID", "").strip(): "Pro",
}

PRICE_TO_PLAN = {
    price_id: plan
    for price_id, plan in PRICE_TO_PLAN.items()
    if price_id
}

stripe.api_key = STRIPE_SECRET_KEY


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def get_plan_from_subscription(subscription) -> str:
    try:
        price_id = subscription["items"]["data"][0]["price"]["id"]
    except (KeyError, IndexError, TypeError):
        return ""

    return PRICE_TO_PLAN.get(price_id, "")


def get_user_id_from_metadata(obj):
    metadata = obj.get("metadata") or {}
    value = metadata.get("fitzery_user_id")

    if value and str(value).isdigit():
        return int(value)

    return None


def update_subscription_record(
    *,
    customer_id: str,
    subscription_id: str,
    plan: str,
    status: str,
    user_id=None,
):
    connection = connect()
    cursor = connection.cursor()

    if user_id:
        cursor.execute(
            """
            UPDATE users
            SET plan = ?,
                plan_status = ?,
                stripe_customer_id = ?,
                stripe_subscription_id = ?
            WHERE id = ?
            """,
            (
                plan or "Starter",
                status,
                customer_id or "",
                subscription_id or "",
                user_id,
            ),
        )
    elif subscription_id:
        cursor.execute(
            """
            UPDATE users
            SET plan = ?,
                plan_status = ?,
                stripe_customer_id = CASE
                    WHEN ? != '' THEN ?
                    ELSE stripe_customer_id
                END,
                stripe_subscription_id = ?
            WHERE stripe_subscription_id = ?
               OR stripe_customer_id = ?
            """,
            (
                plan or "Starter",
                status,
                customer_id or "",
                customer_id or "",
                subscription_id,
                subscription_id,
                customer_id,
            ),
        )
    elif customer_id:
        cursor.execute(
            """
            UPDATE users
            SET plan = ?,
                plan_status = ?,
                stripe_customer_id = ?
            WHERE stripe_customer_id = ?
            """,
            (
                plan or "Starter",
                status,
                customer_id,
                customer_id,
            ),
        )

    connection.commit()
    updated = cursor.rowcount
    connection.close()
    return updated


def mark_subscription_cancelled(customer_id: str, subscription_id: str):
    connection = connect()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE users
        SET plan = 'Starter',
            plan_status = 'cancelled',
            stripe_subscription_id = ''
        WHERE stripe_subscription_id = ?
           OR stripe_customer_id = ?
        """,
        (subscription_id, customer_id),
    )

    connection.commit()
    updated = cursor.rowcount
    connection.close()
    return updated


def mark_payment_failed(customer_id: str, subscription_id: str):
    connection = connect()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE users
        SET plan_status = 'past_due'
        WHERE stripe_subscription_id = ?
           OR stripe_customer_id = ?
        """,
        (subscription_id, customer_id),
    )

    connection.commit()
    updated = cursor.rowcount
    connection.close()
    return updated


def mark_payment_active(customer_id: str, subscription_id: str):
    connection = connect()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE users
        SET plan_status = 'active'
        WHERE stripe_subscription_id = ?
           OR stripe_customer_id = ?
        """,
        (subscription_id, customer_id),
    )

    connection.commit()
    updated = cursor.rowcount
    connection.close()
    return updated


@app.get("/")
def health():
    return jsonify(
        {
            "service": "Fitzery Stripe webhook server",
            "status": "running",
        }
    )


@app.post("/stripe-webhook")
def stripe_webhook():
    if not WEBHOOK_SECRET:
        return jsonify({"error": "STRIPE_WEBHOOK_SECRET is missing"}), 500

    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            WEBHOOK_SECRET,
        )
    except ValueError:
        return jsonify({"error": "Invalid webhook payload"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid webhook signature"}), 400

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
    }:
        customer_id = str(data_object.get("customer") or "")
        subscription_id = str(data_object.get("id") or "")
        plan = get_plan_from_subscription(data_object)
        stripe_status = str(data_object.get("status") or "active")
        user_id = get_user_id_from_metadata(data_object)

        app_status = {
            "active": "active",
            "trialing": "active",
            "past_due": "past_due",
            "unpaid": "past_due",
            "incomplete": "incomplete",
            "incomplete_expired": "cancelled",
            "canceled": "cancelled",
            "paused": "paused",
        }.get(stripe_status, stripe_status)

        updated = update_subscription_record(
            customer_id=customer_id,
            subscription_id=subscription_id,
            plan=plan or "Starter",
            status=app_status,
            user_id=user_id,
        )

        print(
            f"[Webhook] {event_type}: plan={plan}, "
            f"status={app_status}, updated_users={updated}"
        )

    elif event_type == "customer.subscription.deleted":
        customer_id = str(data_object.get("customer") or "")
        subscription_id = str(data_object.get("id") or "")

        updated = mark_subscription_cancelled(
            customer_id,
            subscription_id,
        )

        print(
            f"[Webhook] subscription deleted: "
            f"updated_users={updated}"
        )

    elif event_type == "invoice.payment_failed":
        customer_id = str(data_object.get("customer") or "")
        subscription_id = str(data_object.get("subscription") or "")

        updated = mark_payment_failed(
            customer_id,
            subscription_id,
        )

        print(
            f"[Webhook] payment failed: "
            f"updated_users={updated}"
        )

    elif event_type in {
        "invoice.paid",
        "invoice.payment_succeeded",
    }:
        customer_id = str(data_object.get("customer") or "")
        subscription_id = str(data_object.get("subscription") or "")

        updated = mark_payment_active(
            customer_id,
            subscription_id,
        )

        print(
            f"[Webhook] invoice paid: "
            f"updated_users={updated}"
        )

    else:
        print(f"[Webhook] Ignored event: {event_type}")

    return jsonify({"received": True}), 200


if __name__ == "__main__":
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is missing from .env")

    if not WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is missing from .env")

    app.run(
        host="127.0.0.1",
        port=4242,
        debug=False,
    )
