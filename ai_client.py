import os

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from database import get_profile

load_dotenv()


def get_setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def generate(tool_name: str, request: str) -> str:
    api_key = get_setting("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "Your Anthropic API key was not found.\n\n"
            "Make sure your .env file contains:\n"
            "ANTHROPIC_API_KEY=your_real_key\n"
            "CLAUDE_MODEL=claude-sonnet-4-5"
        )

    profile = get_profile(st.session_state.user["id"])
    model = get_setting("CLAUDE_MODEL", "claude-sonnet-4-5")

    system = f"""
You are the strategy engine inside Fitzery Marketing.
Never call yourself AI. Refer to your answer as the plan, recommendation, or today's advice.
Be specific, honest, and practical. Do not invent business results.

Business profile:
Business name: {profile.get('business_name', '')}
Industry: {profile.get('industry', '')}
Location: {profile.get('location', '')}
Services: {profile.get('services', '')}
Ideal customer: {profile.get('ideal_customer', '')}
Brand voice: {profile.get('brand_voice', '')}
Monthly revenue: ${profile.get('monthly_revenue', 0):,.0f}
Monthly goal: ${profile.get('monthly_goal', 0):,.0f}
Marketing budget: ${profile.get('marketing_budget', 0):,.0f}
Employees: {profile.get('employees', 1)}

Current tool: {tool_name}
"""

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1800,
            temperature=0.7,
            system=system,
            messages=[{"role": "user", "content": request}],
        )
        return "\n".join(
            block.text for block in response.content
            if getattr(block, "type", "") == "text"
        ).strip()
    except Exception as exc:
        return (
            "Fitzery Marketing could not generate the result.\n\n"
            f"Error: {exc}\n\n"
            "Check your API key, model name, internet connection, and Anthropic balance."
        )
