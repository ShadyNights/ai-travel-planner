"""Configuration management with environment variable loading."""

import os
from dotenv import load_dotenv

# Load local .env when present
load_dotenv()

# Prefer environment variable, but fallback to Streamlit secrets when available
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

try:
    if not GROQ_API_KEY:
        import streamlit as st
        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
except Exception:
    # Streamlit not available or secrets not configured
    pass
