import streamlit as st
from agent import write_report
from db import run_query
import time
import os

st.title("Create a Failure Analysis Report")
st.caption("Pick or Type a failed drive's serial number, and an AI agent will write a Failure Analysis Report draft from its SMART data")

@st.cache_data
def get_example_serials():
    """Return a list of failed WD/HGST serial numbers for the dropdown"""
    rows = run_query("SELECT serial_number FROM mv_failure_signatures WHERE manufacturer = 'Western Digital' OR manufacturer = 'HGST (WD)' LIMIT 15;")
    return [row["serial_number"] for row in rows]

try:
    example_serial_number = st.selectbox("Example Serial Numbers", get_example_serials(), index=None, placeholder="Choose a Serial Number")
except Exception as e:
    st.error(f'Trouble connecting: {e}')
    st.stop()
user_serial_number = st.text_input("Input Serial Number").strip()

if st.button("Generate report"):
    if user_serial_number != "":
        serial = user_serial_number
    elif example_serial_number is None:
        st.warning("No serial number was provided")
        st.stop()
    else:
        serial = example_serial_number
    with st.spinner("Analyzing drive..."):
        try:
            start = time.perf_counter()
            report = write_report(serial)
            seconds = time.perf_counter() - start
        except Exception as e:
            st.error(f'Trouble connecting: {e}')
            st.stop()

    st.session_state["serial"] = serial
    st.session_state["report"] = report
    st.session_state["seconds"] = seconds

    os.makedirs("reports", exist_ok=True)
    path = f"reports/{st.session_state["serial"]}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(st.session_state["report"])

if "report" in st.session_state:
    st.write(f"Finished in {st.session_state['seconds']:.1f} seconds")
    st.download_button("Download report (.md)", data=st.session_state["report"], file_name=f"{st.session_state["serial"]}.md")
    st.markdown(st.session_state["report"])
    
    
        

