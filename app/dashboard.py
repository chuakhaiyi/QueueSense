from datetime import datetime, time
import pandas as pd
import streamlit as st
from app.db import connect, add_observation, rows
from app.model import QueueModel

st.set_page_config(page_title="QueueSense", page_icon="⏱️", layout="wide")
st.title("QueueSense")
st.caption("Campus queue estimates from your observations")
conn = connect()
data = rows(conn)
model = QueueModel(data)

with st.sidebar:
    st.header("Record observation")
    location = st.text_input("Location", "Main Cafeteria")
    day = st.date_input("Date", datetime.now().date())
    clock = st.time_input("Time", datetime.now().time().replace(second=0, microsecond=0))
    timestamp = datetime.combine(day, clock if isinstance(clock, time) else time())
    queue = st.number_input("Queue length", min_value=0, value=5)
    rate = st.number_input("Service rate (people/min)", min_value=0.01, value=0.5)
    wait = st.number_input("Observed wait (minutes)", min_value=0.0, value=10.0)
    if st.button("Save observation"):
        add_observation(conn, location, timestamp.isoformat(), queue, rate, wait)
        st.success("Saved")
        st.rerun()

tab_capture, tab_estimates, tab_history, tab_evaluation = st.tabs(["Capture", "Live estimates", "History", "Evaluation"])
with tab_capture:
    st.info("Use the sidebar to record observations. Collect data across different hours before trusting predictions.")
    st.write(f"**{len(data)}** observations collected across **{len(set(r['location'] for r in data))}** locations.")
if data:
  with tab_estimates:
    left, right = st.columns(2)
    with left:
        st.subheader("Current estimate")
        selected = st.selectbox("Location", sorted({r["location"] for r in data}))
        result = model.predict(selected, datetime.now())
        st.metric("Estimated wait", f"{result['prediction_minutes']} min")
        st.write(f"Confidence: **{result['confidence']}** · {result['samples']} matching samples")
    with right:
        st.subheader("Model check")
        metrics = model.mae()
        st.metric("Baseline MAE", f"{metrics['baseline_mae']} min")
        st.metric("Model MAE", f"{metrics['model_mae']} min")
  with tab_history:
    frame = pd.DataFrame([dict(r) for r in data])
    st.subheader("Collected observations")
    st.dataframe(frame, use_container_width=True, hide_index=True)
  with tab_evaluation:
    st.subheader("Measured performance")
    st.json(model.evaluate())
else:
    st.warning("Record an observation to unlock estimates and evaluation.")
