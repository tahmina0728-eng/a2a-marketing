"""
models.py — Pydantic models for all CampaignOS agents.

Used as:
  - Input validation (BriefRequest from human form)
  - Output schema (MachineBrief → Strategy Agent input)
  - Tool schemas (ADK reads type hints for tool calling)
  - Brand lock enforcement (BrandLocks canonical values)
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── ENUMS ──────────────────────────────────────────────────────────────────

class BriefStatus(str, Enum):
    READY        = "READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INCOMPLETE   = "INCOMPLETE"


class FanTruthVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class KPIFlag(str, Enum):
    OK          = "OK"
    AMBITIOUS   = "AMBITIOUS"
    UNREALISTIC = "UNREALISTIC"


class FlagType(str, Enum):
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"


class MomentType(str, Enum):
    DAY_TO_DAY   = "Day-to-Day"
    BRAND_MOMENT = "Brand Moment"
    PARTNERSHIP  = "Partnership Moment"


# ── CULTURE ANALYSIS ──────────────────────────────────────────────────────

class CultureAnalysis(BaseModel):
    """Output of culture_formatter — structured cultural intelligence for the brief."""
    summary:           str       = Field(..., description="Key cultural insight in 3–5 sentences, actionable for this specific brief")
    sentiment_metrics: dict      = Field(default_factory=dict, description="Trend/topic → momentum descriptor, e.g. {'premium cooking revival': 'high momentum, youth-led'}")
    recommendations:   list[str] = Field(default_factory=list, description="3–5 concrete cultural hooks the campaign can authentically tap into")


# ── REQUEST MODELS ────────────────────────────────────────────────────────

class AudienceInput(BaseModel):
    segment:             str           = Field(..., description="Audience segment name")
    location:            str           = Field(default="UK")
    age_range:           str           = Field(..., description="Age range e.g. 18-34")
    gender:              str           = Field(default="All genders")
    income:              Optional[str] = None
    interests:           Optional[str] = None
    additional_criteria: Optional[str] = None


class BriefRequest(BaseModel):
    campaign_name:    str              = Field(..., min_length=3, max_length=100)
    brand:            str              = Field(default="")
    goal:             str
    budget:           str
    kpis:             str              = Field(..., description="Comma-separated KPI targets")
    product:          str
    product_category: str
    fan_truth:        str              = Field(..., description="The real human insight — Fan Truth")
    channels:         list[str]        = Field(..., min_length=1)
    market:           str              = Field(default="UK")
    season:           str
    moment_type:      MomentType       = Field(default=MomentType.DAY_TO_DAY)
    audience:         AudienceInput
    tone:             str              = Field(default="Warm & friendly")
    legal_claims:     Optional[str]    = None
    guardrails:       Optional[str]    = None
    notes:            Optional[str]    = None


# ── BRAND LOCKS ───────────────────────────────────────────────────────────

class BrandLocks(BaseModel):
    """
    Non-negotiable brand rules.
    These values are ALWAYS canonical. The AI model must never override them.
    They are enforced as hard constraints after every agent response.
    """
    font:                Optional[str] = None
    primary_colour:      Optional[str] = None
    accent_colour:       Optional[str] = None
    logo:                Optional[str] = None
    token_placement:     str       = "bottom-left or top-right only"
    tagline:             Optional[str] = None
    voice:               str       = "Fan-to-Fan — Authentic, Witty, Optimistic"
    sonic:               Optional[str] = None
    headline_max_words:  int       = 6
    caption_max_chars:   int       = 200
    cta_max_words:       int       = 3
    colour_ratio_short:  str       = "brand 10 : product 1 (<=3s dwell)"
    colour_ratio_medium: str       = "brand 5 : product 5 (1-2 min dwell)"
    colour_ratio_long:   str       = "brand 1 : product 10 (2+ min dwell)"
    forbidden:           list[str] = [
        "non-brand non-product colours",
        "mixing Product IP colours across products",
        "tagline in captions or body copy",
        "corporate or salesy language",
        "over-explanation in copy",
        "condescension or talking down to customer",
    ]


# ── OUTPUT MODELS ─────────────────────────────────────────────────────────

class ValidationResult(BaseModel):
    score:   int          = Field(..., ge=0, le=100)
    status:  BriefStatus
    summary: str


class FanTruthScore(BaseModel):
    specific:              int             = Field(..., ge=0, le=100)
    shared:                int             = Field(..., ge=0, le=100)
    special:               int             = Field(..., ge=0, le=100)
    overall:               int             = Field(..., ge=0, le=100)
    verdict:               FanTruthVerdict
    note:                  Optional[str]   = None
    suggested_alternative: Optional[str]   = None


class KPICheck(BaseModel):
    kpi:            str
    target:         str
    benchmark:      str
    flag:           KPIFlag
    recommendation: Optional[str] = None


class ChannelIntelligence(BaseModel):
    channel:               str
    avg_ctr:               Optional[str] = None
    avg_cpm:               Optional[str] = None
    avg_engagement_rate:   Optional[str] = None
    colour_ratio:          Optional[str] = None
    recommended_ad_length: Optional[str] = None
    flag:                  Optional[str] = None


class AudienceOutput(BaseModel):
    segment_name:        str
    location:            str
    age_range:           str
    gender:              str
    interests:           list[str]
    psychographic_notes: str


class CreativeOutput(BaseModel):
    tone:                       str
    key_message_recommendation: str
    legal_claims:               str
    guardrails:                 list[str]


class ComplianceFlag(BaseModel):
    type:    FlagType
    message: str
    section: Optional[str] = None


class StructuredBrief(BaseModel):
    campaign_name:             str
    brand:                     str
    goal:                      str
    budget:                    str
    kpis:                      list[str]
    channels:                  list[str]
    moment_type:               str
    market:                    str
    season:                    str
    start_date_recommendation: str
    audience:                  AudienceOutput
    creative:                  CreativeOutput
    data_insights:             str
    enrichment_notes:          str
    brand_locks:               BrandLocks
    downstream_ready:          bool = True


class MachineBrief(BaseModel):
    campaign_id:          str
    validation:           ValidationResult
    fan_truth_score:      FanTruthScore
    kpi_flags:            list[KPICheck]
    channel_intelligence: list[ChannelIntelligence]
    brand_locks:          BrandLocks
    flags:                list[ComplianceFlag]
    structured_brief:     StructuredBrief
    handoff_message:      str


class BriefResponse(BaseModel):
    status:             str
    campaign_id:        str
    machine_brief:      dict
    processing_time_ms: int


# ── BRAND ASSET MODELS ────────────────────────────────────────────────────

class BrandAssetsManifest(BaseModel):
    """All discoverable brand assets for a given brand, resolved by BrandAssetLoader."""
    brand:           str
    guidelines_text: str       = ""
    product_paths:   list[str] = Field(default_factory=list)
    logo_paths:      list[str] = Field(default_factory=list)
    font_paths:      list[str] = Field(default_factory=list)
    asset_paths:     list[str] = Field(default_factory=list)
    colour_paths:    list[str] = Field(default_factory=list)


# ── GRAPH NODE DATA MODELS ────────────────────────────────────────────────

class BriefingContext(BaseModel):
    """
    All brand and context data pre-loaded by the load_brand_context function node.
    Passed to briefing_agent via input_schema — the LLM receives all data
    without needing to call any data-loading tools.
    """
    brief_request:               dict      = Field(default_factory=dict,  description="Parsed campaign brief fields")
    brand_guidelines:            str       = Field(default="",            description="Full brand guidelines markdown text")
    brand_rules_summary:         str       = Field(default="",            description="Brand rules search result summary")
    fan_truth_summary:           str       = Field(default="",            description="Fan Truth examples and benchmarks")
    campaign_benchmarks_summary: str       = Field(default="",            description="Historical campaign benchmark summary")
    channel_benchmarks_summary:  str       = Field(default="",            description="Per-channel performance benchmark summary")
    moment_type_rules_summary:   str       = Field(default="",            description="Moment type rules summary")
    brand_locks:                 dict           = Field(default_factory=dict,  description="Canonical brand lock values")
    product_paths:               list[str]      = Field(default_factory=list,  description="Product image paths / GCS URIs")
    logo_paths:                  list[str]      = Field(default_factory=list,  description="Logo file paths / GCS URIs")
    product_image_map:           dict[str, str] = Field(default_factory=dict,  description="Product1/Product2 → GCS URI map")


# ── HITL GATE MODELS ──────────────────────────────────────────────────────

class BriefApproval(BaseModel):
    """Output of the hitl_brief_approval gate."""
    approved: bool
    notes:    str = ""


class KVSelection(BaseModel):
    """Output of the hitl_kv_selection gate."""
    selected_concept_id: str
    notes:               str = ""


# ── STRATEGY STAGE ────────────────────────────────────────────────────────

class ChannelPriority(BaseModel):
    channel:   str
    priority:  int  = Field(..., ge=1, le=10)
    rationale: str  = ""


class MessagingPillar(BaseModel):
    pillar:      str
    description: str = ""


class CampaignStrategy(BaseModel):
    """Legacy strategy model — superseded by CreativeStrategy from creative_director."""
    campaign_id:         str
    strategic_framework: str
    hero_message:        str
    channel_priorities:  list[ChannelPriority] = Field(default_factory=list)
    messaging_pillars:   list[MessagingPillar] = Field(default_factory=list)
    budget_allocation:   dict[str, float]      = Field(default_factory=dict)
    timing_notes:        str                   = ""
    brand_locks:         BrandLocks            = Field(default_factory=BrandLocks)
    handoff_message:     str                   = ""


# ── CREATIVE DIRECTION STAGE ──────────────────────────────────────────────

class BigIdea(BaseModel):
    """The singular creative concept at the heart of the campaign."""
    title:               str = Field(..., description="Punchy idea title, ≤6 words")
    essence:             str = Field(..., description="One sentence: what this campaign makes people feel")
    visual_world:        str = Field(..., description="3–4 sentences: the visual universe, mood, and aesthetic register")
    copy_direction:      str = Field(..., description="The tone, register, rhythm, and 2–3 key phrase examples that demonstrate the creative voice")
    hero_proposition:    str = Field(..., description="What we are saying about the product in this idea")
    emotional_territory: str = Field(..., description="The emotional space we occupy; what people will feel and remember")


class CreativeStrategy(BaseModel):
    """Output of creative_director — full campaign strategy built on the Big Idea."""
    campaign_id:         str
    big_idea:            BigIdea
    strategic_framework: str                   = Field(..., description="Overarching campaign approach, 2–3 sentences")
    hero_message:        str                   = Field(..., description="Single strongest campaign message, ≤8 words, Fan-to-Fan voice")
    channel_priorities:  list[ChannelPriority] = Field(default_factory=list)
    messaging_pillars:   list[MessagingPillar] = Field(default_factory=list)
    budget_allocation:   dict[str, float]      = Field(default_factory=dict, description="Channel → % allocation (must sum to 100)")
    timing_notes:        str                   = ""
    brand_locks:         BrandLocks            = Field(default_factory=BrandLocks)
    culture_context:     str                   = Field(..., description="1–2 sentences: the specific cultural insight that shaped the Big Idea")
    handoff_message:     str                   = Field(..., description="Inspiring 3–4 sentence brief to the KV art directors about the Big Idea")


# ── COPY STAGE ───────────────────────────────────────────────────────────

class CopyVariant(BaseModel):
    """A single length variant of campaign copy."""
    headline: str            = Field(..., description="Primary headline")
    subline:  Optional[str]  = Field(None, description="Optional supporting line")
    body:     Optional[str]  = Field(None, description="Optional body copy (medium/long only)")


class CampaignCopy(BaseModel):
    """Output of copy_agent — three length variants for use across the pipeline."""
    campaign_id: str
    short:       CopyVariant = Field(..., description="KV/OOH headline: ≤6 words, no body")
    medium:      CopyVariant = Field(..., description="Social/display: ≤10 word headline + ≤20 word subline")
    long:        CopyVariant = Field(..., description="Press/editorial: headline + body up to 60 words total")
    copy_notes:  str         = Field(..., description="Craft rationale — what emotional register these words are working in and why")


# ── KV STAGE ─────────────────────────────────────────────────────────────

class KVConcept(BaseModel):
    """Output of a single kv_generator node."""
    concept_id:             str
    generator_id:           int  = 0
    angle:                  str  = ""
    title:                  str
    description:            str
    visual_direction:       str
    colour_palette:         list[str] = Field(default_factory=list)
    image_prompt:           str       = ""
    typography_guidance:    str       = ""
    rationale:              str       = ""
    brand_compliance_notes: str       = ""


class KVRankerOutput(BaseModel):
    """Output of the kv_ranker fan-in node."""
    campaign_id:         str
    selected_concept:    KVConcept
    all_concepts:        list[KVConcept] = Field(default_factory=list)
    selection_rationale: str             = ""


# ── CHANNEL ROUTING STAGE ─────────────────────────────────────────────────

class ChannelTask(BaseModel):
    """A single channel's work order, produced by channel_router."""
    channel:       str
    format:        str
    brief_summary: str               = ""
    asset_specs:   dict[str, str]    = Field(default_factory=dict)


