"""
brand_assets.py — Brand asset loader with local filesystem and GCS backends.

Bucket structure (identical for local and GCS):
  brands/{brand}/
    Guidelines/brand_guidelines.md   ← full brand guidelines text
    Logos/                           ← brand logo files (.png/.jpg/.webp/.svg)
    Products/                        ← product photography (.jpg/.jpeg/.png/.webp)
    Font/                            ← font files (.ttf/.otf/.woff/.woff2)
    Colours/                         ← colour swatch files (.png/.jpg)
    Assets/                          ← campaign banners and supporting assets

Local mode:  {settings.brand_assets_local_path}/brands/{brand}/...
GCS mode:    gs://{settings.gcs_bucket}/brands/{brand}/...

Switch via env var: BRAND_ASSETS_MODE=local|gcs
"""

from __future__ import annotations

import structlog
from pathlib import Path

from app.config import get_settings

logger   = structlog.get_logger()
settings = get_settings()

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_FONT_EXTS  = {".ttf", ".otf", ".woff", ".woff2"}


class BrandAssetLoader:
    """
    Loads brand assets from a local bucket directory or GCS.
    Returns consistent types regardless of backend.
    Controlled by settings.brand_assets_mode ("local" | "gcs").
    """

    def __init__(self):
        self._mode = settings.brand_assets_mode
        # Resolve local path relative to the project root (parent of app/).
        _project_root       = Path(__file__).resolve().parent.parent
        self._local_root    = _project_root / settings.brand_assets_local_path / "brands"
        #logger.debug(
        #    "brand_asset_loader_init",
        #    mode       = self._mode,
        #    local_root = str(self._local_root),
        #)
        # NEW
        logger.info(
            "brand_asset_loader_init",
            mode        = self._mode,
            local_root  = str(self._local_root),
            root_exists = self._local_root.exists(),
        )

    # ── Public API ────────────────────────────────────────────────────────

    def load_guidelines(self, brand: str) -> str:
        """Return the full text of brand_guidelines.md. Empty string if not found."""
        if self._mode == "gcs":
            return self._gcs_read_text(brand, "Guidelines/brand_guidelines.md")
        return self._local_read_text(brand, "Guidelines/brand_guidelines.md")

    def list_products(self, brand: str) -> list[str]:
        """Return sorted list of product image paths / GCS URIs."""
        return self._list_dir(brand, "Products", _IMAGE_EXTS)

    def list_logos(self, brand: str) -> list[str]:
        """Return sorted list of logo paths / GCS URIs (.png/.jpg/.webp/.svg).
        Checks both 'Logos/' and 'Logo/' folders (some brands use the singular form)."""
        exts = _IMAGE_EXTS | {".svg"}
        logos  = self._list_dir(brand, "Logos", exts)
        logos += self._list_dir(brand, "Logo",  exts)
        return sorted(set(logos))

    def list_fonts(self, brand: str) -> list[str]:
        """Return sorted list of font file paths / GCS URIs."""
        return self._list_dir(brand, "Font", _FONT_EXTS)

    def list_assets(self, brand: str) -> list[str]:
        """Return sorted list of supporting asset paths / GCS URIs."""
        return self._list_dir(brand, "Assets", _IMAGE_EXTS)

    def list_colours(self, brand: str) -> list[str]:
        """Return sorted list of colour swatch paths / GCS URIs."""
        return self._list_dir(brand, "Colours", _IMAGE_EXTS)

    # ── Local backend ─────────────────────────────────────────────────────

    def _local_brand_path(self, brand: str) -> Path:
        return self._local_root / brand

    def _local_read_text(self, brand: str, relative: str) -> str:
        path = self._local_brand_path(brand) / relative
        if not path.exists():
            logger.warning("brand_asset_not_found", brand=brand, path=str(path))
            return ""
        return path.read_text(encoding="utf-8")

    def _local_list_dir(
        self, brand: str, subdir: str, extensions: set[str]
    ) -> list[str]:
        folder = self._local_brand_path(brand) / subdir
        if not folder.is_dir():
            return []
        return sorted(
            str(p)
            for p in folder.rglob("*")
            if p.is_file() and p.suffix.lower() in extensions and not p.name.startswith(".")
        )

    # ── GCS backend ───────────────────────────────────────────────────────

    def _gcs_read_text(self, brand: str, relative: str) -> str:
        try:
            from google.cloud import storage  # type: ignore
            client = storage.Client(project=settings.gcp_project)
            blob   = client.bucket(settings.gcs_bucket).blob(
                f"brands/{brand}/{relative}"
            )
            return blob.download_as_text(encoding="utf-8")
        except Exception as e:
            logger.warning("gcs_read_failed", brand=brand, relative=relative, error=str(e))
            return ""

    def _gcs_list_dir(
        self, brand: str, subdir: str, extensions: set[str]
    ) -> list[str]:
        try:
            from google.cloud import storage  # type: ignore
            client  = storage.Client(project=settings.gcp_project)
            prefix  = f"brands/{brand}/{subdir}/"
            blobs   = client.bucket(settings.gcs_bucket).list_blobs(prefix=prefix)
            return sorted(
                f"gs://{settings.gcs_bucket}/{b.name}"
                for b in blobs
                if Path(b.name).suffix.lower() in extensions
            )
        except Exception as e:
            logger.warning(
                "gcs_list_failed", brand=brand, subdir=subdir, error=str(e)
            )
            return []

    # ── Unified router ────────────────────────────────────────────────────

    def _list_dir(
        self, brand: str, subdir: str, extensions: set[str]
    ) -> list[str]:
        if self._mode == "gcs":
            return self._gcs_list_dir(brand, subdir, extensions)
        return self._local_list_dir(brand, subdir, extensions)


# ── Module-level singleton ─────────────────────────────────────────────────

_loader: BrandAssetLoader | None = None


def get_asset_loader() -> BrandAssetLoader:
    """Return the cached BrandAssetLoader instance (lazy init)."""
    global _loader
    if _loader is None:
        _loader = BrandAssetLoader()
    return _loader
