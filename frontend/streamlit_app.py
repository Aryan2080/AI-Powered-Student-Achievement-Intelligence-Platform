"""
frontend/streamlit_app.py
=========================
Streamlit Multi-Persona Dashboard (Student & Faculty).
Calls FastAPI REST endpoints only; never accesses database directly.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import os
from datetime import datetime
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="AI Student Achievement Intelligence",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar Persona & Navigation
st.sidebar.title("🎓 Achievement Intelligence")
persona = st.sidebar.radio("Select Portal Persona", ["Student Dashboard", "Faculty Administration"])

# Helper API Callers
def fetch_api(endpoint: str, params: dict = None):
    try:
        r = requests.get(f"{API_URL}{endpoint}", params=params, timeout=5)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        return None

def post_api(endpoint: str, json_data: dict = None):
    try:
        r = requests.post(f"{API_URL}{endpoint}", json=json_data, timeout=5)
        return r
    except Exception as e:
        return None


# ==============================================================================
# STUDENT PERSONA
# ==============================================================================
if persona == "Student Dashboard":
    student_id = st.sidebar.text_input("Active Student ID", value="STU-2026-0001")
    menu = st.sidebar.selectbox(
        "Navigation",
        ["Overview & Recommendations", "My Achievements", "Skill Profile", "Saved & Deadlines"]
    )

    if menu == "Overview & Recommendations":
        st.title("🚀 Personalized Opportunity Recommendations")
        st.caption("Multi-objective hybrid ranker evaluating semantic vector similarity, skill Jaccard overlap, and deadline urgency.")

        # Header metrics
        prof = fetch_api(f"/students/profile/{student_id}")
        col1, col2, col3, col4 = st.columns(4)
        if prof:
            col1.metric("Student Name", prof.get("full_name", "Student"))
            col2.metric("Cumulative GPA", prof.get("gpa", 8.85))
            col3.metric("Verified Achievements", prof.get("verified_achievement_count", 2))
            col4.metric("Verified Skills", len(prof.get("verified_skills", [])))

        st.divider()

        # Opportunity Type Filter
        opp_filter = st.selectbox(
            "Filter by Opportunity Type",
            ["ALL", "HACKATHON", "INTERNSHIP", "RESEARCH_GRANT", "COMPETITION", "SCHOLARSHIP", "CONFERENCE"]
        )
        type_param = None if opp_filter == "ALL" else opp_filter

        # Fetch recommendations
        with st.spinner("Computing semantic vector similarity and hybrid rank scores..."):
            recs_data = fetch_api(f"/recommendations/{student_id}", params={"top_k": 10, "opportunity_type": type_param})

        if not recs_data or not recs_data.get("recommendations"):
            st.info("No active recommendations found. Ensure backend API is running at " + API_URL)
        else:
            recs = recs_data.get("recommendations", [])
            st.success(f"Discovered {len(recs)} highly aligned opportunities (Algorithm: {recs_data.get('algorithm_version', 'v1.2.0-hybrid')})")

            for item in recs:
                opp = item.get("opportunity", {})
                scores = item.get("scores", {})
                match_pct = int(item.get("match_score", 0.0) * 100)

                with st.container():
                    c_header, c_badge = st.columns([4, 1])
                    c_header.subheader(f"#{item.get('rank')} {opp.get('title')}")
                    c_badge.markdown(f"### `{match_pct}% Match`")

                    st.markdown(f"**Host:** {opp.get('organization')} | **Type:** `{opp.get('opportunity_type')}` | **Deadline:** `{opp.get('deadline') or 'Ongoing'}`")
                    st.info(f"💡 **Why Recommended:** {item.get('explanation')}")

                    # Score Breakdown Accordion
                    with st.expander("Inspect Multi-Criteria Score Breakdown & Skill Attribution"):
                        b1, b2, b3, b4 = st.columns(4)
                        b1.metric("Semantic Sim.", f"{int(scores.get('semantic_similarity', 0)*100)}%")
                        b2.metric("Skill Match", f"{int(scores.get('skill_match_score', 0)*100)}%")
                        b3.metric("Domain Affinity", f"{int(scores.get('domain_match_score', 0)*100)}%")
                        b4.metric("Urgency", f"{int(scores.get('urgency_score', 0)*100)}%")

                        sk_col1, sk_col2 = st.columns(2)
                        sk_col1.markdown(f"**Matched Skills:** {', '.join(item.get('matched_skills', [])) or 'None'}")
                        sk_col2.markdown(f"**Missing Skills (Gaps):** {', '.join(item.get('missing_skills', [])) or 'None'}")

                    btn_c1, btn_c2 = st.columns([1, 4])
                    if btn_c1.button("Bookmark / Save", key=f"save_{opp.get('opportunity_id')}"):
                        res = post_api(f"/opportunities/{opp.get('opportunity_id')}/save")
                        if res and res.status_code == 200:
                            st.toast(f"Saved {opp.get('title')} to bookmarks!")
                    st.markdown("---")

    elif menu == "My Achievements":
        st.title("🏆 Student Achievement Portfolio")
        st.caption("Verified academic credentials and pending submissions awaiting faculty audit.")

        achievements = fetch_api(f"/achievements/student/{student_id}")
        if achievements:
            for ach in achievements:
                status_color = "🟢 Verified" if ach.get("evidence_status") == "VERIFIED" else "🟡 Pending Review"
                with st.expander(f"{status_color} — {ach.get('title')} ({ach.get('level')})"):
                    st.write(ach.get("description"))
                    st.markdown(f"**Category:** `{ach.get('category')}` | **Date:** `{ach.get('achievement_date')}`")
                    st.markdown(f"**Canonical Skills:** {', '.join(ach.get('skills', []))}")
                    if ach.get("evidence_url"):
                        st.markdown(f"[Inspect Evidence Link]({ach.get('evidence_url')})")
        else:
            st.info("No achievements recorded yet.")

        # Form to submit new achievement
        st.subheader("Submit New Achievement")
        with st.form("achievement_form"):
            new_title = st.text_input("Achievement Title", placeholder="e.g. 1st Place at SIH 2024")
            new_desc = st.text_area("Description & Technologies Used", placeholder="Describe your project, role, tools used...")
            new_level = st.selectbox("Competition Scope", ["COLLEGE", "STATE", "NATIONAL", "INTERNATIONAL"])
            new_url = st.text_input("Proof / Certificate URL", placeholder="https://certificate.org/proof")
            submitted = st.form_submit_button("Submit for Faculty Review")

            if submitted:
                payload = {
                    "title": new_title,
                    "description": new_desc,
                    "level": new_level,
                    "evidence_url": new_url,
                }
                res = post_api("/achievements", json_data=payload)
                if res and res.status_code in [200, 201]:
                    st.success("Achievement submitted successfully! Routing to faculty verification queue.")
                else:
                    st.error("Failed to submit achievement.")

    elif menu == "Skill Profile":
        st.title("📊 Verified Competency Profile")
        prof = fetch_api(f"/students/profile/{student_id}")
        if prof:
            st.subheader(f"{prof.get('full_name')} ({prof.get('department')})")
            st.markdown(f"**Cumulative GPA:** `{prof.get('gpa')}` | **Year:** `{prof.get('year_of_study')}`")
            st.markdown("### Authenticated Skills")
            st.write(", ".join(prof.get("verified_skills", [])) or "None verified yet")

            st.markdown("### Declared Skills & Interests")
            st.write(f"**Skills:** {', '.join(prof.get('declared_skills', []))}")
            st.write(f"**Interests:** {', '.join(prof.get('declared_interests', []))}")

            st.download_button(
                "📥 Download Official PDF Transcript",
                data=requests.get(f"{API_URL}/reports/transcript/{student_id}").content,
                file_name=f"Transcript_{student_id}.pdf",
                mime="application/pdf",
            )


# ==============================================================================
# FACULTY PERSONA
# ==============================================================================
else:
    st.sidebar.subheader("Department Administrator")
    f_menu = st.sidebar.selectbox(
        "Faculty Actions",
        ["Verification Queue", "Institutional Analytics", "Talent Search"]
    )

    if f_menu == "Verification Queue":
        st.title("🛡️ Achievement Verification Queue")
        st.caption("Review submitted student certificates, verify OCR evidence, and authorize official transcript inclusion.")

        queue = fetch_api("/faculty/verification-queue")
        if queue:
            for item in queue:
                ach_id = item.get("achievement_id")
                with st.expander(f"Pending: {item.get('title')} ({item.get('category')}) — Student {item.get('student_id')}"):
                    st.write(item.get("description"))
                    st.markdown(f"**Extracted Skills:** {', '.join(item.get('skills', []))}")
                    st.markdown(f"**Confidence:** `{int((item.get('classifier_confidence') or 0.9)*100)}%`")
                    if item.get("evidence_url"):
                        st.markdown(f"[Verify Evidence Document]({item.get('evidence_url')})")

                    remarks = st.text_input(f"Verification Remarks", key=f"rem_{ach_id}")
                    col_app, col_rej = st.columns(2)
                    if col_app.button("Approve Achievement", key=f"app_{ach_id}"):
                        res = post_api(f"/faculty/verify/{ach_id}", json_data={"status": "VERIFIED", "remarks": remarks})
                        if res and res.status_code == 200:
                            st.success("Achievement Approved!")
                            st.rerun()
                    if col_rej.button("Reject Submission", key=f"rej_{ach_id}"):
                        res = post_api(f"/faculty/verify/{ach_id}", json_data={"status": "REJECTED", "remarks": remarks})
                        if res and res.status_code == 200:
                            st.warning("Achievement Rejected.")
                            st.rerun()
        else:
            st.success("Verification queue is clean! All student submissions reviewed.")

    elif f_menu == "Institutional Analytics":
        st.title("📈 Departmental Achievement Analytics")
        dept = st.selectbox("Department", ["Computer Science", "Information Technology", "AI & Data Science"])
        data = fetch_api(f"/analytics/department/{dept}")

        if data:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Department Students", data.get("total_students", 0))
            c2.metric("Verified Achievements", data.get("verified_achievements", 0))
            c3.metric("Average GPA", data.get("average_gpa", 0.0))

            st.subheader("Category Distribution")
            for c in data.get("category_distribution", []):
                st.write(f"- **{c.get('category')}:** {c.get('count')} records")

            st.download_button(
                "📥 Export Department Analytics (CSV)",
                data=requests.get(f"{API_URL}/reports/department/{dept}").content,
                file_name=f"Department_{dept}.csv",
                mime="text/csv",
            )
