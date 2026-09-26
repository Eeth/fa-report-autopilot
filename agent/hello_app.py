import streamlit as st

st.title("Hello Streamlit")
name = st.text_input("What's your name?")

if st.button("Greet me"):
    st.write(f"Hi {name}!")