class ChannelPlan(BaseModel):
    """Output of the channel_router node."""
    campaign_id: str
    tasks:       list[ChannelTask] = Field(default_factory=list)


# ── CONTENT STAGE ─────────────────────────────────────────────────────────

class ChannelContent(BaseModel):
    """Content assets for a single channel."""
    channel:         str
    format:          str
    headline:        str
    body:            str
    cta:             str
    caption:         str = ""
    image_direction: str = ""
    image_prompt:    str = ""
    legal_text:      str = ""
    notes:           str = ""


class ContentPackage(BaseModel):
    """Output of the content_agent node — all channel content for this campaign."""
    campaign_id:      str
    selected_concept: KVConcept
    channel_contents: list[ChannelContent] = Field(default_factory=list)
    brand_locks:      BrandLocks           = Field(default_factory=BrandLocks)


# ── EXECUTION STAGE ───────────────────────────────────────────────────────

class ExecutionResult(BaseModel):
    """Stub activation result for a single channel."""
    channel:          str
    status:           str            = "STUB"
    activation_notes: str            = ""
    platform_ids:     dict[str, str] = Field(default_factory=dict)


class ExecutionPackage(BaseModel):
    """Output of the execution_agent node."""
    campaign_id:       str
    execution_results: list[ExecutionResult] = Field(default_factory=list)
    summary:           str                   = ""


# ── AGGREGATION & PERFORMANCE STAGES ──────────────────────────────────────

class CampaignAggregation(BaseModel):
    """Output of the aggregation_agent node — full pipeline consolidation."""
    campaign_id:       str
    machine_brief:     Optional[dict]     = None
    strategy:          Optional[dict]     = None
    selected_concept:  Optional[KVConcept] = None
    channel_contents:  list[ChannelContent]  = Field(default_factory=list)
    execution_results: list[ExecutionResult] = Field(default_factory=list)
    summary:           str                   = ""


class KPIActual(BaseModel):
    kpi:      str
    target:   str
    actual:   str = "pending"
    variance: str = "pending"
    status:   str = "pending"


class PerformanceReport(BaseModel):
    """Output of the performance_agent node."""
    campaign_id:     str
    kpi_actuals:     list[KPIActual] = Field(default_factory=list)
    overall_status:  str             = "pending"
    insights:        list[str]       = Field(default_factory=list)
    recommendations: list[str]       = Field(default_factory=list)
    next_steps:      str             = ""
