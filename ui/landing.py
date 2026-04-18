# ui/landing.py
import streamlit as st


def render_landing_page():
    st.markdown("# Chumcred Academy LMS — AI Essentials (6 Weeks)")
    st.markdown(
        "## Become Confident with AI in 6 Weeks — From Zero to Real-World Results\n"
        "A practical, beginner-friendly online program that helps you use AI to work smarter, "
        "build useful workflows, create a portfolio, and launch career or business opportunities — anywhere in the world."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.success("Self-paced weekly lessons")
    c2.success("1-hour live recap every Saturday")
    c3.success("Assignments + support inside LMS")
    c4.success("Certificate + portfolio (Week 6)")

    st.markdown("---")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.button("✅ Enroll Now", use_container_width=True, key="cta_enroll")
    with col_b:
        st.button("🎁 Access Free Week 0 (Orientation)", use_container_width=True, key="cta_week0")

    st.info("To enroll or access Week 0, log in below (we can make Week 0 public later if you want).")

    st.markdown("---")

    st.markdown("## Who This Program Is For")
    st.write(
        "This program is designed for everyone — across industries and backgrounds.\n\n"
        "Students • Professionals • SMEs • Creators • Job seekers • Anyone curious about AI."
    )

    st.markdown("---")

    st.markdown("## What You’ll Be Able to Do After 6 Weeks")
    st.write(
        "- Write faster and better (emails, reports, proposals, CVs, business documents)\n"
        "- Build repeatable workflows that save time daily\n"
        "- Use AI for research, planning, and decision support\n"
        "- Turn messy notes into clear summaries, action plans, and templates\n"
        "- Build a professional AI portfolio\n"
        "- Apply for jobs, win freelance work, or improve your business with AI"
    )

    st.markdown("---")

    st.markdown("## How The Program Works")
    st.write(
        "**1) Learn weekly (self-paced):** short lessons + examples + practice.\n\n"
        "**2) Submit weekly assignments:** practical tasks that build real skill.\n\n"
        "**3) Saturday live recap (1 hour):** recap + demos + assignment briefing + Q&A.\n\n"
        "**4) Get help inside the LMS:** use Help & Support to ask questions."
    )

    st.markdown("---")

    st.markdown("## The 6-Week Roadmap (Week 0–6)")
    st.write(
        "**Week 0:** Orientation + how to succeed\n\n"
        "**Week 1:** AI foundations\n\n"
        "**Week 2:** Prompt mastery\n\n"
        "**Week 3:** Productivity + workflows\n\n"
        "**Week 4:** Business & career use cases\n\n"
        "**Week 5:** Advanced applications + capstone\n\n"
        "**Week 6:** Certification + portfolio + career launch"
    )

    st.markdown("---")

    st.markdown("## FAQs")
    with st.expander("Do I need a tech background?"):
        st.write("No. Beginner-friendly and designed for non-technical learners.")
    with st.expander("How many hours per week do I need?"):
        st.write("Recommended: 2–4 hours weekly + 1 hour Saturday recap.")
    with st.expander("Will I get a certificate?"):
        st.write("Yes. Week 6 includes certification (Gold/Silver/Bronze).")
    with st.expander("How do I get help if I’m stuck?"):
        st.write("Use Help & Support inside the LMS.")