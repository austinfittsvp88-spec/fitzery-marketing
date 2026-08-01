from datetime import date, datetime

import pandas as pd
import streamlit as st

from ai_client import generate
from database import (
    add_lead,
    delete_lead,
    get_leads,
    get_profile,
    get_saved_outputs,
    save_output,
    update_lead,
    update_profile,
)
from pdf_export import build_pdf


STATUSES = ["New", "Contacted", "Qualified", "Proposal Sent", "Closed Won", "Closed Lost"]
PRIORITIES = ["Low", "Medium", "High"]


def user_id():
    return st.session_state.user["id"]


def render_result(tool_name: str, key: str, content: str):
    if not content:
        return

    st.markdown("### Your result")
    st.markdown(f'<div class="output-box">{content}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save result", key=f"save_{key}", use_container_width=True):
            save_output(user_id(), tool_name, content)
            st.success("Saved to Reports.")
    with c2:
        st.download_button(
            "Download text",
            data=content,
            file_name=f"{key}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key=f"text_{key}",
            use_container_width=True,
        )


def business_numbers():
    profile = get_profile(user_id())
    leads = get_leads(user_id())
    saved = get_saved_outputs(user_id())

    revenue = float(profile.get("monthly_revenue", 0) or 0)
    goal = float(profile.get("monthly_goal", 0) or 0)
    budget = float(profile.get("marketing_budget", 0) or 0)

    active = [x for x in leads if x["status"] not in ("Closed Won", "Closed Lost")]
    won = [x for x in leads if x["status"] == "Closed Won"]
    lost = [x for x in leads if x["status"] == "Closed Lost"]
    high_priority = [x for x in active if (x.get("priority") or "Medium") == "High"]

    pipeline = sum(float(x.get("value") or 0) for x in active)
    won_value = sum(float(x.get("value") or 0) for x in won)

    today_text = date.today().isoformat()
    overdue = []
    due_today = []

    for lead in active:
        follow_up = lead.get("follow_up_date") or ""
        if follow_up:
            if follow_up < today_text:
                overdue.append(lead)
            elif follow_up == today_text:
                due_today.append(lead)

    total_closed = len(won) + len(lost)
    conversion_rate = (len(won) / total_closed * 100) if total_closed else 0
    goal_progress = (revenue / goal * 100) if goal > 0 else 0

    return {
        "profile": profile,
        "leads": leads,
        "saved": saved,
        "revenue": revenue,
        "goal": goal,
        "budget": budget,
        "active": active,
        "won": won,
        "lost": lost,
        "high_priority": high_priority,
        "pipeline": pipeline,
        "won_value": won_value,
        "overdue": overdue,
        "due_today": due_today,
        "conversion_rate": conversion_rate,
        "goal_progress": goal_progress,
    }


def choose_top_lead(data):
    candidates = data["overdue"] or data["due_today"] or data["high_priority"] or data["active"]
    if not candidates:
        return None

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}

    return sorted(
        candidates,
        key=lambda lead: (
            priority_rank.get(lead.get("priority") or "Medium", 1),
            lead.get("follow_up_date") or "9999-12-31",
            -float(lead.get("value") or 0),
        ),
    )[0]


