from datetime import datetime
from html import escape
from pathlib import Path
import os
import sys

# Support both Streamlit's script runner and normal Python imports.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import altair as alt
import pandas as pd
import streamlit as st
from app import service
from app.demo import seed

st.set_page_config(page_title='QueueSense | Make time for campus', page_icon='◷', layout='wide')
st.markdown('<style>' + Path(__file__).with_name('style.css').read_text(encoding='utf-8-sig') + '</style>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand">◷ Queue<span>Sense</span></div>', unsafe_allow_html=True)
    st.caption('A little less waiting. More campus.')
    st.divider()
    page = st.radio('Workspace', ['Overview', 'Plan a visit', 'Record observations', 'Data & insights', 'Model studio'])
    st.divider()
    demo = st.toggle('Explore demo workspace', value=False)
    st.caption('Synthetic data is isolated from your real observations.' if demo else 'Your campus observations · local workspace')
    st.divider()
    st.caption('CAMPUS CLOCK')
    st.write(service.campus_now().strftime('%a, %d %b · %H:%M'))
    st.caption('Malaysia time · UTC+08:00')
    st.caption('Estimates support decisions. They are not live queue measurements.')

path = os.getenv('QUEUESENSE_DB', 'queuesense.db')
if demo:
    path = str(Path(path).parent / 'queuesense-demo.db')
    with st.spinner('Preparing the demo campus…'):
        seed(path)
    st.info('DEMO WORKSPACE — all observations and evaluation results here are synthetic.')

data = service.dataset(path)
model, metrics = service.current_model(path)
locations = sorted({r['location'] for r in data})
now = service.campus_now()
frame = pd.DataFrame(data)
if data:
    frame['timestamp'] = pd.to_datetime(frame['timestamp'])
    frame['hour'] = frame['timestamp'].dt.hour
    frame['day'] = frame['timestamp'].dt.date


def header(kicker, title, subtitle):
    st.markdown(f'<div class="eyebrow">{kicker}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="lead">{subtitle}</div>', unsafe_allow_html=True)


def forecast_chart(records):
    chart_data = pd.DataFrame(records)
    chart_data['hour'] = pd.to_datetime(chart_data['timestamp']).dt.hour
    chart = alt.Chart(chart_data).mark_line(point=True, color='#2a6b4b', strokeWidth=3).encode(
        x=alt.X('hour:O', title='Campus hour (08:00–18:00)'),
        y=alt.Y('prediction_minutes:Q', title='Estimated wait · minutes', scale=alt.Scale(zero=True)),
        tooltip=[alt.Tooltip('hour:O', title='Hour'), alt.Tooltip('prediction_minutes:Q', title='Minutes')]
    ).properties(height=280).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)


if page == 'Overview':
    header('YOUR CAMPUS, AT A GLANCE', 'Make time for what matters.', 'Find a quieter moment for lunch, coffee, or your next campus errand.')
    if not data:
        st.markdown('<div class="hero"><div class="eyebrow">A fresh start</div><h2>Your campus story starts with one observation.</h2><p>Record a queue and its observed wait, or turn on the demo workspace in the sidebar to explore.</p></div>', unsafe_allow_html=True)
    else:
        results = [model.predict(name, now) for name in locations]
        available = [r for r in results if r['prediction_minutes'] is not None]
        if available:
            best = min(available, key=lambda r: r['prediction_minutes'])
            st.markdown(f'<div class="hero"><div class="eyebrow">Lowest estimated wait · now</div><h2>{escape(best["location"])} · {best["prediction_minutes"]:g} min</h2><p>Compare locations that fit your errand. Cafeterias, clinics, and counters serve different needs.</p></div>', unsafe_allow_html=True)
        st.subheader('Around campus')
        for start in range(0, len(results), 3):
            cols = st.columns(3)
            for col, result in zip(cols, results[start:start+3]):
                value = result['prediction_minutes']
                label = 'No trained data' if value is None else 'Quieter' if value < 10 else 'Allow extra time'
                wait = '—' if value is None else f'{value:g}'
                latest = max(r['timestamp'] for r in data if r['location'] == result['location'])
                col.markdown(f'<div class="place"><span class="tag {"busy" if value is not None and value >= 10 else ""}">{label}</span><h3>{escape(result["location"])}</h3><div class="wait">{wait} <small>min estimated</small></div><p>{result["samples"]} observations at this hour · {result["confidence"]} data support<br>Last observation: {escape(latest[:16].replace("T", " "))}</p></div>', unsafe_allow_html=True)
        st.caption('Confidence reflects sample support only; it is not a calibrated probability. Predictions may be stale as campus conditions change.')
        st.divider()
        left, right = st.columns([2, 1])
        with left:
            st.subheader('The rhythm of the day')
            selected = st.selectbox('Explore a location', locations)
            forecast_chart(service.forecast(selected, now.date(), path))
        with right:
            st.subheader('Behind the estimates')
            st.metric('Observations collected', f'{len(data):,}')
            st.metric('Locations covered', len(locations))
            st.caption('Random Forest · last trained ' + metrics['trained_at'][:16] if 'trained_at' in metrics else 'Location/hour baseline · model not trained yet')

