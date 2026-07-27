"""
haleon_catalog.py — Haleon brand/category catalog and enrichment helpers.

Haleon owns two levels of hierarchy:
  Category → Brand (sub-brand)

This catalog is the authoritative source for that mapping. It is used by
load_brand_context in nodes.py to enrich the brief when brand == "Haleon"
and the user has not explicitly provided a sub_brand / product_category.
"""

from __future__ import annotations

# ── Full catalog ────────────────────────────────────────────────────────────
# key: lowercase brand name (for lookup)
# value: display name + parent category

HALEON_CATALOG: dict[str, dict[str, str]] = {
    # Oral Health
    "sensodyne":   {"brand": "Sensodyne",   "category": "Oral Health"},
    "polident":    {"brand": "Polident",    "category": "Oral Health"},
    "parodontax":  {"brand": "parodontax",  "category": "Oral Health"},

    # Vitamins, Minerals & Supplements
    "centrum":     {"brand": "Centrum",     "category": "Vitamins, Minerals & Supplements"},
    "emergen-c":   {"brand": "Emergen-C",   "category": "Vitamins, Minerals & Supplements"},
    "emergen c":   {"brand": "Emergen-C",   "category": "Vitamins, Minerals & Supplements"},
    "caltrate":    {"brand": "Caltrate",    "category": "Vitamins, Minerals & Supplements"},

    # Respiratory
    "otrivin":     {"brand": "Otrivin",     "category": "Respiratory"},
    "theraflu":    {"brand": "Theraflu",    "category": "Respiratory"},
    "flonase":     {"brand": "Flonase",     "category": "Respiratory"},
    "robitussin":  {"brand": "Robitussin",  "category": "Respiratory"},

    # Pain Relief
    "voltaren":    {"brand": "Voltaren",    "category": "Pain Relief"},
    "panadol":     {"brand": "Panadol",     "category": "Pain Relief"},
    "advil":       {"brand": "Advil",       "category": "Pain Relief"},
    "fenbid":      {"brand": "Fenbid",      "category": "Pain Relief"},
    "contac":      {"brand": "Contac",      "category": "Pain Relief"},
    "grand-pa":    {"brand": "Grand-pa",    "category": "Pain Relief"},
    "grandpa":     {"brand": "Grand-pa",    "category": "Pain Relief"},
    "excedrin":    {"brand": "Excedrin",    "category": "Pain Relief"},

    # Digestive Health
    "tums":        {"brand": "Tums",        "category": "Digestive Health"},
    "eno":         {"brand": "Eno",         "category": "Digestive Health"},
    "benefiber":   {"brand": "Benefiber",   "category": "Digestive Health"},

    # Therapeutic Skin Health
    "fenistil":    {"brand": "Fenistil",    "category": "Therapeutic Skin Health"},
    "zovirax":     {"brand": "Zovirax",     "category": "Therapeutic Skin Health"},
    "bactroban":   {"brand": "Bactroban",   "category": "Therapeutic Skin Health"},
}

# All valid categories (for display / validation)
HALEON_CATEGORIES: list[str] = [
    "Oral Health",
    "Vitamins, Minerals & Supplements",
    "Respiratory",
    "Pain Relief",
    "Digestive Health",
    "Therapeutic Skin Health",
]

# Brands grouped by category (for UI use)
HALEON_BRANDS_BY_CATEGORY: dict[str, list[str]] = {
    "Oral Health":                         ["Sensodyne", "Polident", "parodontax"],
    "Vitamins, Minerals & Supplements":    ["Centrum", "Emergen-C", "Caltrate"],
    "Respiratory":                         ["Otrivin", "Theraflu", "Flonase", "Robitussin"],
    "Pain Relief":                         ["Voltaren", "Panadol", "Advil", "Fenbid", "Contac", "Grand-pa", "Excedrin"],
    "Digestive Health":                    ["Tums", "Eno", "Benefiber"],
    "Therapeutic Skin Health":             ["Fenistil", "Zovirax", "Bactroban"],
}


def lookup_sub_brand(text: str) -> dict[str, str] | None:
    """
    Scan free text for a known Haleon sub-brand name.

    Returns the first match as {"brand": ..., "category": ...}, or None.
    Priority is given to longer / more specific brand names first (Emergen-C
    before Eno) to avoid partial false matches.
    """
    normalized = text.lower()
    # Sort by key length descending so longer names match before shorter ones
    for key in sorted(HALEON_CATALOG, key=len, reverse=True):
        if key in normalized:
            return HALEON_CATALOG[key]
    return None


def enrich_brief(brief_dict: dict) -> dict:
    """
    Enrich a brief dict in-place when brand == "Haleon".

    If product / product_category are missing, scan the objective/goal and
    campaign_name fields for a known Haleon sub-brand and populate them.
    Returns the (possibly mutated) dict.
    """
    brand = brief_dict.get("brand", "")
    if brand.lower() != "haleon":
        return brief_dict

    product          = brief_dict.get("product", "").strip()
    product_category = brief_dict.get("product_category", "").strip()

    # Already fully specified — nothing to do
    if product and product_category and product_category != "Haleon":
        return brief_dict

    # Build search corpus from all free-text fields
    search_corpus = " ".join([
        brief_dict.get("goal", ""),
        brief_dict.get("campaign_name", ""),
        brief_dict.get("fan_truth", ""),
        brief_dict.get("notes", "") or "",
        product,
    ])

    match = lookup_sub_brand(search_corpus)
    if match:
        if not product:
            brief_dict["product"] = match["brand"]
        brief_dict["product_category"] = match["category"]
        brief_dict["sub_brand"] = match["brand"]

    return brief_dict
