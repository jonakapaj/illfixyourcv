import streamlit as st

st.set_page_config(page_title="AI CV Optimizer Pro", layout="wide")

st.title("AI CV Optimizer Pro")
st.write("The app is idle. Upload a CV from the analysis screen to begin.")

uploaded_file = st.file_uploader("Upload CV (PDF)", type="pdf")

if uploaded_file is None:
    st.info("No CV loaded yet.")
else:
    st.success(f"Loaded: {uploaded_file.name}")
    st.write("Nothing runs automatically on page load.")