elif page == 'Plan a visit':
    header('A LITTLE PLANNING GOES A LONG WAY', 'Find your quieter hour.', 'Compare the same errand across locations and choose a time that works for you.')
    if not locations:
        st.info('Add observations or explore the demo workspace to plan a visit.')
    else:
        chosen = st.multiselect('Locations suitable for your errand', locations, default=locations[:1])
        day = st.date_input('Visit date', value=now.date(), min_value=now.date())
        records = [r for name in chosen for r in service.forecast(name, day, path)
                   if datetime.fromisoformat(r['timestamp']) >= now and r['prediction_minutes'] is not None]
        if records:
            best = min(records, key=lambda r: r['prediction_minutes'])
            st.success(f"Lowest estimate: {best['location']} at {best['timestamp'][11:16]} — {best['prediction_minutes']:g} minutes.")
            plot = pd.DataFrame(records)
            plot['time'] = pd.to_datetime(plot['timestamp'])
            st.altair_chart(alt.Chart(plot).mark_line(point=True).encode(
                x=alt.X('time:T', title='Visit time'), y=alt.Y('prediction_minutes:Q', title='Estimated minutes'),
                color=alt.Color('location:N', title='Location', scale=alt.Scale(range=['#205c43','#b78c35','#779b9c','#6e6592'])),
                tooltip=['location', alt.Tooltip('time:T', format='%H:%M'), 'prediction_minutes']
            ).properties(height=350).configure_view(stroke=None), use_container_width=True)
            st.dataframe(plot[['location', 'time', 'prediction_minutes', 'samples', 'confidence']], hide_index=True, use_container_width=True)
            st.caption('Planning hours: 08:00–18:00. Confirm actual location opening hours before visiting.')
        else:
            st.info('Choose a location and a future time with observations. After 18:00, choose a later date.')

elif page == 'Record observations':
    header('BETTER DATA, BETTER CAMPUS DAYS', 'Every observation helps.', 'Record the queue you saw and the wait you actually measured. No student names or personal details needed.')
    left, right = st.columns([2, 1])
    with left:
        with st.form('observation', clear_on_submit=False):
            location = st.text_input('Location', placeholder='e.g. North Hall Cafeteria', max_chars=100)
            a, b = st.columns(2)
            day = a.date_input('Observation date', now.date(), max_value=now.date())
            clock = b.time_input('Observation time', now.time().replace(second=0, microsecond=0))
            queue = st.number_input('People waiting', 0, 10000, 5)
            rate = st.number_input('Service rate · people per minute', .01, 10000., 1., step=.1)
            wait = st.number_input('Measured wait · minutes', 0., 1440., 5., step=.5)
            submitted = st.form_submit_button('Save observation', type='primary', use_container_width=True)
        if submitted:
            try:
                item = service.Observation(location=location, timestamp=datetime.combine(day, clock), queue_length=queue, service_rate=rate, wait_minutes=wait)
                service.save(item, path)
                st.success('Observation saved. It is available in Data & insights. Retrain to include it in an existing model.')
            except ValueError as error:
                st.error(str(error))
    with right:
        st.subheader('A quick field guide')
        st.write('**1 · Count the queue**\n\nCount people waiting, excluding those already being served.')
        st.write('**2 · Measure the service rate**\n\nCount people served over a few minutes, then divide by the minutes observed.')
        st.write('**3 · Time the wait**\n\nMeasure from joining the queue until service begins. Do not enter a prediction as the measured wait.')
        st.caption('Collect across weekdays, peak times and quieter hours. Campus time is UTC+08:00.')

