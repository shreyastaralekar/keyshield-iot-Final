from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_starts_and_generates_demo():
    app_path = Path(__file__).resolve().parents[1] / "app" / "dashboard.py"
    at = AppTest.from_file(app_path).run(timeout=20)
    assert not at.exception
    assert at.title
    assert at.tabs
