import streamlit as st


def _set_landing_route(route: str):
    st.session_state["landing_route"] = route


def _get_landing_route() -> str:
    return st.session_state.get("landing_route", "home")


def _cta_row():
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("✅ Enroll Now", use_container_width=True, key="cta_enroll"):
            _set_landing_route("enroll")
            st.rerun()
    with c2:
        if st.button("🎁 Access Free Week 0 (Orientation)", use_container_width=True, key="cta_week0"):
            _set_landing_route("week0")
            st.rerun()
    with c3:
        if st.button("🔐 Login", use_container_width=True, key="cta_login"):
            _set_landing_route("login")
            st.rerun()


def _back_to_home():
    if st.button("⬅️ Back", key="landing_back"):
        _set_landing_route("home")
        st.rerun()


def render_landing_page():
    route = _get_landing_route()

    # ============ HOME ============
    if route == "home":
        st.markdown("# Chumcred Academy LMS — AI Essentials (6 Weeks)")
        st.markdown(
            "## Real-World Results\n"
            "A practical, beginner-friendly online program that helps you use AI to work smarter, build useful workflows, "
            "create a portfolio, and launch career or business opportunities — anywhere in the world."
        )

        a, b, c, d = st.columns(4)
        a.success("Self-paced weekly lessons")
        b.success("1-hour live recap every Saturday")
        c.success("Assignments + support inside LMS")
        d.success("Certificate + portfolio (Week 6)")

        st.markdown("---")
        _cta_row()

        st.info("Tip: If you’re new, start with **Free Week 0**. If you’re ready, click **Enroll Now**.")

        st.markdown("---")
        st.markdown("## Who This Program Is For")
        st.write(
            "This program is designed for everyone — across industries and backgrounds.\n\n"
            "**Students • Professionals • SMEs • Creators • Job seekers • Anyone curious about AI**"
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

        return

    # ============ ENROLL ============
    if route == "enroll":
        _back_to_home()
        st.markdown("# ✅ Enroll Now")

        st.markdown(
            "**AI Essentials (6 Weeks)** is a practical program designed to help you become confident using AI in real life.\n\n"
            "**What you get:** weekly lessons + assignments + Saturday live recap + support + certificate + portfolio."
        )

        st.markdown("### Next Cohort")
        st.write(
            "- **Duration:** 6 weeks\n"
            "- **Mode:** Self-paced + Saturday live recap (1 hour)\n"
            "- **Support:** Help & Support inside the LMS\n"
            "- **Certification:** Week 6 (Gold/Silver/Bronze)"
        )

        st.markdown("### Enrollment (choose one)")
        st.write(
            "**Option A (Recommended):** Join the WhatsApp enrollment desk and get guided onboarding.\n\n"
            "**Option B:** If you already have your login details, proceed to Login below."
        )

        # ✅ Replace with your real WhatsApp link/number
        st.success("WhatsApp Enrollment Desk: +234 805 557 6770 (replace with your number)")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔐 Login to Enroll", use_container_width=True, key="enroll_login"):
                _set_landing_route("login")
                st.rerun()
        with col2:
            if st.button("🎁 Start with Free Week 0", use_container_width=True, key="enroll_week0"):
                _set_landing_route("week0")
                st.rerun()
        return

    # ============ WEEK 0 ============
    if route == "week0":
        _back_to_home()
        st.markdown("# 🎁 Free Week 0 (Orientation)")

        st.write(
            "Week 0 helps you start strong. You’ll learn:\n"
            "- How to use the LMS\n"
            "- How weekly assignments work\n"
            "- How Saturday live recap works\n"
            "- How to get help inside Help & Support\n"
            "- How to stay consistent and complete the program"
        )

        st.markdown("### Start Week 0 Now")
        st.info("To access Week 0, you need to login (or we can make Week 0 public later).")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔐 Login to Access Week 0", use_container_width=True, key="week0_login"):
                _set_landing_route("login")
                st.rerun()
        with col2:
            if st.button("✅ Enroll (Full Program)", use_container_width=True, key="week0_enroll"):
                _set_landing_route("enroll")
                st.rerun()
        return

    # ============ LOGIN ============
    if route == "login":
        _back_to_home()
        st.markdown("# 🔐 Login")
        st.caption("Scroll down to the login form below.")
        st.info("Use your username and password provided by the admin.")
        return