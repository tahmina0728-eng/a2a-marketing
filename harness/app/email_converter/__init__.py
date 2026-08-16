"""
email_converter — modular document-to-HTML-email pipeline.

Quick start:
    from app.email_converter import EmailConverterAgent

    agent  = EmailConverterAgent()
    result = agent.run(
        files       = [(pdf_bytes, "brief.pdf"), (docx_bytes, "copy.docx")],
        brand_name  = "Haleon",
        brand_color = "#0055A4",
    )
    html = result["html"]

With full AI features (requires GCP project):
    agent = EmailConverterAgent(
        gcp_project = "my-project",
        use_vision  = True,   # Gemini Vision for image understanding
        use_rag     = True,   # Firestore brand RAG + BigQuery campaign RAG
        use_llm     = True,   # Gemini refines headline / subject / bullets
    )
    result = await agent.run_async(files=..., brand_name="Haleon")
"""
from .agent import EmailConverterAgent

__all__ = ["EmailConverterAgent"]
