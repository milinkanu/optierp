import streamlit as st

from services.api_client import (
    APIError,
    clear_auth_session,
    init_api_config,
    login,
    set_auth_session,
)


st.set_page_config(page_title="FinOps", page_icon="FinOps", layout="wide")
init_api_config()

st.title("FinOps Frontend")

with st.sidebar:
    st.subheader("API services")
    for service, default_url in st.session_state["service_urls"].items():
        st.session_state["service_urls"][service] = st.text_input(
            f"{service.title()} URL",
            value=default_url,
            key=f"{service}_url",
        ).rstrip("/")

    st.divider()
    if st.session_state.get("access_token"):
        st.caption("Signed in")
        st.write(st.session_state.get("company_id", ""))
        if st.button("Logout", use_container_width=True):
            clear_auth_session()
            st.rerun()


if not st.session_state.get("access_token"):
    st.subheader("Login")
    with st.form("login_form"):
        email = st.text_input("Email", value="test@example.com")
        password = st.text_input("Password", type="password", value="password123")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        with st.spinner("Signing in..."):
            try:
                result = login(email, password)
                set_auth_session(result["access_token"])
                st.success("Logged in successfully.")
                st.rerun()
            except APIError as exc:
                st.error(f"Login failed: {exc}")
else:
    st.success("You are logged in.")
    st.write("Use the pages in the sidebar for Dashboard, Onboarding, and Accounting.")
