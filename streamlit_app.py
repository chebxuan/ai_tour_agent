"""Compatibility entrypoint for Streamlit Cloud and existing local commands."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "legacy" / "streamlit_app.py"), run_name="__main__")
