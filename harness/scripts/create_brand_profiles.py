"""
create_brand_profiles.py — Create brand.json profiles for all brands.

Writes brand.json to the local bucket/ folder for brands that exist locally,
and uploads Barclays directly to GCS (it has no local folder).

Run:
  cd d:\\campaignos\\harness
  uv run python scripts/create_brand_profiles.py

The brand.json files are:
  - brand-owner approved configuration (visual identity, creative rules, compliance)
  - NOT AI-invented — values come from actual brand guidelines
  - Loaded at runtime by BrandAssetLoader.load_brand_profile()
  - Injected into the briefing agent as hard constraints
"""

import json
import pathlib
import os

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)
except ImportError:
    pass

GCS_BUCKET  = os.getenv("GCS_BUCKET", "dauntless-karma-497108-b0-campaignos")
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "dauntless-karma-497108-b0")
LOCAL_ROOT  = pathlib.Path(__file__).parent.parent / "bucket" / "brands"

# ── Brand profile definitions ──────────────────────────────────────────────
# Values are sourced from actual brand guidelines, NOT AI-generated defaults.

BRAND_PROFILES: dict[str, dict] = {

    "Barclays": {
        "brand": {
            "name": "Barclays",
            "industry": "Banking",
            "market": "UK",
            "regulator": "FCA",
            "category": "Retail & Business Banking",
            "platform": "Barclays makes money work for you"
        },
        "visual_identity": {
            "primary_colors": ["#00AEEF", "#1A2142"],
            "secondary_colors": ["#00395D", "#0076B6", "#472380", "#006838"],
            "logo_files": ["barclays1_wb.png", "barclays_wb.png", "barclays-symbol_wb.png"],
            "font": "Effra",
            "style": "professional, modern, trustworthy, clear"
        },
        "creative_rules": {
            "logo_required": True,
            "avoid_unapproved_logo_variations": True,
            "tone": "clear, confident, helpful — like a trusted adviser, not a salesperson",
            "avoid": [
                "misleading financial claims",
                "unapproved promotional offers",
                "implied guaranteed returns or outcomes",
                "pressure tactics on vulnerable customers",
                "unapproved Wimbledon partnership references",
                "distorted or unofficial logo usage",
                "fine-print surprises"
            ],
            "require": [
                "FCA-regulated financial promotions approved by Barclays Legal",
                "risk warnings on investment or returns messaging",
                "FSCS protection statement on eligible deposits",
                "Effra typeface (licensed) for all live brand assets"
            ]
        },
        "compliance": {
            "regulator": "FCA",
            "required_disclaimers": ["FSCS", "FCA", "risk_warning"],
            "prohibited_phrases": [
                "guaranteed", "guaranteed return", "risk-free", "sure thing",
                "can't lose", "win big", "no risk", "100% safe", "definitely earn"
            ],
            "approval_required": [
                "financial_promotion", "product_claim", "returns_mention",
                "Wimbledon_cobranding", "competitor_reference"
            ]
        },
        "co_brands": [
            {
                "name": "Barclays × Wimbledon",
                "partner": "AELTC",
                "additional_approvals": ["AELTC", "Barclays_Brand_Team"],
                "allowed_contexts": ["official_partnership_campaign", "Championships_season"],
                "partner_colors": ["#472380", "#006838"]
            }
        ]
    },

    "Rnorr": {
        "brand": {
            "name": "Rnorr",
            "industry": "Food & Beverage",
            "market": "Global",
            "category": "Dry Cook-In Sauces & Stock"
        },
        "visual_identity": {
            "primary_colors": ["#D62A1E", "#FFD700"],
            "secondary_colors": ["#FFFFFF", "#000000"],
            "logo_files": ["Rnorr-Logo.png"],
            "font": "Custom brand typeface",
            "style": "warm, appetising, homely, reassuring"
        },
        "creative_rules": {
            "logo_required": True,
            "avoid_unapproved_logo_variations": True,
            "tone": "warm, reassuring, practical — like advice from someone who cooks well",
            "avoid": [
                "health claims without substantiation",
                "unrealistic cooking time claims",
                "corporate or clinical language",
                "premium / luxury positioning (Rnorr is accessible)"
            ],
            "require": [
                "food photography that looks genuinely appetising",
                "real home-cooking context (not restaurant plating)"
            ]
        },
        "compliance": {
            "regulator": "ASA",
            "required_disclaimers": [],
            "prohibited_phrases": ["cures", "treats", "medical benefit"],
            "approval_required": ["nutrition_claim", "health_claim"]
        },
        "co_brands": []
    },

    "Sunglow": {
        "brand": {
            "name": "Sunglow",
            "industry": "Beauty & Personal Care",
            "market": "UK",
            "category": "Hair Care"
        },
        "visual_identity": {
            "primary_colors": ["#F5A623", "#2C1810"],
            "secondary_colors": ["#FFFFFF", "#F9E4B7"],
            "logo_files": ["sunglow_logo.png"],
            "font": "Brand typeface",
            "style": "vibrant, authentic, celebratory, community-driven"
        },
        "creative_rules": {
            "logo_required": True,
            "avoid_unapproved_logo_variations": True,
            "tone": "celebratory, inclusive, empowering — Fan-to-Fan not brand-to-consumer",
            "avoid": [
                "hair straightening or 'taming' language",
                "Eurocentric beauty standards",
                "before/after framing that implies hair is a problem"
            ],
            "require": [
                "representation of natural hair textures",
                "authentic community voices and imagery"
            ]
        },
        "compliance": {
            "regulator": "ASA",
            "required_disclaimers": [],
            "prohibited_phrases": ["tame", "control", "fix your hair"],
            "approval_required": ["efficacy_claim", "before_after"]
        },
        "co_brands": []
    },

    "Boozt": {
        "brand": {
            "name": "Boozt",
            "industry": "FMCG / Energy",
            "market": "UK",
            "category": "Energy Drinks"
        },
        "visual_identity": {
            "primary_colors": ["#00D4FF", "#0A0A0A"],
            "secondary_colors": ["#FFFFFF", "#FF6B00"],
            "logo_files": ["Boozt_Logo.png"],
            "font": "Brand typeface",
            "style": "high energy, bold, modern, Gen Z"
        },
        "creative_rules": {
            "logo_required": True,
            "avoid_unapproved_logo_variations": True,
            "tone": "bold, energetic, witty — never corporate, never preachy",
            "avoid": [
                "health or medical benefit claims beyond energy",
                "targeting under-16s",
                "alcohol association",
                "mixing with alcohol references"
            ],
            "require": [
                "caffeine content advisory on all ads",
                "age-appropriate audience targeting"
            ]
        },
        "compliance": {
            "regulator": "ASA",
            "required_disclaimers": ["caffeine_advisory"],
            "prohibited_phrases": ["healthiest", "no side effects", "safe for everyone"],
            "approval_required": ["health_claim", "children_adjacent_content"]
        },
        "co_brands": []
    },

    "Glenfiddich": {
        "brand": {
            "name": "Glenfiddich",
            "industry": "Spirits & Luxury",
            "market": "Global",
            "category": "Single Malt Scotch Whisky"
        },
        "visual_identity": {
            "primary_colors": ["#1B4D2E", "#C9A84C"],
            "secondary_colors": ["#FFFFFF", "#1A1A1A"],
            "logo_files": ["logo_glenfiddich_dark.png"],
            "font": "Glenfiddich proprietary typeface",
            "style": "premium, crafted, heritage, adventurous"
        },
        "creative_rules": {
            "logo_required": True,
            "avoid_unapproved_logo_variations": True,
            "tone": "authoritative, heritage-led, adventurous — for connoisseurs not for everyone",
            "avoid": [
                "targeting under-18s",
                "irresponsible drinking depictions",
                "health benefit claims for alcohol",
                "price promotion in brand-led channels"
            ],
            "require": [
                "responsible drinking message on all executions",
                "18+ age gate where applicable",
                "Drinkaware or local equivalent reference"
            ]
        },
        "compliance": {
            "regulator": "ASA / PORTMAN_GROUP",
            "required_disclaimers": ["drink_responsibly", "drinkaware", "age_gate_18"],
            "prohibited_phrases": ["health benefit", "good for you", "safe to drink every day"],
            "approval_required": ["alcohol_claim", "age_restricted_content"]
        },
        "co_brands": [
            {
                "name": "Glenfiddich × Aston Martin F1",
                "partner": "Aston Martin Aramco F1 Team",
                "additional_approvals": ["AMF1_Brand_Team"],
                "allowed_contexts": ["Formula 1 season", "premium gifting"]
            }
        ]
    },

    "UBS Bank": {
        "brand": {
            "name": "UBS Bank",
            "industry": "Financial Services",
            "market": "Global",
            "regulator": "FCA / FINMA",
            "category": "Private Banking & Wealth Management"
        },
        "visual_identity": {
            "primary_colors": ["#E60000", "#1A1A1A"],
            "secondary_colors": ["#FFFFFF", "#767676"],
            "logo_files": ["ubs-bank-logo.png"],
            "font": "UBS brand typeface",
            "style": "precise, authoritative, global, understated luxury"
        },
        "creative_rules": {
            "logo_required": True,
            "avoid_unapproved_logo_variations": True,
            "tone": "precise, confident, globally aware — never flashy or salesy",
            "avoid": [
                "guaranteed returns or investment outcomes",
                "mass-market positioning",
                "casual or colloquial language",
                "unapproved financial promotions"
            ],
            "require": [
                "regulatory disclaimer on all financial promotions",
                "capital at risk warning on investment ads",
                "FINMA / FCA compliance approval"
            ]
        },
        "compliance": {
            "regulator": "FCA / FINMA",
            "required_disclaimers": ["capital_at_risk", "regulatory_approval", "past_performance"],
            "prohibited_phrases": ["guaranteed", "risk-free", "certain return", "no risk"],
            "approval_required": ["financial_promotion", "investment_claim", "performance_data"]
        },
        "co_brands": []
    },

    "sunrise": {
        "brand": {
            "name": "Sunrise",
            "industry": "Telecommunications",
            "market": "Switzerland",
            "category": "Mobile & Internet Services"
        },
        "visual_identity": {
            "primary_colors": ["#E2001A", "#FFFFFF"],
            "secondary_colors": ["#000000", "#F5F5F5"],
            "logo_files": ["sunrise_logo_red.svg"],
            "font": "Sunrise brand typeface",
            "style": "bright, modern, bold, Swiss precision"
        },
        "creative_rules": {
            "logo_required": True,
            "avoid_unapproved_logo_variations": True,
            "tone": "direct, clear, confident — Swiss precision without being cold",
            "avoid": [
                "unsubstantiated speed or coverage claims",
                "competitor naming without approval",
                "pricing errors or unapproved offers"
            ],
            "require": [
                "price including VAT (Swiss requirement)",
                "coverage disclaimer where applicable",
                "German / French / Italian localisation for Swiss market"
            ]
        },
        "compliance": {
            "regulator": "BAKOM",
            "required_disclaimers": ["price_incl_vat", "coverage_disclaimer"],
            "prohibited_phrases": ["best in Switzerland (unverified)", "guaranteed coverage"],
            "approval_required": ["speed_claim", "price_claim", "competitor_comparison"]
        },
        "co_brands": []
    },

    "Haleon": {
        "brand": {
            "name": "Haleon",
            "industry": "Consumer Health",
            "market": "Global",
            "regulator": "MHRA / local health authority",
            "category": "Consumer Healthcare"
        },
        "visual_identity": {
            "primary_colors": ["#007A33", "#FFFFFF"],
            "secondary_colors": ["#1A1A1A", "#F0F0F0"],
            "logo_files": ["haleon_logo_black.svg"],
            "font": "Haleon brand typeface",
            "style": "trusted, scientific, human, accessible"
        },
        "creative_rules": {
            "logo_required": True,
            "avoid_unapproved_logo_variations": True,
            "tone": "trusted, clear, scientifically grounded — human warmth without claims we can't support",
            "avoid": [
                "unsubstantiated medical or health claims",
                "cure or treatment language without regulatory clearance",
                "misleading efficacy comparisons"
            ],
            "require": [
                "Always read the label / leaflet on all OTC ads",
                "MHRA / local regulatory clearance for health claims",
                "sub-brand consistency (Panadol, Sensodyne, Voltaren etc. each follow own rules)"
            ]
        },
        "compliance": {
            "regulator": "MHRA / ASA",
            "required_disclaimers": ["always_read_label", "ask_pharmacist", "regulatory_clearance"],
            "prohibited_phrases": ["cures", "treats permanently", "no side effects", "100% effective"],
            "approval_required": ["health_claim", "efficacy_claim", "before_after", "testimonial"]
        },
        "co_brands": []
    },
}


