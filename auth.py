import hashlib
import hmac
import os

import streamlit as st

from database import create_user, get_user_by_email


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            bytes.fromhex(salt_hex),
            120_000,
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def auth_screen():
    st.markdown(
        """
        <div class="hero">
            <h1>Fitzery Marketing</h1>
            <p>Grow your business with one organized platform.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, middle, right = st.columns([1, 1.3, 1])
    with middle:
        tab_login, tab_signup = st.tabs(["Sign in", "Create account"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

            if submitted:
                user = get_user_by_email(email)
                if user and verify_password(password, user["password_hash"]):
                    st.session_state.user = {"id": user["id"], "email": user["email"]}
                    st.rerun()
                else:
                    st.error("Incorrect email or password.")

        with tab_signup:
            with st.form("signup_form"):
                email = st.text_input("Email", key="signup_email")
                password = st.text_input("Password", type="password", key="signup_password")
                confirm = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)

            if submitted:
                if "@" not in email or "." not in email:
                    st.error("Enter a valid email address.")
                elif len(password) < 8:
                    st.error("Use at least 8 characters for your password.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    ok, message = create_user(email, hash_password(password))
                    if ok:
                        st.success("Account created. You can sign in now.")
                    else:
                        st.error(message)


def logout_button():
    if st.button("Log out", use_container_width=True):
        st.session_state.user = None
        st.rerun()
