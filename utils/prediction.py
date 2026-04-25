import joblib
import streamlit as st

@st.cache_resource
def load_model():
    model_path = "models/engagement_model.joblib.gz"
    return joblib.load(model_path)