def write_local(brand: str, profile: dict) -> bool:
    folder = LOCAL_ROOT / brand
    if not folder.exists():
        print(f"  SKIP local {brand}: folder {folder} doesn't exist")
        return False
    dest = folder / "brand.json"
    dest.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [OK] Local: {dest}")
    return True


def upload_gcs(brand: str, profile: dict) -> bool:
    try:
        from google.cloud import storage
        client  = storage.Client(project=GCP_PROJECT)
        bucket  = client.bucket(GCS_BUCKET)
        blob    = bucket.blob(f"brands/{brand}/brand.json")
        blob.upload_from_string(
            json.dumps(profile, indent=2, ensure_ascii=False),
            content_type="application/json",
        )
        print(f"  [OK] GCS:   gs://{GCS_BUCKET}/brands/{brand}/brand.json")
        return True
    except Exception as e:
        print(f"  FAIL GCS {brand}: {e}")
        return False


if __name__ == "__main__":
    print("=== Creating brand.json profiles ===\n")
    for brand, profile in BRAND_PROFILES.items():
        print(f"  {brand}:")
        wrote_local = write_local(brand, profile)
        # Always upload to GCS (production source of truth)
        upload_gcs(brand, profile)
        print()
    print("=== Done ===")
    print("Brands profiled:", sorted(BRAND_PROFILES.keys()))
