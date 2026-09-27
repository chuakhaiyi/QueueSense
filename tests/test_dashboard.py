from pathlib import Path
from streamlit.testing.v1 import AppTest
from app import service


def test_dashboard_pages_and_capture(tmp_path, monkeypatch):
    path = str(tmp_path / 'real.db')
    monkeypatch.setenv('QUEUESENSE_DB', path)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app' / 'dashboard.py'), default_timeout=60).run()
    assert not app.exception
    app.sidebar.radio[0].set_value('Record observations').run()
    app.text_input[0].set_value('Test Cafe')
    app.button[0].click().run()
    assert not app.exception
    assert len(service.dataset(path)) == 1
    app.sidebar.toggle[0].set_value(True).run()
    for page in ['Overview','Plan a visit','Data & insights','Model studio']:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, page
    assert len(service.dataset(path)) == 1  # demo never contaminates real observations