def render_dashboard():
    data = business_numbers()
    profile = data["profile"]

    progress = int(data["goal_progress"]) if data["goal"] > 0 else 0
    hot_leads = len(data["high_priority"])

    marketing_score = min(
        100,
        30
        + min(len(data["saved"]) * 3, 20)
        + min(len(data["active"]) * 4, 25)
        + min(len(data["won"]) * 5, 15)
        + (10 if data["budget"] > 0 else 0),
    )

    st.markdown(
        f"""
        <div class="hero">
            <h1>Welcome back, {profile.get('business_name', 'Business Owner')}</h1>
            <p>Your growth numbers, leads, priorities, and reports are all in one place.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    cards = [
        ("Revenue This Month", f"${data['revenue']:,.0f}", f"{progress}% of goal"),
        ("Active Leads", str(len(data["active"])), f"{hot_leads} high priority"),
        ("Lead Pipeline", f"${data['pipeline']:,.0f}", "Open potential value"),
        ("Closed-Won Value", f"${data['won_value']:,.0f}", f"{len(data['won'])} won deals"),
    ]

    for col, (label, value, note) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### Revenue Goal")
    st.progress(min(progress, 100) / 100 if data["goal"] > 0 else 0)
    st.caption(f"${data['revenue']:,.0f} earned toward a ${data['goal']:,.0f} monthly goal")

    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("### Today's Priority")
        top_lead = choose_top_lead(data)

        if data["overdue"]:
            lead = top_lead
            st.warning(
                f"Follow up with **{lead['name']}** today. "
                f"This lead is overdue and worth **${float(lead.get('value') or 0):,.0f}**."
            )
        elif data["due_today"]:
            lead = top_lead
            st.warning(
                f"Your follow-up with **{lead['name']}** is due today. "
                f"Potential value: **${float(lead.get('value') or 0):,.0f}**."
            )
        elif data["high_priority"]:
            lead = top_lead
            st.info(f"Your highest-priority open lead is **{lead['name']}**.")
        elif data["active"]:
            st.info(f"You have **{len(data['active'])} open leads**. Contact the oldest lead first.")
        else:
            st.info("Add your first lead in the CRM, then start your follow-up plan.")

        if st.button("Open CEO Advisor", type="primary", use_container_width=True):
            st.session_state.open_ceo_hint = True
            st.info("Click **CEO Advisor** in the left menu to build your full daily mission.")

    with right:
        st.markdown("### Business Snapshot")
        st.info(
            f"""
**Industry:** {profile.get('industry', '')}

**Location:** {profile.get('location', '')}

**Employees:** {profile.get('employees', 1)}

**Marketing score:** {marketing_score}/100

**Saved reports:** {len(data['saved'])}
"""
        )

    st.markdown("### Six-Month Projection")
    start = max(data["revenue"], data["goal"] * 0.55 if data["goal"] else 1000)
    end = max(data["goal"], start)
    values = [round(start + ((end - start) / 5) * i) for i in range(6)]
    chart = pd.DataFrame(
        {"Projected Revenue": values},
        index=["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"],
    )
    st.line_chart(chart, height=280)

    st.markdown("### Marketing Score Breakdown")
    score_items = {
        "Business profile": 15 if profile.get("services") and profile.get("ideal_customer") else 7,
        "Lead pipeline": min(25, len(data["active"]) * 5),
        "Follow-up discipline": 20 if not data["overdue"] else max(0, 20 - len(data["overdue"]) * 5),
        "Saved campaigns": min(20, len(data["saved"]) * 4),
        "Marketing investment": 20 if data["budget"] > 0 else 0,
    }
    for item, points in score_items.items():
        st.write(f"**{item}:** {points} points")
        st.progress(points / 25 if item == "Lead pipeline" else min(points / 20, 1.0))

    st.markdown("### Daily Return Checklist")
    checks = st.columns(4)
    labels = ["Review today's mission", "Complete lead follow-ups", "Create one growth asset", "Update CRM notes"]
    for col, label in zip(checks, labels):
        with col:
            st.checkbox(label, key=f"dashboard_check_{label}")


def render_ceo_advisor():
    data = business_numbers()
    profile = data["profile"]
    top_lead = choose_top_lead(data)

    st.markdown(
        f"""
        <div class="hero">
            <h1>CEO Advisor</h1>
            <p>Your daily mission is built from {profile.get('business_name', 'your business')} data.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Leads", len(data["active"]))
    c2.metric("Pipeline", f"${data['pipeline']:,.0f}")
    c3.metric("Overdue Follow-ups", len(data["overdue"]))
    c4.metric("Goal Progress", f"{data['goal_progress']:.0f}%")

    st.markdown("### Today's Mission")

    if data["overdue"]:
        mission = (
            f"Contact {top_lead['name']} before doing new marketing. "
            f"The follow-up is overdue and the opportunity is worth "
            f"${float(top_lead.get('value') or 0):,.0f}."
        )
        impact = "Highest immediate revenue impact"
    elif data["due_today"]:
        mission = (
            f"Complete today's follow-up with {top_lead['name']}. "
            f"Move the lead to the correct pipeline stage after the conversation."
        )
        impact = "Protects an active sales opportunity"
    elif data["high_priority"]:
        mission = (
            f"Contact high-priority lead {top_lead['name']} and ask for the next commitment: "
            f"appointment, quote approval, deposit, or closing decision."
        )
        impact = "Moves the strongest lead forward"
    elif data["active"]:
        mission = (
            f"Contact {top_lead['name']} and update the lead's status, notes, "
            f"last-contacted date, and next follow-up date."
        )
        impact = "Improves follow-up discipline"
    else:
        mission = (
            "Create your first lead in the CRM, then contact three potential customers "
            "and record every response."
        )
        impact = "Starts the sales pipeline"

    st.success(f"**Mission:** {mission}\n\n**Why it matters:** {impact}")

    st.markdown("### Advisor Warnings")
    warnings = []

    if data["overdue"]:
        warnings.append(f"{len(data['overdue'])} follow-up(s) are overdue.")
    if data["goal"] > 0 and data["goal_progress"] < 25:
        warnings.append("Revenue is below 25% of the monthly goal.")
    if not data["active"]:
        warnings.append("There are no active leads in the CRM.")
    if data["active"] and not data["high_priority"]:
        warnings.append("No open leads are marked high priority.")
    if data["budget"] <= 0:
        warnings.append("No monthly marketing budget is recorded.")
    if data["active"] and data["pipeline"] <= 0:
        warnings.append("Open leads do not have potential values entered.")

    if warnings:
        for warning in warnings:
            st.warning(warning)
    else:
        st.success("No major operating warnings were found today.")

    st.markdown("### Build My Full Daily Plan")

    focus = st.selectbox(
        "Main focus",
        [
            "Increase revenue",
            "Get more leads",
            "Close existing leads",
            "Improve marketing",
            "Improve customer retention",
            "Organize the business",
        ],
    )

    time_available = st.selectbox(
        "Time available today",
        ["30 minutes", "1 hour", "2 hours", "Half day", "Full day"],
        index=2,
    )

    urgency = st.selectbox(
        "Work style",
        ["Focused and realistic", "Aggressive growth", "Simple beginner plan"],
    )

    if st.button("Generate today's CEO plan", type="primary", use_container_width=True):
        lead_summary = "\n".join(
            [
                (
                    f"- {lead['name']} | status: {lead['status']} | "
                    f"priority: {lead.get('priority') or 'Medium'} | "
                    f"value: ${float(lead.get('value') or 0):,.0f} | "
                    f"follow-up: {lead.get('follow_up_date') or 'not set'}"
                )
                for lead in data["active"][:15]
            ]
        ) or "- No active leads"

        request = f"""
Create today's CEO operating plan.

Main focus: {focus}
Time available: {time_available}
Work style: {urgency}

Current business numbers:
- Revenue this month: ${data['revenue']:,.0f}
- Monthly revenue goal: ${data['goal']:,.0f}
- Goal progress: {data['goal_progress']:.1f}%
- Marketing budget: ${data['budget']:,.0f}
- Active leads: {len(data['active'])}
- High-priority leads: {len(data['high_priority'])}
- Overdue follow-ups: {len(data['overdue'])}
- Due today: {len(data['due_today'])}
- Open pipeline: ${data['pipeline']:,.0f}
- Won deals: {len(data['won'])}
- Conversion rate: {data['conversion_rate']:.1f}%

Open leads:
{lead_summary}

Create:
1. One clear mission for today
2. The exact first action
3. Three prioritized tasks with estimated time
4. Which lead to contact first and why
5. One revenue action
6. One marketing action
7. One customer-retention action
8. One task to avoid today
9. A measurable end-of-day scorecard
10. A short motivational closing

Keep the plan practical. Do not invent facts or results.
"""
        with st.spinner("Building your CEO plan..."):
            st.session_state.ceo_plan = generate("CEO Advisor", request)

    render_result("CEO Advisor", "ceo_daily_plan", st.session_state.get("ceo_plan", ""))

    st.markdown("### Ask Your Business Advisor")
    advisor_question = st.text_area("What business decision are you working through?", key="advisor_question")
    if st.button("Get advisor recommendation", use_container_width=True):
        with st.spinner("Reviewing your business numbers..."):
            st.session_state.advisor_chat = generate("Business Advisor", f"Answer this owner question using the saved business profile and current numbers. Give a direct recommendation, reasons, risks, and the next 3 actions. Question: {advisor_question}")
    render_result("Business Advisor", "advisor_answer", st.session_state.get("advisor_chat", ""))


def render_marketing():
    st.title("Marketing Strategy")
    st.caption("Create a complete campaign around your goals and budget.")

    offer = st.text_input("What are you promoting?")
    campaign_goal = st.selectbox("Primary campaign goal", ["Generate leads", "Book appointments", "Increase sales", "Build local awareness", "Win back past customers"])
    timeframe = st.selectbox("Timeframe", ["7 days", "30 days", "90 days"])
    channels = st.multiselect(
        "Channels",
        ["Facebook", "Instagram", "Google Search", "Email", "TikTok", "Direct Mail", "Partnerships"],
        default=["Facebook", "Google Search"],
    )

    if st.button("Create marketing plan", type="primary", use_container_width=True):
        request = f"""
Create a {timeframe} marketing plan for {offer or 'the business and its main services'}.
Campaign goal: {campaign_goal}.
Preferred channels: {', '.join(channels) if channels else 'choose the strongest channels'}.

Include:
- Campaign objective
- Ideal customer
- Offer and positioning
- Channel-by-channel strategy
- Budget allocation
- Weekly action plan
- Key numbers to track
- Three mistakes to avoid
- Exact execution checklist for day 1
- A simple test using one real offer before scaling
- What to change after the first 7 days based on results
"""
        with st.spinner("Building your strategy..."):
            st.session_state.marketing_result = generate("Marketing Strategy", request)

    render_result("Marketing Strategy", "marketing_plan", st.session_state.get("marketing_result", ""))

    st.markdown("### Campaign Execution")
    e1, e2, e3 = st.columns(3)
    e1.checkbox("Offer approved", key="mk_offer")
    e2.checkbox("Tracking method ready", key="mk_tracking")
    e3.checkbox("First campaign launched", key="mk_launch")


def render_social():
    st.title("Social Media")
    platform = st.selectbox("Platform", ["Facebook", "Instagram", "TikTok", "LinkedIn", "X"])
    goal = st.selectbox("Goal", ["Get leads", "Build trust", "Promote an offer", "Educate customers", "Increase engagement"])
    topic = st.text_input("Topic or offer")
    amount = st.slider("Number of posts", 1, 10, 5)
    content_style = st.selectbox("Content style", ["Helpful and trustworthy", "Bold and attention-grabbing", "Local and community-focused", "Professional and educational"])
    include_video = st.checkbox("Include a short-video script", value=True)

    if st.button("Generate posts", type="primary", use_container_width=True):
        request = f"""
Write {amount} ready-to-post {platform} posts about {topic or 'the business and its services'}.
The goal is to {goal.lower()}.
Style: {content_style}.
For each include an opening hook, full post, call to action, visual idea, and suitable hashtags.
Include a short-video script: {include_video}.
Do not invent results or fake customer claims.
"""
        with st.spinner("Writing posts..."):
            st.session_state.social_result = generate("Social Media", request)

    render_result("Social Media", "social_posts", st.session_state.get("social_result", ""))

    with st.expander("Managed Advertising — $199/month add-on"):
        st.markdown("Fitzery can prepare and manage the customer's ad campaign while the customer's ad spend remains separate. Before public launch, this feature will require connected ad accounts, customer approval, spending limits, and reporting.")
        st.checkbox("Customer approved the campaign", key="ads_approved")
        st.number_input("Planned monthly ad spend", min_value=0.0, step=50.0, key="ads_budget")
        st.text_area("Campaign notes", key="ads_notes")


def render_email():
    st.title("Email Campaigns")
    email_type = st.selectbox(
        "Email type",
        ["Cold outreach", "Follow-up", "Promotion", "Customer win-back", "Appointment reminder", "Thank-you"],
    )
    audience = st.text_input("Audience")
    message = st.text_area("Main message or offer")
    tone = st.selectbox("Tone", ["Professional and friendly", "Direct and confident", "Warm and conversational", "Premium and polished"])
    sequence_length = st.selectbox("Campaign length", ["Single email", "3-email sequence", "5-email sequence"])

    if st.button("Write email", type="primary", use_container_width=True):
        request = f"""
Write a {email_type.lower()} email for {audience or 'a prospective customer'}.
Main message: {message or 'introduce the business and encourage the next step'}.
Tone: {tone}. Campaign length: {sequence_length}.
Use personalization placeholders such as [First Name] and [Company] where useful.
Include three subject lines, preview text, body copy, and one clear call to action.
Make it persuasive without sounding spammy.
"""
        with st.spinner("Writing email..."):
            st.session_state.email_result = generate("Email Campaigns", request)

    render_result("Email Campaigns", "email_campaign", st.session_state.get("email_result", ""))

    st.info("Best practice: personalize every message, make the next step easy, and stop outreach when someone opts out.")


def render_sales():
    st.title("Sales Assistant")
    situation = st.selectbox(
        "Sales situation",
        ["Cold call", "Inbound lead", "Quote follow-up", "In-person pitch", "Direct message", "Closing conversation"],
    )
    service = st.text_input("Product or service")
    objection = st.text_input("Expected objection")
    sales_style = st.selectbox("Sales style", ["Consultative", "Straightforward", "Friendly expert", "High-energy closer"])
    include_followups = st.checkbox("Include email, text, and voicemail follow-ups", value=True)

    if st.button("Build sales script", type="primary", use_container_width=True):
        request = f"""
Create a practical {situation.lower()} script for selling {service or 'the business service'}.
Expected objection: {objection or 'the customer wants to think about it'}.
Sales style: {sales_style}. Include follow-up email, text, and voicemail: {include_followups}.
Include opening, discovery questions, value explanation, objection handling, closing question, and follow-up text.
Make it ethical and natural to say out loud.
"""
        with st.spinner("Building script..."):
            st.session_state.sales_result = generate("Sales Assistant", request)

    render_result("Sales Assistant", "sales_script", st.session_state.get("sales_result", ""))

    with st.expander("Objection Practice"):
        practice = st.selectbox("Practice objection", ["Your price is too high", "I need to think about it", "I already use someone else", "Send me information", "I am not interested"])
        st.caption(f"Practice answering: {practice}. Keep your answer short, ask one question, and guide the customer toward a clear next step.")


def render_reviews():
    st.title("Review Manager")
    platform = st.selectbox("Review platform", ["Google", "Facebook", "Yelp", "BBB", "Other"])
    review = st.text_area("Paste the customer review", height=170)
    tone = st.selectbox("Tone", ["Warm and professional", "Brief and direct", "Apologetic and solution-focused"])

    if st.button("Write response", type="primary", use_container_width=True):
        request = f"""
Write a {tone.lower()} public response for {platform} to this review:

{review or 'The customer left a general review without much detail.'}

Provide both a public response and a private follow-up message. Do not argue, share private information, or admit legal liability. Move sensitive details offline when appropriate.
"""
        with st.spinner("Writing response..."):
            st.session_state.review_result = generate("Review Manager", request)

    render_result("Review Manager", "review_response", st.session_state.get("review_result", ""))


def render_seo():
    st.title("SEO")
    service = st.text_input("Service")
    location = st.text_input("Target city or area")
    target_keyword = st.text_input("Primary keyword (optional)")
    content_type = st.selectbox(
        "Content type",
        ["Service page", "Homepage section", "Blog outline", "Google Business Profile post", "Meta titles and descriptions"],
    )

    if st.button("Generate SEO content", type="primary", use_container_width=True):
        request = f"""
Create {content_type.lower()} content for {service or 'the main business service'} in {location or 'the business location'}.
Requested primary keyword: {target_keyword or 'choose the strongest natural keyword'}.
Include natural local keywords, search intent, primary keyword, secondary keywords, title, headings,
finished copy or detailed outline, meta title, meta description, and call to action where appropriate.
Do not promise rankings.
"""
        with st.spinner("Building SEO content..."):
            st.session_state.seo_result = generate("SEO", request)

    render_result("SEO", "seo_content", st.session_state.get("seo_result", ""))

    st.markdown("### Local SEO Readiness")
    seo_checks = ["Google Business Profile completed", "Name/address/phone consistent", "Service pages published", "Recent customer reviews", "Mobile-friendly website"]
    completed = sum(st.checkbox(item, key=f"seo_{i}") for i, item in enumerate(seo_checks))
    st.progress(completed / len(seo_checks))
    st.caption(f"{completed} of {len(seo_checks)} local SEO foundations completed")


def render_crm():
    st.title("CRM")
    st.caption("Track leads, follow-ups, priority, and potential revenue.")

    with st.expander("➕ Add a new lead", expanded=False):
        with st.form("lead_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Lead name")
                email = st.text_input("Email")
                company = st.text_input("Company")
                status = st.selectbox("Status", STATUSES)
                priority = st.selectbox("Priority", PRIORITIES, index=1)
            with c2:
                phone = st.text_input("Phone")
                value = st.number_input("Potential value", min_value=0.0, step=100.0)
                follow_up = st.date_input("Follow-up date", value=date.today())
                last_contacted = st.date_input("Last contacted", value=date.today())
                notes = st.text_area("Notes")

            submitted = st.form_submit_button("Add lead", type="primary", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Lead name is required.")
            else:
                add_lead(
                    user_id(),
                    name.strip(),
                    email.strip(),
                    phone.strip(),
                    company.strip(),
                    status,
                    priority,
                    follow_up.isoformat(),
                    last_contacted.isoformat(),
                    value,
                    notes.strip(),
                )
                st.success("Lead added.")
                st.rerun()

    leads = get_leads(user_id())
    if not leads:
        st.info("No leads yet.")
        return

    st.markdown("### Lead pipeline")
    top1, top2, top3 = st.columns(3)
    with top1:
        search = st.text_input("Search leads", placeholder="Name, company, email, or phone")
    with top2:
        status_filter = st.selectbox("Filter by status", ["All"] + STATUSES)
    with top3:
        priority_filter = st.selectbox("Filter by priority", ["All"] + PRIORITIES)

    filtered = []
    query = search.lower().strip()
    for lead in leads:
        searchable = " ".join(
            [
                str(lead.get("name", "")),
                str(lead.get("company", "")),
                str(lead.get("email", "")),
                str(lead.get("phone", "")),
            ]
        ).lower()
        if query and query not in searchable:
            continue
        if status_filter != "All" and lead["status"] != status_filter:
            continue
        if priority_filter != "All" and lead.get("priority", "Medium") != priority_filter:
            continue
        filtered.append(lead)

    if not filtered:
        st.warning("No leads match those filters.")
        return

    pipeline_value = sum(float(x.get("value") or 0) for x in filtered if x["status"] != "Closed Lost")
    c1, c2, c3 = st.columns(3)
    c1.metric("Visible leads", len(filtered))
    c2.metric("Visible pipeline", f"${pipeline_value:,.0f}")
    c3.metric("High priority", len([x for x in filtered if x.get("priority") == "High"]))

    for lead in filtered:
        value = float(lead.get("value") or 0)
        follow_up_text = lead.get("follow_up_date") or "Not set"
        company_text = lead.get("company") or "No company"
        priority_text = lead.get("priority") or "Medium"

        st.markdown(
            f"""
            <div class="lead-card">
                <div class="lead-name">{lead['name']}</div>
                <div style="margin:8px 0 10px 0;">
                    <span class="badge">{lead['status']}</span>
                    <span class="badge">{priority_text} priority</span>
                </div>
                <div class="lead-meta">
                    <strong>Company:</strong> {company_text}<br>
                    <strong>Potential value:</strong> ${value:,.0f}<br>
                    <strong>Follow-up:</strong> {follow_up_text}<br>
                    <strong>Email:</strong> {lead.get('email') or 'Not provided'}<br>
                    <strong>Phone:</strong> {lead.get('phone') or 'Not provided'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"Edit {lead['name']}"):
            with st.form(f"edit_lead_{lead['id']}"):
                e1, e2 = st.columns(2)
                with e1:
                    edit_name = st.text_input("Lead name", value=lead["name"], key=f"name_{lead['id']}")
                    edit_email = st.text_input("Email", value=lead.get("email", ""), key=f"email_{lead['id']}")
                    edit_company = st.text_input("Company", value=lead.get("company", ""), key=f"company_{lead['id']}")
                    edit_status = st.selectbox(
                        "Status",
                        STATUSES,
                        index=STATUSES.index(lead["status"]) if lead["status"] in STATUSES else 0,
                        key=f"status_{lead['id']}",
                    )
                    current_priority = lead.get("priority") or "Medium"
                    edit_priority = st.selectbox(
                        "Priority",
                        PRIORITIES,
                        index=PRIORITIES.index(current_priority) if current_priority in PRIORITIES else 1,
                        key=f"priority_{lead['id']}",
                    )
                with e2:
                    edit_phone = st.text_input("Phone", value=lead.get("phone", ""), key=f"phone_{lead['id']}")
                    edit_value = st.number_input(
                        "Potential value",
                        min_value=0.0,
                        step=100.0,
                        value=float(lead.get("value") or 0),
                        key=f"value_{lead['id']}",
                    )
                    try:
                        follow_default = date.fromisoformat(lead.get("follow_up_date") or date.today().isoformat())
                    except ValueError:
                        follow_default = date.today()
                    try:
                        contacted_default = date.fromisoformat(lead.get("last_contacted") or date.today().isoformat())
                    except ValueError:
                        contacted_default = date.today()

                    edit_follow_up = st.date_input("Follow-up date", value=follow_default, key=f"follow_{lead['id']}")
                    edit_last_contacted = st.date_input(
                        "Last contacted",
                        value=contacted_default,
                        key=f"contacted_{lead['id']}",
                    )
                    edit_notes = st.text_area("Notes", value=lead.get("notes", ""), key=f"notes_{lead['id']}")

                save_edit = st.form_submit_button("Save changes", type="primary", use_container_width=True)

            if save_edit:
                if not edit_name.strip():
                    st.error("Lead name is required.")
                else:
                    update_lead(
                        user_id(),
                        lead["id"],
                        edit_name.strip(),
                        edit_email.strip(),
                        edit_phone.strip(),
                        edit_company.strip(),
                        edit_status,
                        edit_priority,
                        edit_follow_up.isoformat(),
                        edit_last_contacted.isoformat(),
                        edit_value,
                        edit_notes.strip(),
                    )
                    st.success("Lead updated.")
                    st.rerun()

            if st.button("Delete lead", key=f"delete_lead_{lead['id']}", use_container_width=True):
                delete_lead(user_id(), lead["id"])
                st.rerun()


def render_reports():
    st.title("Reports")
    st.caption("View saved work and export professional PDFs.")

    profile = get_profile(user_id())
    outputs = get_saved_outputs(user_id())

    if not outputs:
        st.info("Save a result from any tool and it will appear here.")
        return

    tool_names = sorted({item["tool_name"] for item in outputs})
    report_filter = st.selectbox("Filter saved work", ["All"] + tool_names)
    search_reports = st.text_input("Search saved work")
    visible_outputs = [item for item in outputs if (report_filter == "All" or item["tool_name"] == report_filter) and (not search_reports.strip() or search_reports.lower() in item["content"].lower())]

    selected_ids = []
    for item in visible_outputs:
        checked = st.checkbox(
            f"{item['tool_name']} • {item['created_at']}",
            key=f"report_{item['id']}",
        )
        if checked:
            selected_ids.append(item["id"])

        with st.expander(f"Preview: {item['tool_name']}"):
            st.markdown(item["content"])

    selected = [x for x in outputs if x["id"] in selected_ids]

    if selected:
        pdf = build_pdf(
            "Business Growth Report",
            profile.get("business_name", "Business"),
            [(item["tool_name"], item["content"]) for item in selected],
        )
        st.download_button(
            "Download selected as PDF",
            data=pdf,
            file_name="fitzery_marketing_report.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )


def render_settings():
    st.title("Business Settings")
    st.caption("These details personalize every tool.")

    profile = get_profile(user_id())
    readiness_fields = [profile.get("business_name"), profile.get("industry"), profile.get("location"), profile.get("services"), profile.get("ideal_customer"), profile.get("brand_voice")]
    readiness = int(sum(bool(str(x).strip()) for x in readiness_fields) / len(readiness_fields) * 100)
    st.metric("Profile readiness", f"{readiness}%")
    st.progress(readiness / 100)
    st.caption("A complete profile makes every recommendation, campaign, report, and dashboard insight more specific.")

    with st.form("profile_form"):
        business_name = st.text_input("Business name", value=profile.get("business_name", ""))
        industry = st.text_input("Industry", value=profile.get("industry", ""))
        location = st.text_input("Primary location", value=profile.get("location", ""))
        services = st.text_area("Services", value=profile.get("services", ""))
        ideal_customer = st.text_area("Ideal customer", value=profile.get("ideal_customer", ""))
        brand_voice = st.text_input("Brand voice", value=profile.get("brand_voice", ""))

        c1, c2 = st.columns(2)
        with c1:
            monthly_revenue = st.number_input(
                "Current monthly revenue",
                min_value=0.0,
                step=500.0,
                value=float(profile.get("monthly_revenue", 0) or 0),
            )
            marketing_budget = st.number_input(
                "Monthly marketing budget",
                min_value=0.0,
                step=100.0,
                value=float(profile.get("marketing_budget", 0) or 0),
            )
        with c2:
            monthly_goal = st.number_input(
                "Monthly revenue goal",
                min_value=0.0,
                step=500.0,
                value=float(profile.get("monthly_goal", 0) or 0),
            )
            employees = st.number_input(
                "Number of employees",
                min_value=1,
                step=1,
                value=int(profile.get("employees", 1) or 1),
            )

        submitted = st.form_submit_button("Save settings", type="primary", use_container_width=True)

    if submitted:
        update_profile(
            user_id(),
            {
                "business_name": business_name,
                "industry": industry,
                "location": location,
                "services": services,
                "ideal_customer": ideal_customer,
                "brand_voice": brand_voice,
                "monthly_revenue": monthly_revenue,
                "monthly_goal": monthly_goal,
                "marketing_budget": marketing_budget,
                "employees": employees,
            },
        )
        st.success("Business settings saved.")
