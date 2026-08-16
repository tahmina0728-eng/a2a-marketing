"""
email_converter — modular document-to-HTML-email pipeline.

Two entry points:

1. REST endpoint (main.py /convert-email):
       from app.email_converter import EmailConverterAgent
       agent  = EmailConverterAgent()
       result = agent.run([(pdf_bytes, "brief.pdf")], brand_name="Haleon")
       html   = result["html"]

2. ADK pipeline DAG:
       from app.email_converter.agent import email_converter_agent
       # wire into a Workflow node
"""
from app.email_converter._pipeline import EmailConverterAgent

__all__ = ["EmailConverterAgent"]
