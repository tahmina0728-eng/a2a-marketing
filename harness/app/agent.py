"""
agent.py — ADK web entry point.

`adk web` discovers agents by scanning for subdirectories containing agent.py.
This file re-exports root_agent from pipeline so the full Workflow DAG is
visible in the ADK web UI.

Run from rebuild/:
    adk web .
"""

from app.pipeline import root_agent  # noqa: F401