elif page == 'Data & insights':
    header('THE OBSERVATION NOTEBOOK', 'See the patterns taking shape.', 'Explore your collection, take a copy, or bring in observations from the field.')
    if data:
        selected = st.multiselect('Filter locations', locations, default=locations)
        filtered = frame[frame.location.isin(selected)]
        a, b, c = st.columns(3)
        a.metric('Observations', len(filtered))
        b.metric('Average measured wait', f'{filtered.wait_minutes.mean():.1f} min' if len(filtered) else '—')
        c.metric('Collection days', filtered.day.nunique())
        if len(filtered):
            st.subheader('Measured wait by hour')
            grouped = filtered.groupby(['hour', 'location'], as_index=False).wait_minutes.mean()
            st.altair_chart(alt.Chart(grouped).mark_bar().encode(x=alt.X('hour:O', title='Hour'), y=alt.Y('wait_minutes:Q', title='Mean measured wait'), color='location:N', xOffset='location:N').properties(height=260), use_container_width=True)
        st.dataframe(filtered.sort_values('timestamp', ascending=False).drop(columns=['hour','day']), hide_index=True, use_container_width=True)
    else:
        st.info('Your observation notebook is empty.')
    st.download_button('Export all observations · CSV', service.export_csv(path), 'queuesense-observations.csv', 'text/csv')
    with st.expander('Import a CSV file'):
        st.caption('Required columns: location, timestamp, queue_length, service_rate, wait_minutes. Imports append rows; repeated uploads create duplicates.')
        uploaded = st.file_uploader('Observation CSV', type=['csv'])
        if st.button('Validate and import', disabled=uploaded is None):
            try:
                if uploaded.size > 2_000_000:
                    raise ValueError('Use a CSV smaller than 2 MB.')
                count = service.import_csv(uploaded.getvalue().decode('utf-8-sig'), path)
                st.success(f'Imported {count} observations. Refresh the page to see them.')
            except (ValueError, UnicodeError) as error:
                st.error(str(error))

else:
    header('TRANSPARENCY BEFORE ACCURACY', 'Know what your model knows.', 'Compare a Random Forest with a simple location-and-hour average on observations held out from training.')
    a, b, c = st.columns(3)
    a.metric('Available observations', len(data))
    b.metric('Baseline MAE', f"{metrics['baseline_mae']:.2f} min" if metrics.get('baseline_mae') is not None else 'Not measured')
    c.metric('Random Forest MAE', f"{metrics['model_mae']:.2f} min" if metrics.get('model_mae') is not None else 'Not measured')
    st.subheader('Train, compare, then decide')
    st.write('Training uses location, hour and weekday. Queue length and service rate are collected for analysis, but are not used as future inputs because they are unknown before your visit.')
    st.write('The newest 20% of timestamps form the test set. Both predictors learn only from earlier rows. At least 50 observations and 10 supported test rows are required to report MAE. Lower MAE is better; a complex model may lose to the baseline.')
    st.caption('30 observations enable training; these thresholds are operational minimums, not proof of adequate accuracy. Collect across multiple weeks and evaluate changing campus conditions.')
    if 'trained_at' in metrics:
        st.caption(f"Last trained: {metrics['trained_at']} · snapshot contains {metrics.get('samples', 0)} observations. New observations require retraining.")
    if st.button('Train & evaluate model', type='primary', disabled=len(data) < 30):
        with st.spinner('Training and checking unseen observations…'):
            service.train(path)
        st.rerun()
    if metrics.get('status') == 'evaluated':
        st.info(f"Held out {metrics['test_samples']} observations after {metrics['cutoff']}. Trained on {metrics['train_samples']}. Unseen-location rows excluded: {metrics['skipped_unseen_locations']}.")
        if metrics['model_mae'] >= metrics['baseline_mae']:
            st.warning('The baseline performs at least as well on this holdout. Do not claim the model improves accuracy.')
    else:
        st.info('No validated error estimate yet. Collect observations across different dates and run training when ready.')
    st.divider()
    st.subheader('Reading confidence responsibly')
    st.write('Low or medium describes the number of observations at a location and hour. It is not a percentage chance of correctness. This application does not yet provide calibrated prediction intervals.')
