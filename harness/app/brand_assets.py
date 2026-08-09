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

    def list_brands(self) -> list[str]:
        """Return every brand name that has a folder under brands/, local or GCS."""
        if self._mode == "gcs":
            try:
                from google.cloud import storage  # type: ignore
                client = storage.Client(project=settings.gcp_project)
                names: set[str] = set()
                for blob in client.bucket(settings.gcs_bucket).list_blobs(prefix="brands/"):
                    parts = blob.name.split("/")
                    if len(parts) > 1 and parts[1]:
                        names.add(parts[1])
                return sorted(names)
            except Exception as e:
                logger.warning("gcs_list_brands_failed", error=str(e))
                return []
        if not self._local_root.is_dir():
            return []
        return sorted(p.name for p in self._local_root.iterdir() if p.is_dir())

    def load_guidelines(self, brand: str) -> str:
        """Return brand guidelines text. Tries several known filenames in order."""
        for filename in (
            "Guidelines/brand_guidelines.md",
            "Guidelines/brand_guidelines.txt",
            "Guidelines/Guideline.md",
        ):
            if self._mode == "gcs":
                text = self._gcs_read_text(brand, filename)
            else:
                text = self._local_read_text(brand, filename)
            if text:
                return text
        return ""

    def load_agent_skill(self, brand: str, skill_name: str) -> str:
        """Return the text of a SKILL file from brands/{brand}/Agents/{skill_name}-SKILL.md."""
        relative = f"Agents/{skill_name}-SKILL.md"
        if self._mode == "gcs":
            return self._gcs_read_text(brand, relative)
        return self._local_read_text(brand, relative)

    def load_brand_profile(self, brand: str) -> "dict | None":
        """
        Load brands/{brand}/brand.json and return it as a dict.
        Returns None if the file doesn't exist (brand hasn't been profiled yet).
        """
        import json
        if self._mode == "gcs":
            raw = self._gcs_read_text(brand, "brand.json")
        else:
            raw = self._local_read_text(brand, "brand.json")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("brand_profile_parse_error", brand=brand, error=str(e))
            return None

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
        """Return sorted list of supporting asset paths / GCS URIs.

        For Barclays, puts 'Moments of progress' campaign images first —
        they represent the current campaign platform and should be the
        primary reference for style analysis.
        """
        assets = self._list_dir(brand, "Assets", _IMAGE_EXTS)
        if brand.lower() == "barclays":
            _moments = [a for a in assets if "moments of progress" in a.lower() or "moments_of_progress" in a.lower()]
            _campaigns = [a for a in assets if a not in _moments]
            assets = _moments + _campaigns
        return assets

    def list_colours(self, brand: str) -> list[str]:
        """Return sorted list of colour swatch paths / GCS URIs.

        If no image swatches exist but a barclays-colours.json is present,
        generate a colour swatch PNG on the fly and return it as a data URI
        so Gemini Vision can see the exact brand palette.
        """
        swatches = self._list_dir(brand, "Colours", _IMAGE_EXTS)
        if swatches:
            return swatches

        # Fallback: generate a swatch PNG from JSON colour definitions
        json_swatch = self._generate_colour_swatch_from_json(brand)
        return [json_swatch] if json_swatch else []

    def _generate_colour_swatch_from_json(self, brand: str) -> str:
        """Read barclays-colours.json and render a swatch PNG as a data URI."""
        import json as _json
        try:
            if self._mode == "gcs":
                raw = self._gcs_read_text(brand, "Colours/barclays-colours.json")
            else:
                raw = self._local_read_text(brand, "Colours/barclays-colours.json")
            if not raw:
                return ""
            data = _json.loads(raw)
        except Exception:
            return ""

        # Collect all colours: primary + partner + neutrals + key secondary
        swatches: list[tuple[str, str]] = []  # (name, hex)
        for c in data.get("primary", []):
            swatches.append((c.get("name", ""), c.get("hex", "")))
        for c in data.get("partner_wimbledon", []):
            swatches.append((c.get("name", ""), c.get("hex", "")))
        for c in data.get("neutrals", [])[:3]:
            swatches.append((c.get("name", ""), c.get("hex", "")))
        # A few representative secondary colours
        for grp in ("blues", "teals"):
            for c in data.get("secondary", {}).get(grp, [])[:2]:
                swatches.append((c.get("name", ""), c.get("hex", "")))

        swatches = [(n, h) for n, h in swatches if h and h.startswith("#")]
        if not swatches:
            return ""

        try:
            from PIL import Image, ImageDraw, ImageFont
            import io, base64 as _b64
            sw_w, sw_h = 120, 60
            cols       = min(len(swatches), 6)
            rows       = (len(swatches) + cols - 1) // cols
            img = Image.new("RGB", (sw_w * cols, sw_h * rows), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            for i, (name, hex_val) in enumerate(swatches):
                r = int(hex_val[1:3], 16)
                g = int(hex_val[3:5], 16)
                b = int(hex_val[5:7], 16)
                col, row = i % cols, i // cols
                x0, y0   = col * sw_w, row * sw_h
                draw.rectangle([x0, y0, x0 + sw_w - 2, y0 + sw_h - 2], fill=(r, g, b))
                # Label in contrasting colour
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                txt_col = (0, 0, 0) if lum > 128 else (255, 255, 255)
                try:
                    fnt = ImageFont.load_default(size=9)
                except Exception:
                    fnt = ImageFont.load_default()
                draw.text((x0 + 4, y0 + 4),  hex_val,          fill=txt_col, font=fnt)
                draw.text((x0 + 4, y0 + 16), name[:14],        fill=txt_col, font=fnt)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64_str = _b64.b64encode(buf.getvalue()).decode()
            return f"data:image/png;base64,{b64_str}"
        except Exception as e:
            logger.warning("colour_swatch_generation_failed", brand=brand, error=str(e))
            return ""

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

    def _gcs_read_bytes(self, brand: str, relative: str) -> bytes:
        """Download a binary file (font, image) from GCS. Returns empty bytes on failure."""
        try:
            from google.cloud import storage  # type: ignore
            client = storage.Client(project=settings.gcp_project)
            blob   = client.bucket(settings.gcs_bucket).blob(
                f"brands/{brand}/{relative}"
            )
            return blob.download_as_bytes()
        except Exception as e:
            logger.warning("gcs_read_bytes_failed", brand=brand, relative=relative, error=str(e))
            return b""

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
