"""
Brand RAG — retrieves brand guidelines from Firestore to ground email generation.

Storage schema (Firestore collection: "brand_guidelines"):
  document ID : brand_name (lowercase, slugified)
  fields:
    brand_name    : str   — display name
    brand_color   : str   — primary hex colour, e.g. "#0055A4"
    tone_of_voice : str   — e.g. "Confident and human, never corporate"
    do_say        : list  — phrases / patterns to use
    dont_say      : list  — phrases / patterns to avoid
    font_family   : str   — preferred web-safe font stack
    email_footer  : str   — standard footer text override (optional)
    updated_at    : timestamp

Wire-up:
  1. Set GOOGLE_CLOUD_PROJECT env var (or pass project= explicitly).
  2. Ensure the Cloud Run / harness service account has "Cloud Datastore User" role.
  3. Populate the collection via the CampaignOS admin panel or a migration script.
"""
from __future__ import annotations
from typing import Any


_DEFAULT_GUIDELINES: dict[str, Any] = {
    "tone_of_voice": "",
    "do_say":        [],
    "dont_say":      [],
    "font_family":   "'Helvetica Neue', Helvetica, Arial, sans-serif",
    "email_footer":  "",
}


class BrandRAG:
    """
    Retrieves brand guidelines for a given brand name.

    Usage:
        rag = BrandRAG(project="my-gcp-project")
        ctx = await rag.search("Haleon")
        # ctx = { tone_of_voice, do_say, dont_say, font_family, email_footer }
    """

    def __init__(self, project: str = "", collection: str = "brand_guidelines"):
        self._project    = project
        self._collection = collection
        self._client     = None   # lazy Firestore AsyncClient

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import firestore
                self._client = firestore.AsyncClient(project=self._project or None)
            except ImportError:
                raise RuntimeError(
                    "google-cloud-firestore is required for BrandRAG. "
                    "Install: pip install google-cloud-firestore"
                )
        return self._client

    async def search(self, brand_name: str) -> dict[str, Any]:
        """
        Return brand guidelines for brand_name, or defaults if not found.
        Never raises — always returns a usable dict.
        """
        if not brand_name:
            return dict(_DEFAULT_GUIDELINES)
        try:
            db     = self._get_client()
            slug   = brand_name.lower().strip().replace(" ", "_")
            doc    = await db.collection(self._collection).document(slug).get()
            if doc.exists:
                data = doc.to_dict() or {}
                return {**_DEFAULT_GUIDELINES, **data}
        except Exception:
            pass
        return dict(_DEFAULT_GUIDELINES)

    async def upsert(self, brand_name: str, guidelines: dict[str, Any]) -> None:
        """Save or update brand guidelines (admin / setup use)."""
        db   = self._get_client()
        slug = brand_name.lower().strip().replace(" ", "_")
        await db.collection(self._collection).document(slug).set(
            {"brand_name": brand_name, **guidelines}, merge=True
        )
