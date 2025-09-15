import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Inspection Report Processor",
    page_icon="🏢",
    layout="wide"
)

# Simple authentication
def simple_login():
    st.title("Building Inspection System")
    
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if username == "admin" and password == "admin123":
                st.session_state.authenticated = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials")

# Main app
def main_app():
    st.title("Inspection Report System")
    st.write(f"Welcome, {st.session_state.username}!")
    
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.success("App is working! You can now add features back gradually.")

# App routing
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    simple_login()
else:
    main_app()