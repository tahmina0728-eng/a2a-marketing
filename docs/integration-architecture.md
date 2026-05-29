# CampaignOS — Integration Architecture & Implementation Plan

> **Document scope:** A deep architectural analysis and implementation blueprint for extending the existing ADK 2.0 `rebuild/` pipeline with five external integration layers: CRM (Salesforce / HubSpot), CDP (pgvector + Customer Personality Analysis), DAM (Marqo / ABO datasets), Adspirer mock execution engine, and the MCP protocol bridges that unify them all.

---

## Table of Contents

1. [Strategic Intent](#1-strategic-intent)
2. [Current Pipeline Baseline](#2-current-pipeline-baseline)
3. [Integration Layer Map](#3-integration-layer-map)
4. [Layer 1 — CRM Integration (Salesforce + HubSpot)](#4-layer-1--crm-integration-salesforce--hubspot)
5. [Layer 2 — CDP Integration (pgvector + Customer Personality Analysis)](#5-layer-2--cdp-integration-pgvector--customer-personality-analysis)
6. [Layer 3 — DAM Integration (Marqo / ABO)](#6-layer-3--dam-integration-marqo--abo)
7. [Layer 4 — pgvector Semantic Engine (Cross-Cutting)](#7-layer-4--pgvector-semantic-engine-cross-cutting)
8. [Layer 5 — Adspirer Mock Execution Engine](#8-layer-5--adspirer-mock-execution-engine)
9. [MCP Protocol Bridges](#9-mcp-protocol-bridges)
10. [Database Architecture](#10-database-architecture)
11. [ADK 2.0 Pipeline Integration Points](#11-adk-20-pipeline-integration-points)
12. [New Agent Definitions Required](#12-new-agent-definitions-required)
13. [New Tool Definitions Required](#13-new-tool-definitions-required)
14. [New Node Definitions Required](#14-new-node-definitions-required)
15. [Updated Pydantic Models](#15-updated-pydantic-models)
16. [Docker Infrastructure](#16-docker-infrastructure)
17. [Dataset Seeding Strategy](#17-dataset-seeding-strategy)
18. [Frontend UI Extensions](#18-frontend-ui-extensions)
19. [Implementation Phases & Sequencing](#19-implementation-phases--sequencing)
20. [Testing & Verification Strategy](#20-testing--verification-strategy)
21. [Demo Narrative & Presentation Flow](#21-demo-narrative--presentation-flow)
22. [Security & Compliance Considerations](#22-security--compliance-considerations)

---

## 1. Strategic Intent

The existing pipeline is an **isolated creative factory**: it ingests a raw campaign brief typed into a UI, generates strategy, produces four key visuals in parallel, routes to channels, and stubs out deployment. It proves the agentic orchestration concept but does not demonstrate **enterprise integration depth**.

The integrations described in the attached files transform CampaignOS from a standalone tool into what the attached notes correctly call:

> **A Semantic Operating Layer for Marketing**

The architectural thesis is that enterprise marketing operations already have data everywhere — objectives in CRM, audience intelligence in CDPs, approved creative assets in DAMs — but no connective tissue that lets an AI understand and act across all three simultaneously. pgvector becomes that connective tissue: a **semantic bridge** where every data source deposits its knowledge as a queryable embedding, and the ADK agents retrieve exactly the right context at the right pipeline stage using natural language.

The five integration layers correspond directly to the five stages of an enterprise campaign lifecycle:

| Stage | Integration | Role in CampaignOS |
|---|---|---|
| **Define** | CRM (Salesforce / HubSpot) | Campaign objectives, budget, product focus enter from existing records — not typed by hand |
| **Understand** | CDP (pgvector + Customer Personality) | Audience intelligence derived from real first-party-style data enriches the brief |
| **Source** | DAM (Marqo / ABO datasets) | Approved product imagery retrieved semantically, not searched manually |
| **Connect** | pgvector semantic engine | Unified retrieval layer stitching all three sources together for every agent |
| **Execute** | Adspirer mock | Campaign structures deployed to ad platforms in paused state, awaiting HITL sign-off |

---

## 2. Current Pipeline Baseline

Before extending, it is essential to understand exactly what the current pipeline does and where the integration attach points are.

### 2.1 Execution Graph (current)

```
load_brand_context  [FunctionNode — no LLM]
        │
        │  → loads brand guidelines from local/GCS
        │  → queries Vertex AI Search for benchmarks
        │  → builds product image map
        │
briefing_agent  [LlmAgent]
        │
hitl_brief_approval  [HITL gate]
        │
strategy_agent  [LlmAgent]
        │
    ┌───┴───┐ (fan-out)
   [kv_generator_1..4]
        │
   [kv_image_agent_1..4]     — Gemini text-to-image
        │
   [copy_renderer_agent_1..4] — Pillow text overlay
        │
   [kv_swap_agent_1..4]       — Nano Banana 2 img-to-img
        │
    └───┬───┘ (fan-in via aggregate_kv_concepts FunctionNode)
        │
kv_ranker  [LlmAgent]
        │
hitl_kv_selection  [HITL gate]
        │
channel_router  [LlmAgent]
        │
content_agent  [LlmAgent]
        │
execution_agent  [LlmAgent — stub]
        │
aggregation_agent  [LlmAgent]
        │
performance_agent  [LlmAgent]
```

### 2.2 Key State Objects in Session

The pipeline communicates via session state keys. The integration layers need to inject data **before** it is consumed by agents that currently generate it from scratch:

| State Key | Set By | Consumed By | Integration Opportunity |
|---|---|---|---|
| `machine_brief` | `briefing_agent` | `strategy_agent`, KV generators | CRM + CDP can pre-populate fields |
| `brand_guidelines` | `load_brand_context` | All downstream agents | DAM can add resolved asset URLs |
| `product_images` | `load_brand_context` | `kv_image_agent_1..4` | DAM retrieval replaces static paths |
| `kv_concepts_all` | `aggregate_kv_concepts` | `kv_ranker` | — |
| `selected_kv` | `kv_ranker` | `channel_router` | — |
| `channel_plan` | `channel_router` | `content_agent` | Adspirer preflight validates specs |
| `execution_result` | `execution_agent` | `aggregation_agent` | Adspirer mock replaces stub |

### 2.3 Current Gaps the Integrations Fill

1. **Brief source**: currently requires a human to type objectives. CRM integration replaces this with a structured record fetch.
2. **Audience intelligence**: currently the briefing agent reasons from the brief text alone. CDP provides real segmentation data and behavioural profiles.
3. **Product assets**: currently resolved from local bucket paths or GCS URIs. DAM provides semantic search across an approved asset catalogue.
4. **Execution**: currently a stub agent that produces a placeholder. Adspirer mock produces campaign structures that mirror the real API schema.
5. **Semantic retrieval**: currently Vertex AI Search for brand guidelines only. pgvector provides cross-source semantic retrieval for audience, assets, and historical campaigns.

---

## 3. Integration Layer Map

The full integrated architecture, showing all layers and the data flows between them:

```
╔══════════════════════════════════════════════════════════════════════════╗
║                         ENTERPRISE DATA SOURCES                         ║
╠══════════════════════════════╦═══════════════════════════════════════════╣
║   CRM LAYER                  ║   DATA & ASSET LAYERS                    ║
║   ┌─────────────────┐        ║   ┌─────────────────┐                    ║
║   │   Salesforce    │        ║   │  CDP pgvector   │                    ║
║   │  Campaign Obj   │        ║   │  (Kaggle CPA    │                    ║
║   │  MCP Bridge     │        ║   │   dataset)      │                    ║
║   └────────┬────────┘        ║   └────────┬────────┘                    ║
║            │                 ║            │                              ║
║   ┌─────────────────┐        ║   ┌─────────────────┐                    ║
║   │    HubSpot      │        ║   │  DAM pgvector   │                    ║
║   │  Deals / Mktg   │        ║   │  (Marqo / ABO   │                    ║
║   │  MCP Bridge     │        ║   │   datasets)     │                    ║
║   └────────┬────────┘        ║   └────────┬────────┘                    ║
╚════════════╪═════════════════╩════════════╪══════════════════════════════╝
             │                              │
             ▼                              ▼
╔══════════════════════════════════════════════════════════════════════════╗
║                   pgvector SEMANTIC RETRIEVAL ENGINE                     ║
║   PostgreSQL + pgvector (Docker)   /   MCP Postgres Server              ║
║   ┌──────────────────────────────────────────────────────────┐          ║
║   │  customer_insights  │  dam_assets  │  brand_history  │  ...│         ║
║   └──────────────────────────────────────────────────────────┘          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                        ADK 2.0 PIPELINE                                 ║
║                                                                         ║
║  load_brand_context → [CRM fetch] → [CDP enrich] → briefing_agent       ║
║       → HITL → strategy → KV fan-out → [DAM asset pull] → ...          ║
║       → channel_router → content_agent → [Adspirer preflight]          ║
║       → execution_agent → [Adspirer deploy] → aggregation → perf       ║
╠══════════════════════════════════════════════════════════════════════════╣
║                       EXECUTION LAYER                                   ║
║   ┌─────────────────────────────────────────────────────────────┐       ║
║   │              Adspirer Mock (MockAdspirer class)             │       ║
║   │   validate_ad_requirements │ create_campaign │ upload_assets│       ║
║   └─────────────────────────────────────────────────────────────┘       ║
║        │               │                 │                              ║
║   [Google Ads]     [Meta Ads]       [TikTok Ads]   (all PAUSED)        ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 4. Layer 1 — CRM Integration (Salesforce + HubSpot)

### 4.1 Architectural Role

The CRM is the **canonical source of marketing intent**. In a real enterprise, a campaign does not originate from a blank text input — it originates from a planned campaign record in the CRM system that has already been through budget approval, product team alignment, and objective setting. By pulling from CRM at pipeline start, we:

- Remove manual re-entry of campaign metadata
- Ensure the AI-generated brief is traceable back to an approved business record
- Allow the enterprise to control what campaigns are permitted to run
- Demonstrate that the pipeline is an **extension** of existing workflows, not a replacement

### 4.2 Data Model: The CRM Campaign Object

Whether using Salesforce or HubSpot, the following canonical fields must be extracted to seed a `BriefRequest`:

| CRM Field | Maps To | Type |
|---|---|---|
| `Campaign Name` | `campaign_name` | string |
| `Product_Focus__c` | `product` | string |
| `Target_Segment__c` | `target_audience` description | string |
| `Channel_Format__c` | `channels` | list[string] |
| `Budget__c` | `budget_range` | string |
| `Campaign_Objective__c` | `objective` | string |
| `Brand__c` | `brand` | string |
| `Market__c` | `market` | string |
| `Status` | filter to `Planned` | — |

### 4.3 Salesforce MCP Bridge Implementation

The Salesforce MCP server uses Salesforce DX SOQL queries. The tool wrapper sits in `app/tools.py`:

```python
# app/tools.py — new tool

from google.adk.tools import tool
from app.models import BriefRequest
from app.config import settings

@tool
async def crm_fetch_campaign_objective(
    campaign_status: str,
    tool_context
) -> dict:
    """
    Fetch planned campaign records from Salesforce CRM.
    Returns a list of campaign records formatted as BriefRequest fields.
    
    Args:
        campaign_status: Filter campaigns by this status (e.g. 'Planned', 'Active')
    """
    # In production: call Salesforce MCP endpoint
    # mcp_client.callTool("Salesforce-DX.query", {...})
    
    # Mock implementation:
    return {
        "campaigns": [
            {
                "campaign_id": "CMP_SF_001",
                "campaign_name": "2026_Q3_Maille_Premium_Reengagement",
                "brand": "Maille",
                "product": "Maille Dijon Originale & Maille Old Style Mustard",
                "objective": "Re-engage lapsed premium buyers with a 9:16 vertical video campaign emphasising culinary craftsmanship",
                "target_audience": "Premium Spenders — high-income urban households, digital-first, aged 35-55, interest in premium food and cooking",
                "channels": ["Instagram Stories", "TikTok", "Pinterest"],
                "budget_range": "£50,000–£80,000",
                "market": "UK",
                "source_crm": "salesforce",
                "status": campaign_status
            }
        ]
    }
```

### 4.4 HubSpot MCP Bridge Implementation

HubSpot provides a remote MCP server at `mcp.hubspot.com`. The tool wrapper provides the same interface with a different underlying query:

```python
@tool
async def crm_fetch_hubspot_deal(
    pipeline_stage: str,
    tool_context
) -> dict:
    """
    Fetch marketing campaign deals from HubSpot CRM.
    Equivalent output schema to crm_fetch_campaign_objective for pipeline compatibility.
    
    Args:
        pipeline_stage: HubSpot pipeline stage to filter by
    """
    # In production: call HubSpot MCP server
    # mcp.hubspot.com → search_deals tool
    
    # Mock implementation with identical output schema:
    return {
        "campaigns": [
            {
                "campaign_id": "CMP_HS_001",
                "campaign_name": "Paula's Choice Summer Ritual Campaign",
                "brand": "PaulasChoice",
                "product": "Paula's Choice RESIST Anti-Aging Serum",
                "objective": "Drive first-purchase conversion among new-to-brand skincare enthusiasts via carousel and story formats",
                "target_audience": "Skincare enthusiasts — digitally native, female skew, aged 28-45, interested in active ingredients and clinical skincare",
                "channels": ["Instagram", "Facebook", "Pinterest"],
                "budget_range": "£30,000–£50,000",
                "market": "UK",
                "source_crm": "hubspot",
                "status": pipeline_stage
            }
        ]
    }
```

### 4.5 CRM Abstraction Layer

The frontend toggle (Salesforce / HubSpot) routes to a common abstraction:

```python
# app/tools.py

@tool
async def get_crm_objective(
    crm_provider: str,
    record_id: str,
    tool_context
) -> dict:
    """
    Unified CRM gateway. Routes to the appropriate MCP bridge
    based on the crm_provider selection from the UI.
    
    Args:
        crm_provider: 'salesforce' or 'hubspot'
        record_id: The CRM record ID to fetch
    """
    if crm_provider.lower() == "salesforce":
        return await crm_fetch_campaign_objective("Planned", tool_context)
    elif crm_provider.lower() == "hubspot":
        return await crm_fetch_hubspot_deal("Proposal", tool_context)
    else:
        raise ValueError(f"Unknown CRM provider: {crm_provider}")
```

### 4.6 New Pipeline Node: `load_crm_context`

This becomes the **new first node** in the pipeline, replacing the manual brief input path when `crm_mode` is enabled:

```python
# app/nodes.py — new function node

async def load_crm_context(node_input, tool_context):
    """
    FunctionNode: Fetches campaign objectives from configured CRM.
    When crm_mode is enabled, this node fires before load_brand_context
    and populates the brief fields from a CRM record, so the user only
    needs to select a campaign from a dropdown rather than typing a brief.
    """
    state = tool_context.state
    crm_provider = state.get("crm_provider", "none")
    
    if crm_provider == "none":
        # Manual brief mode — pass through unchanged
        return node_input
    
    record_id = state.get("crm_record_id")
    crm_data = await get_crm_objective(crm_provider, record_id, tool_context)
    
    if not crm_data.get("campaigns"):
        raise ValueError("CRM returned no campaign records")
    
    campaign = crm_data["campaigns"][0]
    
    # Inject into session state as a pre-formed brief
    state["crm_brief"] = campaign
    state["brand"] = campaign["brand"]
    
    # Build a BriefRequest-compatible dict from the CRM record
    brief_from_crm = {
        "brand": campaign["brand"],
        "product": campaign["product"],
        "objective": campaign["objective"],
        "target_audience": campaign["target_audience"],
        "channels": campaign["channels"],
        "budget_range": campaign["budget_range"],
        "market": campaign["market"],
        "campaign_name": campaign["campaign_name"],
        "crm_source": campaign["source_crm"],
        "crm_record_id": campaign["campaign_id"]
    }
    
    state["brief"] = brief_from_crm
    return brief_from_crm
```

### 4.7 Updated Pipeline DAG (with CRM)

```
load_crm_context   ← NEW — fetches objectives from Salesforce or HubSpot
        │
load_brand_context  ← existing — brand guidelines, benchmarks, product images
        │
enrich_brief_with_cdp  ← NEW — audience intelligence from pgvector CDP
        │
briefing_agent
        │
        ... (rest unchanged)
```

---

## 5. Layer 2 — CDP Integration (pgvector + Customer Personality Analysis)

### 5.1 Architectural Role

The CDP layer is the **audience intelligence engine**. The Customer Personality Analysis dataset (Kaggle: `imakash3011/customer-personality-analysis`) provides 2,240 customer records with 29 features spanning demographics, spending, channel preferences, and campaign response history. 

The critical insight from the attached notes is that raw numbers are not useful for a semantic retrieval agent. The seeding strategy must **translate quantitative state into qualitative sentiment**: a customer with `Income=$92,000, MntWines=$720` becomes a vector-indexed paragraph:

> *"VIP customer contact log updated. Strong affinity for reserve selections and vintage allocations. Customer registered intense dissatisfaction via phone regarding a persistent UI crash during checkout on premium product drops. Threatening to abandon loyalty program due to app bugs."*

This means an agent searching for *"high-value churn risk"* finds semantically relevant rows rather than doing expensive SQL arithmetic, while the structured columns remain available for relational filtering.

### 5.2 CDP Database Schema

```sql
-- Extension and schema setup
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE customer_insights (
    id                  INT PRIMARY KEY,
    
    -- Raw demographic columns (from Kaggle CSV)
    year_birth          INT,
    education           VARCHAR(50),
    marital_status      VARCHAR(30),
    income              NUMERIC(10,2),
    kidhome             INT,
    teenhome            INT,
    dt_customer         DATE,
    recency             INT,           -- Days since last purchase
    complain            INT,           -- 0/1 complaint flag
    
    -- Spending columns
    mnt_wines           NUMERIC(8,2),
    mnt_fruits          NUMERIC(8,2),
    mnt_meat_products   NUMERIC(8,2),
    mnt_fish_products   NUMERIC(8,2),
    mnt_sweet_products  NUMERIC(8,2),
    mnt_gold_prods      NUMERIC(8,2),
    
    -- Channel preferences
    num_web_purchases       INT,
    num_catalog_purchases   INT,
    num_store_purchases     INT,
    num_web_visits_month    INT,
    num_deals_purchases     INT,
    
    -- Campaign response history (binary flags)
    accepted_cmp1       INT,
    accepted_cmp2       INT,
    accepted_cmp3       INT,
    accepted_cmp4       INT,
    accepted_cmp5       INT,
    response            INT,           -- Response to last campaign
    
    -- Derived / enrichment columns
    age                 INT GENERATED ALWAYS AS (EXTRACT(YEAR FROM CURRENT_DATE) - year_birth) STORED,
    total_spend         NUMERIC(10,2) GENERATED ALWAYS AS (
                            mnt_wines + mnt_fruits + mnt_meat_products +
                            mnt_fish_products + mnt_sweet_products + mnt_gold_prods
                        ) STORED,
    total_campaign_responses INT GENERATED ALWAYS AS (
                            accepted_cmp1 + accepted_cmp2 + accepted_cmp3 +
                            accepted_cmp4 + accepted_cmp5
                        ) STORED,
    
    -- Semantic enrichment (the pgvector payload)
    customer_notes      TEXT,           -- Generated CRM-style narrative
    segment_label       VARCHAR(100),   -- e.g. "Premium Wine Buyer", "Deal Seeker"
    value_tier          VARCHAR(20),    -- 'HIGH', 'MID', 'LOW'
    lifestyle_archetype VARCHAR(50),    -- 'DINK', 'FAMILY', 'SENIOR_SOLO', 'TEEN_HOUSEHOLD'
    primary_friction    VARCHAR(100),   -- Generated friction scenario
    
    -- Vector column (all-MiniLM-L6-v2, 384-dimensional)
    embedding           vector(384)
);

-- HNSW index for fast approximate nearest neighbour search
CREATE INDEX cdp_hnsw_idx 
    ON customer_insights 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Partial index for high-value segment queries
CREATE INDEX cdp_high_value_idx 
    ON customer_insights (income, total_spend) 
    WHERE value_tier = 'HIGH';

-- Segment summary view (used by CDP tools without per-row embedding cost)
CREATE VIEW cdp_segment_summary AS
SELECT
    segment_label,
    value_tier,
    lifestyle_archetype,
    COUNT(*)                            AS segment_size,
    ROUND(AVG(income), 0)               AS avg_income,
    ROUND(AVG(total_spend), 0)          AS avg_total_spend,
    ROUND(AVG(mnt_wines), 0)            AS avg_wine_spend,
    ROUND(AVG(mnt_gold_prods), 0)       AS avg_luxury_spend,
    ROUND(AVG(num_web_purchases), 1)    AS avg_web_purchases,
    ROUND(AVG(total_campaign_responses), 2) AS avg_campaign_response_rate,
    ROUND(AVG(recency), 0)              AS avg_recency_days
FROM customer_insights
GROUP BY segment_label, value_tier, lifestyle_archetype;
```

### 5.3 Seeding Strategy: Deterministic CRM Note Generation

The note generation engine translates raw numbers into semantically rich text using a deterministic rule system. This is critical: the vocabulary must scale with the actual data values so that vector search is not contrived:

```python
# scripts/seed_cdp.py

import random
import pandas as pd
from sentence_transformers import SentenceTransformer
import psycopg2

MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# --- Bucket A: Value Status -----------------------------------------------
PREMIUM_INTROS = [
    "VIP customer contact log updated.",
    "Priority account review conducted.",
    "Premium tier customer flagged for retention review.",
    "High-value profile updated following account manager call.",
]
MID_INTROS = [
    "Standard account review completed.",
    "Customer profile updated following survey response.",
    "Mid-tier customer activity logged.",
    "Regular buyer profile refreshed.",
]
LOW_INTROS = [
    "Deal-segment customer note appended.",
    "Promotional-tier customer activity recorded.",
    "Value-seeking customer profile updated.",
    "Budget-conscious buyer interaction logged.",
]

# --- Bucket B: Lifestyle Archetype ----------------------------------------
DINK_NOTES = [
    "High disposable income household. No dependants. Frequently entertains at home.",
    "Dual-income couple. Strong preference for premium and artisan products.",
    "No-children household. Impulse buyer in premium food and luxury personal care.",
]
FAMILY_NOTES = [
    "Household includes young children. Shopping behaviour skewed to bulk and family-size formats.",
    "Family-oriented buyer. Strong response to bundle promotions and multi-buy offers.",
    "Parent-led household. Priority on convenience and value-for-money in grocery categories.",
]
SENIOR_SOLO_NOTES = [
    "Single-person household. Established brand loyalist. Resistant to switching.",
    "Solo lifestyle customer. Regular catalog buyer. Prefers premium single-serve formats.",
    "Mature single customer. High brand loyalty index. Infrequent but high-value purchases.",
]
TEEN_HOUSEHOLD_NOTES = [
    "Household with teenagers. High-volume consumption. Digital-first purchasing behaviour.",
    "Teen-household profile. Heavy web shopper. Responsive to social media promotions.",
    "Older-children household. Budget-conscious but responsive to digital deals.",
]

# --- Bucket C: Friction Scenarios (per value tier) -------------------------
PREMIUM_FRICTION = [
    "Customer registered intense dissatisfaction via phone regarding a persistent UI crash during checkout on premium product drops. Threatening to abandon loyalty program due to app bugs.",
    "Account holder logged formal complaint after premium product launch page failed to load during exclusive early-access window. Expressed frustration with digital reliability.",
    "VIP customer escalated a case after repeat failures to apply loyalty points at checkout on the web platform. Expressed intent to switch to competitor if issue not resolved.",
    "Senior customer contact noted a broken 'save for later' feature preventing wishlist management. Rated digital experience 1/5 in post-interaction survey.",
    "Premium buyer noted that personalised product recommendations on the app are irrelevant and repetitive. Requested to be removed from automated push notification campaign.",
]
MID_FRICTION = [
    "Customer noted slow delivery on last three catalog orders. Expressed preference for faster shipping options.",
    "Mid-tier buyer commented that promotional emails arrive after in-store deals have expired. Timing mismatch frustration noted.",
    "Customer noted that the mobile app loyalty card scanner does not work reliably in-store. Switched to manual barcode entry.",
]
LOW_FRICTION = [
    "Deal-seeking customer noted that discount codes frequently expire before cart checkout is completed.",
    "Budget buyer expressed frustration that flash sales are not signposted clearly enough on the homepage.",
    "Promotional customer noted that bundle deal messaging is inconsistent between email and website.",
]

# --- Brand affinity notes (category-specific vocabulary) -------------------
def wine_affinity_note(income, mnt_wines):
    if income > 80000 and mnt_wines > 500:
        return "Strong affinity for reserve selections and vintage allocations."
    elif mnt_wines > 200:
        return "Regular wine buyer. Responds to curated recommendations and seasonal promotions."
    return "Occasional wine purchaser. Price-sensitive in this category."

def luxury_affinity_note(mnt_gold):
    if mnt_gold > 100:
        return "Active luxury and gold-tier product purchaser. Responds to premium positioning."
    return "Limited luxury category engagement."

def channel_preference_note(num_web, num_catalog, num_store):
    if num_web > num_catalog and num_web > num_store:
        return "Predominantly digital-channel buyer. High web purchase frequency."
    elif num_catalog > num_web:
        return "Strong catalog affinity. Prefers curated printed communications over digital."
    return "Omnichannel buyer. Balanced spend across web, catalog, and in-store."

# --- Main note assembly function -------------------------------------------
def generate_crm_note(row):
    income = row.get("Income", 0) or 0
    mnt_wines = row.get("MntWines", 0) or 0
    mnt_gold = row.get("MntGoldProds", 0) or 0
    num_web = row.get("NumWebPurchases", 0) or 0
    num_catalog = row.get("NumCatalogPurchases", 0) or 0
    num_store = row.get("NumStorePurchases", 0) or 0
    num_deals = row.get("NumDealsPurchases", 0) or 0
    kidhome = row.get("Kidhome", 0) or 0
    teenhome = row.get("Teenhome", 0) or 0
    total_spend = (
        mnt_wines + row.get("MntFruits", 0) + row.get("MntMeatProducts", 0) +
        row.get("MntFishProducts", 0) + row.get("MntSweetProducts", 0) + mnt_gold
    )

    # Value tier
    if income > 80000 or total_spend > 1000:
        value_tier = "HIGH"
        intro = random.choice(PREMIUM_INTROS)
        friction = random.choice(PREMIUM_FRICTION)
    elif income > 50000 or total_spend > 400:
        value_tier = "MID"
        intro = random.choice(MID_INTROS)
        friction = random.choice(MID_FRICTION)
    else:
        value_tier = "LOW"
        intro = random.choice(LOW_INTROS)
        friction = random.choice(LOW_FRICTION)

    # Lifestyle archetype
    if kidhome == 0 and teenhome == 0:
        if income > 60000:
            archetype = "DINK"
            lifestyle = random.choice(DINK_NOTES)
        else:
            archetype = "SENIOR_SOLO"
            lifestyle = random.choice(SENIOR_SOLO_NOTES)
    elif teenhome > 0:
        archetype = "TEEN_HOUSEHOLD"
        lifestyle = random.choice(TEEN_HOUSEHOLD_NOTES)
    else:
        archetype = "FAMILY"
        lifestyle = random.choice(FAMILY_NOTES)

    # Compose note
    notes = [
        intro,
        lifestyle,
        wine_affinity_note(income, mnt_wines),
        luxury_affinity_note(mnt_gold),
        channel_preference_note(num_web, num_catalog, num_store),
        friction,
    ]
    return " ".join(notes), value_tier, archetype


def seed_cdp(csv_path: str, conn_str: str):
    df = pd.read_csv(csv_path, sep="\t")  # Kaggle CPA uses tab delimiter
    df = df.dropna(subset=["Income"])     # Remove rows with missing income
    
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    notes_batch = []
    for _, row in df.iterrows():
        note, value_tier, archetype = generate_crm_note(row)
        notes_batch.append(note)
    
    # Batch encode all notes (efficient GPU/CPU batching)
    print(f"Encoding {len(notes_batch)} customer notes...")
    embeddings = MODEL.encode(notes_batch, batch_size=64, show_progress_bar=True)
    
    for i, (_, row) in enumerate(df.iterrows()):
        note = notes_batch[i]
        _, value_tier, archetype = generate_crm_note(row)
        emb = embeddings[i].tolist()
        
        cur.execute("""
            INSERT INTO customer_insights (
                id, year_birth, education, marital_status, income,
                kidhome, teenhome, recency, complain,
                mnt_wines, mnt_fruits, mnt_meat_products,
                mnt_fish_products, mnt_sweet_products, mnt_gold_prods,
                num_web_purchases, num_catalog_purchases, num_store_purchases,
                num_web_visits_month, num_deals_purchases,
                accepted_cmp1, accepted_cmp2, accepted_cmp3, accepted_cmp4, accepted_cmp5,
                response, customer_notes, value_tier, lifestyle_archetype, embedding
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
        """, (
            row["ID"], row["Year_Birth"], row["Education"], row["Marital_Status"], row["Income"],
            row["Kidhome"], row["Teenhome"], row["Recency"], row["Complain"],
            row["MntWines"], row["MntFruits"], row["MntMeatProducts"],
            row["MntFishProducts"], row["MntSweetProducts"], row["MntGoldProds"],
            row["NumWebPurchases"], row["NumCatalogPurchases"], row["NumStorePurchases"],
            row["NumWebVisitsMonth"], row["NumDealsPurchases"],
            row["AcceptedCmp1"], row["AcceptedCmp2"], row["AcceptedCmp3"],
            row["AcceptedCmp4"], row["AcceptedCmp5"],
            row["Response"], note, value_tier, archetype, emb
        ))
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"Seeded {len(df)} customer records into CDP.")
```

### 5.4 CDP Tool: Audience Semantic Search

```python
# app/tools.py — CDP retrieval tool

@tool
async def cdp_get_audience_insights(
    audience_description: str,
    top_k: int,
    tool_context
) -> dict:
    """
    Semantic search across the CDP customer profiles using pgvector.
    Returns audience segment intelligence to enrich the campaign brief.
    
    Args:
        audience_description: Natural language description of the target audience
        top_k: Number of matching profiles to return (default 5)
    """
    from app.vector_client import VectorClient
    
    vc = VectorClient()
    results = await vc.semantic_search_cdp(audience_description, top_k=top_k or 5)
    
    # Aggregate into a segment profile
    if not results:
        return {"segment_profile": None, "message": "No matching audience profiles found"}
    
    avg_income = sum(r["income"] for r in results) / len(results)
    avg_spend = sum(r["total_spend"] for r in results) / len(results)
    value_tiers = [r["value_tier"] for r in results]
    archetypes = [r["lifestyle_archetype"] for r in results]
    notes = [r["customer_notes"] for r in results]
    
    dominant_tier = max(set(value_tiers), key=value_tiers.count)
    dominant_archetype = max(set(archetypes), key=archetypes.count)
    
    return {
        "segment_profile": {
            "segment_id": f"pgvector_match_{audience_description[:30].replace(' ', '_')}",
            "summary": f"Cluster of {len(results)} matched profiles. Dominant tier: {dominant_tier}. Archetype: {dominant_archetype}.",
            "attributes": {
                "avg_income": round(avg_income, 0),
                "avg_total_spend": round(avg_spend, 0),
                "dominant_value_tier": dominant_tier,
                "dominant_lifestyle": dominant_archetype,
                "engagement": "high" if dominant_tier == "HIGH" else "medium"
            },
            "qualitative_signals": notes[:3],  # Top 3 most relevant narratives
            "pgvector_match_count": len(results)
        }
    }
```

### 5.5 CDP Enrichment of the Brief

The `enrich_brief_with_cdp` function node runs after CRM fetch and before `briefing_agent`. It queries the CDP using the `target_audience` description from the CRM record and appends audience intelligence to the session state as `audience_insights`:

```python
async def enrich_brief_with_cdp(node_input, tool_context):
    """
    FunctionNode: Enriches the brief with CDP audience intelligence.
    Uses the target_audience field from the brief (populated by CRM or manually)
    to perform a semantic pgvector search and retrieve behavioural profiles.
    """
    state = tool_context.state
    brief = state.get("brief", {})
    target_audience = brief.get("target_audience", "")
    
    if not target_audience:
        return node_input
    
    audience_data = await cdp_get_audience_insights(target_audience, top_k=5, tool_context=tool_context)
    
    if audience_data.get("segment_profile"):
        state["audience_insights"] = audience_data["segment_profile"]
        # Inject into brief so briefing_agent sees it
        brief["cdp_audience_insights"] = audience_data["segment_profile"]
        state["brief"] = brief
    
    return node_input
```

---

## 6. Layer 3 — DAM Integration (Marqo / ABO)

### 6.1 Architectural Role

The DAM layer is the **creative asset repository**. Rather than generating backgrounds entirely from scratch with Gemini, the KV image agents should first check whether an approved product asset already exists that matches the creative direction. This:

- Grounds generated visuals in real product photography
- Reflects how a real brand team operates (brand-approved assets are mandatory)
- Makes the demo visually compelling: retrieved product shots appear directly in the pipeline UI

### 6.2 Dataset Choice: Marqo/amazon-products-eval

The attached notes recommend **Marqo/amazon-products-eval** (Apache 2.0 license) over the Amazon Berkeley Objects dataset. The 100k subset (`Marqo/amazon-products-eval-100k`) provides:

- Live CDN-hosted image URLs (no local storage required)
- Rich text descriptions suitable for semantic embedding
- Product categories covering skincare, food, and personal care (aligning to Unilever mapping)
- Structured metadata (title, category, bullet points)

### 6.3 DAM Database Schema

```sql
CREATE TABLE dam_assets (
    asset_id            VARCHAR(50) PRIMARY KEY,
    
    -- Asset metadata
    brand_division      VARCHAR(100),    -- e.g. 'Knorr/Maille', 'PaulasChoice', 'Dove'
    asset_type          VARCHAR(50),     -- 'product_shot', 'lifestyle', 'logo', 'texture'
    image_url           TEXT NOT NULL,   -- Live CDN URL (no local storage needed)
    title               TEXT,
    category            VARCHAR(100),
    
    -- Rich description assembled from dataset fields
    description         TEXT,           -- Combined title + bullet points for embedding
    
    -- Brand mapping metadata
    mapped_brand        VARCHAR(100),   -- Unilever brand mapped from category
    mapped_division     VARCHAR(50),    -- 'Nutrition', 'BeautyWellbeing', 'PersonalCare'
    visual_attributes   TEXT,           -- e.g. 'white background, clean, clinical, dropper bottle'
    
    -- Vector column (384-dim, same model as CDP for cross-table queries)
    description_embedding vector(384)
);

-- HNSW index for semantic asset search
CREATE INDEX dam_hnsw_idx
    ON dam_assets
    USING hnsw (description_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Category filter index
CREATE INDEX dam_category_idx ON dam_assets (category, mapped_brand);
```

### 6.4 Asset Seeding from Marqo Dataset

```python
# scripts/seed_dam.py

from datasets import load_dataset
import psycopg2
from sentence_transformers import SentenceTransformer

MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# Heuristic category → Unilever brand mapping
CATEGORY_BRAND_MAP = {
    "skin care": ("PaulasChoice", "BeautyWellbeing"),
    "face serum": ("PaulasChoice", "BeautyWellbeing"),
    "body lotion": ("Dove", "PersonalCare"),
    "body wash": ("Dove", "PersonalCare"),
    "condiment": ("Maille", "Nutrition"),
    "mustard": ("Maille", "Nutrition"),
    "sauce": ("Knorr", "Nutrition"),
    "soup": ("Knorr", "Nutrition"),
    "hair care": ("TRESemmé", "PersonalCare"),
    "shampoo": ("TRESemmé", "PersonalCare"),
    "deodorant": ("Lynx", "PersonalCare"),
    "fragrance": ("Lynx", "PersonalCare"),
}

def infer_brand(title: str, category: str):
    text = (title + " " + category).lower()
    for keyword, (brand, division) in CATEGORY_BRAND_MAP.items():
        if keyword in text:
            return brand, division
    return "Unilever", "General"

def build_description(item: dict) -> str:
    parts = [item.get("title", "")]
    bullets = item.get("bullet_point", [])
    if isinstance(bullets, list):
        parts.extend(bullets[:3])
    elif isinstance(bullets, str):
        parts.append(bullets)
    return " ".join(filter(None, parts))

def seed_dam(conn_str: str, limit: int = 500):
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    print("Streaming Marqo 100k dataset from Hugging Face...")
    dataset = load_dataset(
        "Marqo/amazon-products-eval-100k",
        split="train",
        streaming=True
    )
    
    records = []
    for item in dataset:
        image_url = item.get("image_url") or item.get("main_image_url")
        if not image_url:
            continue
        
        description = build_description(item)
        if len(description) < 20:
            continue
        
        brand, division = infer_brand(
            item.get("title", ""),
            item.get("product_type", "")
        )
        
        records.append({
            "asset_id": item.get("item_id", f"MARQO_{len(records)}"),
            "brand_division": brand,
            "asset_type": "product_shot",
            "image_url": image_url,
            "title": item.get("title", ""),
            "category": item.get("product_type", ""),
            "description": description,
            "mapped_brand": brand,
            "mapped_division": division,
            "visual_attributes": "product photography, ecommerce, clean background"
        })
        
        if len(records) >= limit:
            break
    
    print(f"Encoding {len(records)} asset descriptions...")
    descriptions = [r["description"] for r in records]
    embeddings = MODEL.encode(descriptions, batch_size=64, show_progress_bar=True)
    
    for rec, emb in zip(records, embeddings):
        cur.execute("""
            INSERT INTO dam_assets (
                asset_id, brand_division, asset_type, image_url,
                title, category, description, mapped_brand,
                mapped_division, visual_attributes, description_embedding
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (asset_id) DO NOTHING
        """, (
            rec["asset_id"], rec["brand_division"], rec["asset_type"],
            rec["image_url"], rec["title"], rec["category"],
            rec["description"], rec["mapped_brand"], rec["mapped_division"],
            rec["visual_attributes"], emb.tolist()
        ))
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"Seeded {len(records)} DAM assets.")
```

### 6.5 DAM Tool: Semantic Asset Search

```python
# app/tools.py — DAM retrieval tool

@tool
async def dam_search_brand_assets(
    creative_direction: str,
    brand: str,
    top_k: int,
    tool_context
) -> dict:
    """
    Semantic search across the DAM using pgvector to find the most
    visually relevant product assets for a given creative direction.
    
    Args:
        creative_direction: Natural language description of the visual style needed
        brand: Brand name to filter assets by (e.g. 'PaulasChoice', 'Maille')
        top_k: Number of assets to return
    """
    from app.vector_client import VectorClient
    
    vc = VectorClient()
    results = await vc.semantic_search_dam(
        creative_direction,
        brand_filter=brand,
        top_k=top_k or 3
    )
    
    if not results:
        return {"assets": [], "message": f"No matching assets found for brand '{brand}'"}
    
    return {
        "assets": [
            {
                "asset_id": r["asset_id"],
                "title": r["title"],
                "image_url": r["image_url"],
                "visual_attributes": r["visual_attributes"],
                "brand": r["mapped_brand"],
                "similarity_score": round(1 - r["distance"], 3)
            }
            for r in results
        ],
        "retrieval_query": creative_direction,
        "brand_filter": brand
    }
```

---

## 7. Layer 4 — pgvector Semantic Engine (Cross-Cutting)

### 7.1 Architectural Role

pgvector is not just a database — it is the **semantic backbone** that makes every other integration layer coherent. All three external data sources (CRM context, CDP profiles, DAM assets) converge in a single PostgreSQL instance running pgvector. This means:

- A single Docker container serves all semantic retrieval needs
- The embedding model is consistent across tables (all use `all-MiniLM-L6-v2`, 384 dimensions)
- Cross-table queries are possible (e.g. find audience profiles AND matching assets in a single SQL join)
- The Postgres MCP server exposes this entire knowledge base to every ADK agent as a tool

### 7.2 VectorClient Implementation

```python
# app/vector_client.py

import asyncio
from contextlib import asynccontextmanager
from typing import Any
import asyncpg
from sentence_transformers import SentenceTransformer
from app.config import settings


class VectorClient:
    """
    Async pgvector client. Provides semantic search methods for each
    data layer (CDP, DAM) and a cross-table hybrid search capability.
    """
    
    _pool: asyncpg.Pool | None = None
    _model: SentenceTransformer | None = None
    
    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                dsn=settings.pgvector_dsn,
                min_size=2,
                max_size=10
            )
        return cls._pool
    
    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")
        return cls._model
    
    async def _embed(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        model = self.get_model()
        embedding = await loop.run_in_executor(None, model.encode, text)
        return embedding.tolist()
    
    async def semantic_search_cdp(
        self,
        query: str,
        top_k: int = 5,
        value_tier_filter: str | None = None
    ) -> list[dict]:
        """
        Semantic search over customer_insights.
        Supports optional value_tier filter for hybrid SQL+vector queries.
        """
        pool = await self.get_pool()
        embedding = await self._embed(query)
        
        base_sql = """
            SELECT
                id,
                income,
                total_spend,
                value_tier,
                lifestyle_archetype,
                segment_label,
                customer_notes,
                mnt_wines,
                mnt_gold_prods,
                num_web_purchases,
                (embedding <=> $1::vector) AS distance
            FROM customer_insights
            {where_clause}
            ORDER BY distance ASC
            LIMIT $2
        """
        
        if value_tier_filter:
            sql = base_sql.format(where_clause="WHERE value_tier = $3")
            rows = await pool.fetch(sql, embedding, top_k, value_tier_filter)
        else:
            sql = base_sql.format(where_clause="")
            rows = await pool.fetch(sql, embedding, top_k)
        
        return [dict(r) for r in rows]
    
    async def semantic_search_dam(
        self,
        query: str,
        brand_filter: str | None = None,
        top_k: int = 3
    ) -> list[dict]:
        """
        Semantic search over dam_assets.
        Supports optional brand filter for targeted asset retrieval.
        """
        pool = await self.get_pool()
        embedding = await self._embed(query)
        
        if brand_filter:
            sql = """
                SELECT
                    asset_id, title, image_url, mapped_brand,
                    visual_attributes, category,
                    (description_embedding <=> $1::vector) AS distance
                FROM dam_assets
                WHERE mapped_brand = $3
                ORDER BY distance ASC
                LIMIT $2
            """
            rows = await pool.fetch(sql, embedding, top_k, brand_filter)
        else:
            sql = """
                SELECT
                    asset_id, title, image_url, mapped_brand,
                    visual_attributes, category,
                    (description_embedding <=> $1::vector) AS distance
                FROM dam_assets
                ORDER BY distance ASC
                LIMIT $2
            """
            rows = await pool.fetch(sql, embedding, top_k)
        
        return [dict(r) for r in rows]
    
    async def hybrid_brief_intelligence(
        self,
        audience_query: str,
        asset_query: str,
        value_tier: str = "HIGH",
        brand: str | None = None,
        top_k_audience: int = 5,
        top_k_assets: int = 3
    ) -> dict:
        """
        Cross-table intelligence retrieval: audience profiles + matching DAM assets
        in a single async batch. Used by the brief enrichment node.
        """
        audience_task = self.semantic_search_cdp(
            audience_query, top_k=top_k_audience, value_tier_filter=value_tier
        )
        asset_task = self.semantic_search_dam(
            asset_query, brand_filter=brand, top_k=top_k_assets
        )
        
        audience_results, asset_results = await asyncio.gather(audience_task, asset_task)
        
        return {
            "audience_profiles": audience_results,
            "recommended_assets": asset_results
        }
    
    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None
```

### 7.3 Config Extension for pgvector

```python
# app/config.py — additions to Settings class

class Settings(BaseSettings):
    # ... existing fields ...
    
    # pgvector / PostgreSQL
    pgvector_host: str = Field(default="localhost")
    pgvector_port: int = Field(default=5432)
    pgvector_db: str = Field(default="marketing_intelligence")
    pgvector_user: str = Field(default="mcp_user")
    pgvector_password: str = Field(default="mcp_password")
    
    @property
    def pgvector_dsn(self) -> str:
        return (
            f"postgresql://{self.pgvector_user}:{self.pgvector_password}"
            f"@{self.pgvector_host}:{self.pgvector_port}/{self.pgvector_db}"
        )
    
    # Embedding model
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_dimensions: int = Field(default=384)
```

---

## 8. Layer 5 — Adspirer Mock Execution Engine

### 8.1 Architectural Role

The Adspirer layer replaces the current `execution_agent` stub with a **realistic deployment simulation**. It performs three functions that mirror the real Adspirer MCP API:

1. **`validate_ad_requirements`** — pre-flight check: returns platform-specific character limits, aspect ratios, and technical specs so the content agent can produce compliant copy *before* rendering
2. **`create_campaign`** — stages a paused campaign structure across one or more ad networks with budget allocation, targeting configuration, and schedule metadata
3. **`upload_assets`** — binds generated creative assets (retrieved from ADK artifact service / DAM) to the staged campaign structures

The "PAUSED state" is the critical UX detail: the agent *never* publishes live. The final human review (HITL gate) happens *after* the campaign has been fully structured, which means the brand manager reviews a complete, ready-to-launch package rather than isolated creative files.

### 8.2 MockAdspirer Implementation

```python
# app/mock_adspirer.py

import uuid
import datetime
from typing import Optional

# Platform technical specifications (mirrors real Adspirer validate_ad_requirements schema)
PLATFORM_SPECS = {
    "meta": {
        "formats": {
            "story": {"aspect_ratio": "9:16", "width": 1080, "height": 1920, "max_file_size_mb": 30},
            "feed": {"aspect_ratio": "1:1", "width": 1080, "height": 1080, "max_file_size_mb": 30},
            "carousel": {"aspect_ratio": "1:1", "width": 1080, "height": 1080, "max_file_size_mb": 30},
        },
        "copy_limits": {
            "headline": 40,
            "body": 125,
            "description": 30,
            "cta": 20
        },
        "video_duration_max_s": 60,
        "supported_objectives": ["BRAND_AWARENESS", "REACH", "CONVERSIONS", "TRAFFIC"]
    },
    "google_pmax": {
        "formats": {
            "responsive_display": {"aspect_ratios": ["1.91:1", "1:1"], "min_width": 600},
        },
        "copy_limits": {
            "headline": 30,
            "long_headline": 90,
            "description": 90,
        },
        "asset_groups": {"max_headlines": 15, "max_descriptions": 4, "max_images": 20},
        "supported_objectives": ["CONVERSIONS", "STORE_VISITS", "REACH"]
    },
    "tiktok": {
        "formats": {
            "in_feed": {"aspect_ratio": "9:16", "width": 1080, "height": 1920, "max_file_size_mb": 500},
        },
        "copy_limits": {
            "ad_text": 100,
            "display_name": 25,
        },
        "video_duration_range_s": [5, 60],
        "supported_objectives": ["REACH", "VIDEO_VIEWS", "CONVERSIONS"]
    },
    "pinterest": {
        "formats": {
            "standard": {"aspect_ratio": "2:3", "width": 1000, "height": 1500},
            "video": {"aspect_ratio": "9:16", "width": 1080, "height": 1920},
        },
        "copy_limits": {
            "title": 100,
            "description": 500,
        },
        "supported_objectives": ["BRAND_AWARENESS", "VIDEO_VIEWS", "CONSIDERATION"]
    }
}

class MockAdspirer:
    """
    Mock implementation of Adspirer MCP for innovation demonstrations.
    Replicates the core Adspirer API schema with realistic structured JSON
    outputs. All campaigns are created in PAUSED state — no live spend.
    """
    
    def __init__(self):
        self._campaign_registry: dict = {}
        self._asset_registry: dict = {}
        self._audit_log: list = []
        self._session_id = str(uuid.uuid4())[:8]
    
    def _log(self, action: str, payload: dict):
        self._audit_log.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "session": self._session_id,
            "action": action,
            **payload
        })
    
    def validate_ad_requirements(self, platform: str) -> dict:
        """
        Pre-flight check: returns platform-specific specs.
        Call this BEFORE content generation so copy lengths are compliant.
        """
        platform_key = platform.lower().replace(" ", "_").replace("-", "_")
        
        if platform_key not in PLATFORM_SPECS:
            return {
                "status": "ERROR",
                "message": f"Platform '{platform}' not found in Adspirer registry",
                "supported_platforms": list(PLATFORM_SPECS.keys())
            }
        
        specs = PLATFORM_SPECS[platform_key]
        self._log("VALIDATE", {"platform": platform_key})
        
        return {
            "status": "OK",
            "platform": platform_key,
            "specifications": specs,
            "compliance_notes": [
                f"Headline must not exceed {specs['copy_limits'].get('headline', 'N/A')} characters",
                "All assets must be brand-approved before deployment",
                "Campaign will be created in PAUSED state for HITL review"
            ]
        }
    
    def create_campaign(
        self,
        campaign_name: str,
        platforms: list[str],
        budget: float,
        status: str = "PAUSED",
        objective: str = "BRAND_AWARENESS",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        Stage paused campaign structures across one or more ad networks.
        Returns a campaign_id that can be used in subsequent upload_assets calls.
        """
        campaign_id = f"cmp_{uuid.uuid4().hex[:8]}"
        start = start_date or datetime.date.today().isoformat()
        end = end_date or (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        
        platform_records = []
        for p in platforms:
            platform_key = p.lower().replace(" ", "_").replace("-", "_")
            specs = PLATFORM_SPECS.get(platform_key, {})
            platform_records.append({
                "platform": platform_key,
                "status": status,
                "network_campaign_id": f"NET_{platform_key.upper()}_{uuid.uuid4().hex[:6]}",
                "budget_allocation": round(budget / len(platforms), 2),
                "currency": "GBP",
                "objective": objective,
                "daily_budget": round((budget / len(platforms)) / 30, 2),
                "start_date": start,
                "end_date": end,
                "targeting": {
                    "locations": ["UK"],
                    "age_min": 25,
                    "age_max": 55,
                    "interests": ["Premium Food", "Skincare", "Lifestyle"]
                },
                "spec_reference": specs.get("copy_limits", {})
            })
        
        campaign_record = {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "status": status,
            "total_budget": budget,
            "currency": "GBP",
            "created_at": datetime.datetime.utcnow().isoformat(),
            "platforms": platform_records,
            "assets_bound": [],
            "hitl_gate": {
                "required": True,
                "approver_role": "Brand Manager",
                "approval_url": f"https://campaignos.internal/review/{campaign_id}"
            }
        }
        
        self._campaign_registry[campaign_id] = campaign_record
        self._log("CREATE_CAMPAIGN", {"campaign_id": campaign_id, "platforms": platforms})
        
        return campaign_record
    
    def upload_assets(
        self,
        campaign_id: str,
        platform: str,
        asset_url: str,
        copy_variants: list[str]
    ) -> dict:
        """
        Bind generated creative assets to the staged campaign structures.
        asset_url can be a GCS URI or a live CDN URL from the DAM.
        """
        if campaign_id not in self._campaign_registry:
            return {"status": "ERROR", "message": f"Campaign {campaign_id} not found"}
        
        asset_id = f"ast_{uuid.uuid4().hex[:8]}"
        asset_record = {
            "asset_id": asset_id,
            "campaign_id": campaign_id,
            "platform": platform.lower(),
            "asset_url": asset_url,
            "copy_variants": copy_variants,
            "bound_at": datetime.datetime.utcnow().isoformat(),
            "status": "PENDING_REVIEW",
            "moderation_status": "APPROVED",
            "serving_status": "PAUSED"
        }
        
        self._campaign_registry[campaign_id]["assets_bound"].append(asset_record)
        self._asset_registry[asset_id] = asset_record
        self._log("UPLOAD_ASSET", {"asset_id": asset_id, "campaign_id": campaign_id})
        
        return asset_record
    
    def get_deployment_manifest(self) -> dict:
        """
        Returns the full deployment manifest for the current session.
        Used to generate the UI summary table at demo conclusion.
        """
        return {
            "session_id": self._session_id,
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "simulation_mode": True,
            "campaigns": list(self._campaign_registry.values()),
            "total_assets_bound": len(self._asset_registry),
            "audit_log": self._audit_log
        }
```

### 8.3 Adspirer ADK Tool Wrappers

```python
# app/tools.py — Adspirer tool wrappers

from app.mock_adspirer import MockAdspirer

# Session-scoped singleton
_adspirer_client = MockAdspirer()

@tool
async def adspirer_preflight(channel: str, tool_context) -> dict:
    """
    ADK Wrapper: Query platform specs before content generation.
    Call this during channel_router stage so content_agent generates
    compliant copy lengths from the start.
    
    Args:
        channel: Platform name (e.g. 'meta', 'tiktok', 'google_pmax')
    """
    return _adspirer_client.validate_ad_requirements(channel)

@tool
async def adspirer_deploy_draft(
    campaign_name: str,
    channels: list[str],
    budget: float,
    objective: str,
    tool_context
) -> dict:
    """
    ADK Wrapper: Stage paused campaign structures across ad networks.
    All campaigns created in PAUSED state — requires HITL sign-off before live.
    
    Args:
        campaign_name: Human-readable campaign name from CRM record
        channels: List of platform targets
        budget: Total campaign budget in GBP
        objective: Campaign objective (BRAND_AWARENESS, CONVERSIONS, etc.)
    """
    return _adspirer_client.create_campaign(
        campaign_name=campaign_name,
        platforms=channels,
        budget=budget,
        status="PAUSED",
        objective=objective
    )

@tool
async def adspirer_bind_media(
    campaign_id: str,
    platform: str,
    asset_url: str,
    copy_variants: list[str],
    tool_context
) -> dict:
    """
    ADK Wrapper: Bind creative assets to the staged campaign structures.
    asset_url should be the GCS artifact URI or DAM CDN URL.
    
    Args:
        campaign_id: Campaign ID from adspirer_deploy_draft
        platform: Platform to bind this asset to
        asset_url: GCS URI or CDN URL of the creative asset
        copy_variants: List of headline/copy text variants
    """
    return _adspirer_client.upload_assets(campaign_id, platform, asset_url, copy_variants)

@tool
async def adspirer_get_manifest(tool_context) -> dict:
    """
    ADK Wrapper: Retrieve the full deployment manifest for the current session.
    Used by aggregation_agent to produce the final output summary.
    """
    return _adspirer_client.get_deployment_manifest()
```

---

## 9. MCP Protocol Bridges

### 9.1 The Role of MCP in This Architecture

Every integration layer is accessible via the **Model Context Protocol (MCP)** — a standard transport that lets ADK agents query external systems with the same tool-call interface, regardless of whether the underlying system is Salesforce, PostgreSQL, Cloudinary, or a local mock.

The unified MCP architecture means:

- No bespoke API integrations to maintain
- Any agent in the pipeline can call any tool without knowing implementation details
- Swapping from mock to production (e.g. from `MockAdspirer` to real Adspirer MCP) is a single config change
- The enterprise can demo with their own CRM record against the same codebase

### 9.2 Postgres MCP Server (CDP + DAM)

The Postgres MCP server exposes the pgvector database to any MCP-compatible client, including the ADK agents:

```yaml
# docker-compose.yml addition: Postgres MCP server
  mcp-postgres:
    image: modelcontextprotocol/postgres-mcp:latest
    environment:
      - DATABASE_URL=postgresql://mcp_user:mcp_password@postgres:5432/marketing_intelligence
    ports:
      - "3001:3001"
    depends_on:
      - postgres
    networks:
      - campaignos_net
```

ADK agents can then call the Postgres MCP tools directly:

```python
# In any agent instruction string, the agent can execute:
# mcp_postgres.query(sql="SELECT * FROM cdp_segment_summary ORDER BY avg_income DESC LIMIT 5")
# mcp_postgres.query(sql="SELECT asset_id, image_url FROM dam_assets WHERE mapped_brand = 'PaulasChoice' ORDER BY description_embedding <=> '[...]' LIMIT 3")
```

### 9.3 MCP Tool Registration in ADK

ADK 2.0 supports MCP tool integration via `MCPToolset`. Register the Postgres MCP server as a toolset available to the enrichment and execution agents:

```python
# app/agents.py — MCP toolset registration

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams

postgres_mcp_toolset = MCPToolset(
    connection_params=SseServerParams(
        url="http://localhost:3001/sse"
    )
)

# Attach to agents that need semantic retrieval
cdp_enrichment_agent = Agent(
    name="cdp_enrichment_agent",
    model=settings.gemini_model_reasoning,
    instruction=CDP_ENRICHMENT_INSTRUCTIONS,
    tools=[postgres_mcp_toolset],
    output_key="audience_insights"
)

dam_retrieval_agent = Agent(
    name="dam_retrieval_agent",
    model=settings.gemini_model_reasoning,
    instruction=DAM_RETRIEVAL_INSTRUCTIONS,
    tools=[postgres_mcp_toolset, dam_search_brand_assets],
    output_key="retrieved_dam_assets"
)
```

### 9.4 CRM MCP Configuration

For the Salesforce MCP bridge (production):

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "npx",
      "args": ["@salesforce/mcp-server", "--org-alias", "campaignos-demo"],
      "env": {
        "SALESFORCE_ACCESS_TOKEN": "${SALESFORCE_ACCESS_TOKEN}"
      }
    },
    "hubspot": {
      "url": "https://mcp.hubspot.com/mcp",
      "headers": {
        "Authorization": "Bearer ${HUBSPOT_ACCESS_TOKEN}"
      }
    }
  }
}
```

For the demo / mock mode (no live CRM credentials needed):

```python
# app/tools.py — mock mode detection
CRM_MOCK_MODE = os.getenv("CRM_MODE", "mock") == "mock"
```

---

## 10. Database Architecture

### 10.1 Shared Instance, Separate Schemas

All data layers share a single PostgreSQL instance but in logically isolated schemas. This is the recommended architecture from the attached notes: it balances realism (a real enterprise would use separate databases) with demo performance (a single Docker container, single connection pool):

```
marketing_intelligence (database)
├── public (schema)
│   ├── customer_insights          ← CDP: Kaggle Customer Personality Analysis
│   ├── dam_assets                 ← DAM: Marqo/ABO product assets
│   ├── brand_history              ← (future) historical campaign performance
│   └── cdp_segment_summary        ← materialized view of CDP segments
├── adspirer (schema)
│   ├── campaigns                  ← Adspirer mock campaign registry
│   ├── assets_bound               ← Bound creative assets per campaign
│   └── audit_log                  ← Full action audit trail
└── crm_cache (schema)
    └── campaign_records           ← Cached CRM records (TTL-based freshness)
```

### 10.2 docker-compose.yml: Full Infrastructure

```yaml
version: '3.8'

services:
  # Core PostgreSQL + pgvector
  postgres:
    image: pgvector/pgvector:pg16
    container_name: campaignos_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: marketing_intelligence
      POSTGRES_USER: mcp_user
      POSTGRES_PASSWORD: mcp_password
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8"
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/01_init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mcp_user -d marketing_intelligence"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - campaignos_net

  # Postgres MCP Server (exposes pgvector to ADK agents)
  mcp-postgres:
    image: modelcontextprotocol/postgres-mcp:latest
    container_name: campaignos_mcp_postgres
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://mcp_user:mcp_password@postgres:5432/marketing_intelligence
    ports:
      - "3001:3001"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - campaignos_net

  # CampaignOS ADK backend (from rebuild/)
  campaignos-api:
    build:
      context: ./rebuild
      dockerfile: Dockerfile
    container_name: campaignos_api
    restart: unless-stopped
    env_file:
      - rebuild/.env
    environment:
      PGVECTOR_HOST: postgres
      PGVECTOR_PORT: 5432
      PGVECTOR_DB: marketing_intelligence
      PGVECTOR_USER: mcp_user
      PGVECTOR_PASSWORD: mcp_password
      CRM_MODE: mock
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - campaignos_net

volumes:
  pgdata:
    driver: local

networks:
  campaignos_net:
    driver: bridge
```

---

## 11. ADK 2.0 Pipeline Integration Points

### 11.1 Updated Pipeline DAG

The updated `pipeline.py` with all integration nodes and agents wired in:

```python
# app/pipeline.py — updated Workflow DAG

from google.adk.agents import Agent
from google.adk.workflows import Workflow

# ... all existing imports ...

# New integration nodes
from app.nodes import (
    load_crm_context,
    enrich_brief_with_cdp,
    load_brand_context,          # existing — unchanged
    aggregate_kv_concepts,       # existing — unchanged
    inject_dam_assets,           # new — resolves DAM URLs into KV context
    build_adspirer_manifest,     # new — assembles deployment manifest
)

# New integration agents
from app.agents import (
    # ... all existing agents ...
    cdp_enrichment_agent,        # new
    dam_retrieval_agent,         # new
)

root_agent = Workflow(
    name="campaignos_full_pipeline",
    edges=[
        # === CONTEXT LOADING (new integration nodes first) ===
        ("__start__",               load_crm_context),
        (load_crm_context,          load_brand_context),
        (load_brand_context,        enrich_brief_with_cdp),
        
        # === BRIEFING (unchanged, enriched inputs) ===
        (enrich_brief_with_cdp,     briefing_agent),
        (briefing_agent,            hitl_brief_approval),
        (hitl_brief_approval,       strategy_agent),
        
        # === KV FAN-OUT (unchanged) ===
        (strategy_agent,            kv_generator_1),
        (strategy_agent,            kv_generator_2),
        (strategy_agent,            kv_generator_3),
        (strategy_agent,            kv_generator_4),
        
        # === DAM ASSET INJECTION (new — runs in parallel with KV concept gen) ===
        (strategy_agent,            dam_retrieval_agent),
        
        # === KV IMAGE PIPELINE (unchanged) ===
        (kv_generator_1,            kv_image_agent_1),
        (kv_generator_2,            kv_image_agent_2),
        (kv_generator_3,            kv_image_agent_3),
        (kv_generator_4,            kv_image_agent_4),
        (kv_image_agent_1,          copy_renderer_agent_1),
        (kv_image_agent_2,          copy_renderer_agent_2),
        (kv_image_agent_3,          copy_renderer_agent_3),
        (kv_image_agent_4,          copy_renderer_agent_4),
        (copy_renderer_agent_1,     kv_swap_agent_1),
        (copy_renderer_agent_2,     kv_swap_agent_2),
        (copy_renderer_agent_3,     kv_swap_agent_3),
        (copy_renderer_agent_4,     kv_swap_agent_4),
        
        # === FAN-IN (unchanged) ===
        (kv_swap_agent_1,           aggregate_kv_concepts),
        (kv_swap_agent_2,           aggregate_kv_concepts),
        (kv_swap_agent_3,           aggregate_kv_concepts),
        (kv_swap_agent_4,           aggregate_kv_concepts),
        (dam_retrieval_agent,       aggregate_kv_concepts),  # DAM results join here
        
        # === SELECTION & CHANNEL ROUTING (unchanged) ===
        (aggregate_kv_concepts,     kv_ranker),
        (kv_ranker,                 hitl_kv_selection),
        (hitl_kv_selection,         channel_router),
        (channel_router,            content_agent),
        
        # === ADSPIRER EXECUTION (replaces stub) ===
        (content_agent,             execution_agent),   # execution_agent now calls Adspirer tools
        (execution_agent,           build_adspirer_manifest),
        (build_adspirer_manifest,   aggregation_agent),
        (aggregation_agent,         performance_agent),
    ]
)
```

### 11.2 State Key Extensions

The integration layers require the following additional session state keys:

| Key | Type | Set By | Consumed By |
|---|---|---|---|
| `crm_provider` | `str` | Frontend / request | `load_crm_context` |
| `crm_record_id` | `str` | Frontend / request | `load_crm_context` |
| `crm_brief` | `dict` | `load_crm_context` | `briefing_agent` (via `{brief}`) |
| `audience_insights` | `dict` | `enrich_brief_with_cdp` | `briefing_agent`, `strategy_agent` |
| `retrieved_dam_assets` | `list[dict]` | `dam_retrieval_agent` | `kv_image_agent_1..4` |
| `adspirer_campaign_id` | `str` | `execution_agent` | `aggregation_agent` |
| `adspirer_manifest` | `dict` | `build_adspirer_manifest` | `aggregation_agent` |

---

## 12. New Agent Definitions Required

### 12.1 `cdp_enrichment_agent`

This agent is optional — the `enrich_brief_with_cdp` function node can handle simple cases. The agent version adds reasoning over the retrieved profiles:

```python
cdp_enrichment_agent = Agent(
    name="cdp_enrichment_agent",
    model=settings.gemini_model_reasoning,
    instruction="""
    You are a Customer Intelligence Analyst. You have been given a campaign brief
    and access to a CDP database via the Postgres MCP tool.
    
    Your task:
    1. Extract the target audience description from {brief}
    2. Use the mcp_postgres.query tool to perform a semantic search:
       SELECT id, income, value_tier, lifestyle_archetype, customer_notes,
              (embedding <=> mcp_embed('{target_audience}')) as distance
       FROM customer_insights ORDER BY distance LIMIT 5
    3. Aggregate the results into a cohesive audience segment profile
    4. Return a JSON object matching the AudienceInsights schema
    
    The profile must include:
    - segment_id (generate from audience description)
    - summary (2-3 sentences describing who these people are)
    - attributes (avg_income, dominant_tier, dominant_archetype, engagement level)
    - qualitative_signals (top 3 customer notes, verbatim)
    - actionable_insights (2-3 creative implications for the campaign)
    """,
    tools=[postgres_mcp_toolset, cdp_get_audience_insights],
    output_key="audience_insights",
    generate_content_config={"response_modalities": ["TEXT"]}
)
```

### 12.2 `dam_retrieval_agent`

```python
dam_retrieval_agent = Agent(
    name="dam_retrieval_agent",
    model=settings.gemini_model_reasoning,
    instruction="""
    You are a Digital Asset Manager. You have been given a campaign strategy
    and access to a DAM database via semantic search tools.
    
    Your task:
    1. Extract the brand name and visual creative direction from {campaign_strategy}
    2. Call dam_search_brand_assets with a precise visual description query
    3. Return the top 3 most relevant assets with their image URLs
    
    Focus the search query on:
    - Product type (serum, mustard, body lotion, etc.)
    - Visual style from the KV strategy (clean, minimalist, premium, etc.)
    - Brand aesthetic cues
    
    Return a JSON object with:
    - assets: list of {asset_id, title, image_url, visual_attributes, similarity_score}
    - retrieval_rationale: why these assets match the creative direction
    - recommended_primary: which single asset is the strongest match
    """,
    tools=[dam_search_brand_assets],
    output_key="retrieved_dam_assets",
    generate_content_config={"response_modalities": ["TEXT"]}
)
```

### 12.3 Updated `execution_agent`

The existing execution agent stub is upgraded to use Adspirer tools:

```python
execution_agent = Agent(
    name="execution_agent",
    model=settings.gemini_model_reasoning,
    instruction=EXECUTION_AGENT_INSTRUCTIONS,  # Updated — see instructions.py additions
    tools=[
        adspirer_preflight,
        adspirer_deploy_draft,
        adspirer_bind_media,
        adspirer_get_manifest
    ],
    output_key="execution_result"
)
```

---

## 13. New Tool Definitions Required

Summary of all new tools required in `app/tools.py`:

| Tool Function | Layer | Async | Description |
|---|---|---|---|
| `crm_fetch_campaign_objective` | CRM | Yes | Fetch Salesforce campaign records |
| `crm_fetch_hubspot_deal` | CRM | Yes | Fetch HubSpot deal/campaign records |
| `get_crm_objective` | CRM | Yes | Unified CRM gateway (Salesforce or HubSpot) |
| `cdp_get_audience_insights` | CDP | Yes | Semantic search over customer_insights table |
| `cdp_get_segment_summary` | CDP | Yes | Aggregated segment view query |
| `dam_search_brand_assets` | DAM | Yes | Semantic search over dam_assets table |
| `adspirer_preflight` | Adspirer | Yes | Platform spec validation |
| `adspirer_deploy_draft` | Adspirer | Yes | Create paused campaign structures |
| `adspirer_bind_media` | Adspirer | Yes | Bind creative assets to campaigns |
| `adspirer_get_manifest` | Adspirer | Yes | Retrieve full deployment manifest |

---

## 14. New Node Definitions Required

Summary of all new function nodes required in `app/nodes.py`:

| Node Function | Position in DAG | Description |
|---|---|---|
| `load_crm_context` | First node | Fetches CRM campaign record, pre-populates brief |
| `enrich_brief_with_cdp` | After `load_brand_context` | Runs CDP semantic search, appends audience_insights to state |
| `inject_dam_assets` | Parallel with KV fan-out | Writes retrieved_dam_assets into state for kv_image_agents |
| `build_adspirer_manifest` | After `execution_agent` | Calls `adspirer_get_manifest`, writes to state |

---

## 15. Updated Pydantic Models

The following models need to be added to `app/models.py`:

```python
# app/models.py — additions

from pydantic import BaseModel, Field
from typing import Optional

class CRMCampaignRecord(BaseModel):
    """Canonical CRM campaign record (Salesforce or HubSpot)"""
    campaign_id: str
    campaign_name: str
    brand: str
    product: str
    objective: str
    target_audience: str
    channels: list[str]
    budget_range: str
    market: str
    source_crm: str  # 'salesforce' | 'hubspot'
    status: str

class AudienceInsights(BaseModel):
    """CDP audience segment profile from pgvector semantic search"""
    segment_id: str
    summary: str
    attributes: dict = Field(
        description="avg_income, dominant_tier, dominant_archetype, engagement"
    )
    qualitative_signals: list[str] = Field(
        description="Top 3 customer notes from semantic search"
    )
    actionable_insights: list[str] = Field(
        description="Creative implications derived from audience data"
    )
    pgvector_match_count: int

class DAMAsset(BaseModel):
    """A single digital asset retrieved from the DAM"""
    asset_id: str
    title: str
    image_url: str
    visual_attributes: str
    brand: str
    similarity_score: float

class DAMRetrievalResult(BaseModel):
    """Result of a DAM semantic asset search"""
    assets: list[DAMAsset]
    retrieval_query: str
    brand_filter: Optional[str]
    recommended_primary: Optional[str] = Field(
        description="asset_id of the recommended primary asset"
    )
    retrieval_rationale: str

class AdspirePlatformRecord(BaseModel):
    """Single platform entry in an Adspirer campaign"""
    platform: str
    status: str  # Always 'PAUSED' initially
    network_campaign_id: str
    budget_allocation: float
    currency: str
    objective: str
    asset: Optional[str] = None  # Bound asset URL after upload
    headline: Optional[str] = None

class AdspirerCampaign(BaseModel):
    """Full Adspirer campaign structure"""
    campaign_id: str
    campaign_name: str
    status: str
    total_budget: float
    currency: str
    platforms: list[AdspirePlatformRecord]
    hitl_gate: dict
    created_at: str

class AdspirerManifest(BaseModel):
    """Full deployment manifest for the current session"""
    session_id: str
    generated_at: str
    simulation_mode: bool
    campaigns: list[AdspirerCampaign]
    total_assets_bound: int
```

---

## 16. Docker Infrastructure

### 16.1 Database Initialisation Script

```sql
-- scripts/init_db.sql
-- Runs automatically on first container start

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- CDP schema
CREATE TABLE IF NOT EXISTS customer_insights (
    id                  INT PRIMARY KEY,
    year_birth          INT,
    education           VARCHAR(50),
    marital_status      VARCHAR(30),
    income              NUMERIC(10,2),
    kidhome             INT DEFAULT 0,
    teenhome            INT DEFAULT 0,
    recency             INT,
    complain            INT DEFAULT 0,
    mnt_wines           NUMERIC(8,2) DEFAULT 0,
    mnt_fruits          NUMERIC(8,2) DEFAULT 0,
    mnt_meat_products   NUMERIC(8,2) DEFAULT 0,
    mnt_fish_products   NUMERIC(8,2) DEFAULT 0,
    mnt_sweet_products  NUMERIC(8,2) DEFAULT 0,
    mnt_gold_prods      NUMERIC(8,2) DEFAULT 0,
    num_web_purchases       INT DEFAULT 0,
    num_catalog_purchases   INT DEFAULT 0,
    num_store_purchases     INT DEFAULT 0,
    num_web_visits_month    INT DEFAULT 0,
    num_deals_purchases     INT DEFAULT 0,
    accepted_cmp1       INT DEFAULT 0,
    accepted_cmp2       INT DEFAULT 0,
    accepted_cmp3       INT DEFAULT 0,
    accepted_cmp4       INT DEFAULT 0,
    accepted_cmp5       INT DEFAULT 0,
    response            INT DEFAULT 0,
    customer_notes      TEXT,
    segment_label       VARCHAR(100),
    value_tier          VARCHAR(20),
    lifestyle_archetype VARCHAR(50),
    embedding           vector(384)
);

CREATE INDEX IF NOT EXISTS cdp_hnsw_idx
    ON customer_insights
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- DAM schema
CREATE TABLE IF NOT EXISTS dam_assets (
    asset_id            VARCHAR(50) PRIMARY KEY,
    brand_division      VARCHAR(100),
    asset_type          VARCHAR(50),
    image_url           TEXT NOT NULL,
    title               TEXT,
    category            VARCHAR(100),
    description         TEXT,
    mapped_brand        VARCHAR(100),
    mapped_division     VARCHAR(50),
    visual_attributes   TEXT,
    description_embedding vector(384)
);

CREATE INDEX IF NOT EXISTS dam_hnsw_idx
    ON dam_assets
    USING hnsw (description_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Segment summary view
CREATE OR REPLACE VIEW cdp_segment_summary AS
SELECT
    value_tier,
    lifestyle_archetype,
    COUNT(*)                            AS segment_size,
    ROUND(AVG(income)::numeric, 0)      AS avg_income,
    ROUND((AVG(mnt_wines + mnt_fruits + mnt_meat_products +
               mnt_fish_products + mnt_sweet_products + mnt_gold_prods))::numeric, 0)
                                        AS avg_total_spend,
    ROUND(AVG(num_web_purchases)::numeric, 1) AS avg_web_purchases,
    ROUND(AVG(accepted_cmp1 + accepted_cmp2 + accepted_cmp3 +
              accepted_cmp4 + accepted_cmp5)::numeric, 2) AS avg_campaign_responses
FROM customer_insights
GROUP BY value_tier, lifestyle_archetype;
```

### 16.2 New Python Dependencies

Add to `rebuild/pyproject.toml`:

```toml
[project.dependencies]
# ... existing ...

# pgvector integration
asyncpg = ">=0.29.0"
psycopg2-binary = ">=2.9.9"

# Embedding model
sentence-transformers = ">=3.0.0"
torch = ">=2.3.0"

# Dataset loading
datasets = ">=2.20.0"
pandas = ">=2.2.0"

# Seeding utility
kaggle = ">=1.6.0"
```

---

## 17. Dataset Seeding Strategy

### 17.1 Execution Sequence

The complete seeding flow, from raw datasets to queryable pgvector tables:

```
Step 1: Start Docker infrastructure
  docker compose up -d postgres

Step 2: Wait for postgres to be healthy
  docker compose exec postgres pg_isready

Step 3: Run DB initialisation (auto via docker entrypoint)
  docker compose exec postgres psql -U mcp_user -d marketing_intelligence -f /init.sql

Step 4: Download Customer Personality Analysis from Kaggle
  kaggle datasets download -d imakash3011/customer-personality-analysis -p ./data
  unzip ./data/customer-personality-analysis.zip -d ./data

Step 5: Seed CDP
  uv run python scripts/seed_cdp.py --csv ./data/marketing_campaign.csv
  # Expected: ~2,240 records seeded in ~3 minutes (CPU) or ~30s (GPU)

Step 6: Seed DAM from Marqo Hugging Face dataset
  uv run python scripts/seed_dam.py --limit 500
  # Expected: 500 product records, all with live CDN image URLs

Step 7: Start MCP Postgres server
  docker compose up -d mcp-postgres

Step 8: Verify with test queries
  uv run python scripts/verify_pgvector.py
```

### 17.2 Verification Queries

```python
# scripts/verify_pgvector.py

import asyncio
from app.vector_client import VectorClient

async def verify():
    vc = VectorClient()
    
    print("\n=== CDP Verification ===")
    results = await vc.semantic_search_cdp("high value churn risk app failure")
    print(f"Top match: {results[0]['customer_notes'][:200]}...")
    print(f"Income: £{results[0]['income']:,} | Tier: {results[0]['value_tier']}")
    
    print("\n=== DAM Verification ===")
    assets = await vc.semantic_search_dam(
        "clinical skincare serum dropper bottle white background",
        brand_filter="PaulasChoice"
    )
    for a in assets:
        print(f"Asset: {a['title'][:60]} | Score: {1-a['distance']:.3f}")
        print(f"  URL: {a['image_url'][:80]}")
    
    print("\n=== Hybrid Intelligence ===")
    result = await vc.hybrid_brief_intelligence(
        audience_query="premium lifestyle buyers frustrated with digital experience",
        asset_query="premium skincare serum studio shot minimal",
        value_tier="HIGH",
        brand="PaulasChoice"
    )
    print(f"Audience profiles found: {len(result['audience_profiles'])}")
    print(f"DAM assets found: {len(result['recommended_assets'])}")

asyncio.run(verify())
```

---

## 18. Frontend UI Extensions

### 18.1 CRM Source Toggle

Add a CRM source selector to the `LeftPanel.tsx` brief input form:

```tsx
// ui/app/components/LeftPanel.tsx — additions

type CRMProvider = 'none' | 'salesforce' | 'hubspot';

interface CRMSelectorProps {
  value: CRMProvider;
  onChange: (provider: CRMProvider) => void;
}

function CRMSelector({ value, onChange }: CRMSelectorProps) {
  return (
    <div className="crm-selector">
      <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
        Source CRM Network
      </label>
      <div className="flex gap-2 mt-1">
        {(['none', 'salesforce', 'hubspot'] as CRMProvider[]).map(provider => (
          <button
            key={provider}
            onClick={() => onChange(provider)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              value === provider
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {provider === 'none' ? 'Manual' : provider.charAt(0).toUpperCase() + provider.slice(1)}
          </button>
        ))}
      </div>
      {value !== 'none' && (
        <p className="text-xs text-gray-400 mt-1">
          Campaign objectives will be fetched from {value === 'salesforce' ? 'Salesforce' : 'HubSpot'}
        </p>
      )}
    </div>
  );
}
```

### 18.2 Deployment Manifest Panel

Add a deployment manifest view to `RightPanel.tsx` or as a new `DeploymentPanel.tsx`:

```tsx
// ui/app/components/DeploymentPanel.tsx

interface Platform {
  platform: string;
  status: string;
  asset?: string;
  headline?: string;
  budget_allocation: number;
}

interface Campaign {
  campaign_id: string;
  campaign_name: string;
  status: string;
  platforms: Platform[];
}

interface ManifestProps {
  manifest: {
    session_id: string;
    simulation_mode: boolean;
    campaigns: Campaign[];
    total_assets_bound: number;
  };
}

export function DeploymentManifest({ manifest }: ManifestProps) {
  const statusBadge = (status: string) => (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
      status === 'PAUSED' ? 'bg-yellow-100 text-yellow-800' :
      status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
      'bg-gray-100 text-gray-600'
    }`}>
      {status === 'PAUSED' ? '⏸' : status === 'ACTIVE' ? '▶' : '●'} {status}
    </span>
  );

  return (
    <div className="deployment-manifest p-4 rounded-lg border border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">ADK Deployment Manifest</h3>
        {manifest.simulation_mode && (
          <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-medium">
            Simulation Mode
          </span>
        )}
      </div>
      
      {manifest.campaigns.map(campaign => (
        <div key={campaign.campaign_id} className="mb-4">
          <p className="text-xs text-gray-500 mb-2">{campaign.campaign_name}</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b">
                <th className="text-left py-1">Platform</th>
                <th className="text-left py-1">Status</th>
                <th className="text-left py-1">Budget</th>
                <th className="text-left py-1">Asset</th>
              </tr>
            </thead>
            <tbody>
              {campaign.platforms.map(p => (
                <tr key={p.platform} className="border-b border-gray-50">
                  <td className="py-1.5 font-medium capitalize">{p.platform.replace('_', ' ')}</td>
                  <td className="py-1.5">{statusBadge(p.status)}</td>
                  <td className="py-1.5 text-gray-600">£{p.budget_allocation.toLocaleString()}</td>
                  <td className="py-1.5 text-gray-500 text-xs truncate max-w-[120px]">
                    {p.asset ? '✓ Bound' : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      
      <p className="text-xs text-gray-400 mt-2">
        {manifest.total_assets_bound} assets bound · HITL approval required before live
      </p>
    </div>
  );
}
```

### 18.3 CDP Insights Display

Add a real-time CDP insights panel to `CentrePanel.tsx` that shows the retrieved audience profile once `audience_insights` is in the pipeline state stream:

```tsx
// Rendered when the pipeline emits audience_insights in the SSE stream
function AudienceInsightsCard({ insights }: { insights: AudienceInsights }) {
  return (
    <div className="audience-insights rounded-lg bg-purple-50 border border-purple-100 p-3 mb-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-purple-600">👥</span>
        <span className="text-sm font-semibold text-purple-900">CDP Intelligence</span>
        <span className="text-xs text-purple-500 ml-auto">
          {insights.pgvector_match_count} profiles matched via pgvector
        </span>
      </div>
      <p className="text-sm text-purple-800 mb-2">{insights.summary}</p>
      <div className="flex gap-3 text-xs">
        <span className="text-purple-600">
          Avg income: £{insights.attributes.avg_income?.toLocaleString()}
        </span>
        <span className="text-purple-600">
          Tier: {insights.attributes.dominant_value_tier}
        </span>
        <span className="text-purple-600">
          {insights.attributes.dominant_lifestyle}
        </span>
      </div>
      {insights.qualitative_signals?.length > 0 && (
        <blockquote className="mt-2 text-xs text-purple-700 italic border-l-2 border-purple-300 pl-2">
          "{insights.qualitative_signals[0].slice(0, 150)}..."
        </blockquote>
      )}
    </div>
  );
}
```

---

## 19. Implementation Phases & Sequencing

### Phase 0 — Infrastructure Foundation (Days 1–2)

The pgvector infrastructure must exist before any other integration can be tested. This is the critical path dependency for everything else.

**Deliverables:**
- [ ] `docker-compose.yml` created with `postgres` and `mcp-postgres` services
- [ ] `scripts/init_db.sql` written and tested
- [ ] `app/config.py` extended with pgvector settings
- [ ] `app/vector_client.py` written and connected
- [ ] `scripts/verify_pgvector.py` passes with empty tables

**Acceptance Criteria:** `docker compose up -d` produces a healthy Postgres instance with the `marketing_intelligence` database, both tables created, and both HNSW indexes built. The VectorClient connects and returns empty result sets without error.

---

### Phase 1 — CDP Layer (Days 3–4)

**Deliverables:**
- [ ] `scripts/seed_cdp.py` written with `generate_crm_note()` function
- [ ] Kaggle dataset downloaded (2,240 rows)
- [ ] CDP seeding completed and verified (all rows have embeddings)
- [ ] `cdp_get_audience_insights` tool implemented and tested
- [ ] `enrich_brief_with_cdp` function node written
- [ ] `AudienceInsights` Pydantic model added to `models.py`
- [ ] Pipeline updated: `enrich_brief_with_cdp` node inserted after `load_brand_context`

**Acceptance Criteria:** Running `verify_pgvector.py` returns a semantically relevant customer note for the query *"high value churn risk app failure"*. The top result has `value_tier='HIGH'` and `income > 70000`. The briefing agent's output includes `cdp_audience_insights` fields when the pipeline runs.

---

### Phase 2 — DAM Layer (Days 5–6)

**Deliverables:**
- [ ] `scripts/seed_dam.py` written with Marqo dataset streaming
- [ ] DAM seeding completed (500 records with live URLs)
- [ ] `dam_search_brand_assets` tool implemented and tested
- [ ] `dam_retrieval_agent` agent defined in `agents.py`
- [ ] `DAMRetrievalResult` Pydantic model added
- [ ] Pipeline updated: `dam_retrieval_agent` added as parallel branch after `strategy_agent`
- [ ] `inject_dam_assets` node added to fan-in

**Acceptance Criteria:** `dam_search_brand_assets("clinical skincare serum dropper bottle", brand="PaulasChoice")` returns at least 2 results with valid HTTPS image URLs. The KV ranker output includes `retrieved_dam_assets` in session state.

---

### Phase 3 — CRM Layer (Days 7–8)

**Deliverables:**
- [ ] `crm_fetch_campaign_objective` tool implemented (Salesforce mock)
- [ ] `crm_fetch_hubspot_deal` tool implemented (HubSpot mock)
- [ ] `get_crm_objective` unified gateway tool implemented
- [ ] `load_crm_context` function node written
- [ ] `CRMCampaignRecord` Pydantic model added
- [ ] Pipeline updated: `load_crm_context` added as first node
- [ ] Frontend CRM toggle implemented in `LeftPanel.tsx`
- [ ] API `/pipeline` endpoint extended to accept `crm_provider` and `crm_record_id`

**Acceptance Criteria:** Submitting a pipeline run with `crm_provider: "salesforce"` results in the pipeline brief being populated from the mock CRM record without any manual brief text. The `briefing_agent` output reflects the CRM-sourced product and objective.

---

### Phase 4 — Adspirer Execution Layer (Days 9–10)

**Deliverables:**
- [ ] `app/mock_adspirer.py` written with full `MockAdspirer` class
- [ ] `adspirer_preflight`, `adspirer_deploy_draft`, `adspirer_bind_media`, `adspirer_get_manifest` tools implemented
- [ ] `execution_agent` updated to use Adspirer tools instead of stub
- [ ] `build_adspirer_manifest` function node written
- [ ] `AdspirerManifest` and `AdspirerCampaign` Pydantic models added
- [ ] `EXECUTION_AGENT_INSTRUCTIONS` updated in `instructions.py`
- [ ] `DeploymentManifest` React component implemented
- [ ] Pipeline DAG updated with `build_adspirer_manifest` node

**Acceptance Criteria:** A full pipeline run produces an `AdspirerManifest` with at least one `PAUSED` campaign record for each requested channel. All assets are shown as `PENDING_REVIEW`. The manifest JSON is rendered in the UI deployment panel.

---

### Phase 5 — Integration Polish & Demo Preparation (Days 11–14)

**Deliverables:**
- [ ] End-to-end pipeline run tested: Salesforce brief → CDP enrichment → DAM retrieval → KV generation → Adspirer deployment
- [ ] End-to-end pipeline run tested: HubSpot brief → same pipeline
- [ ] Verification queries pass across all three data layers
- [ ] `AudienceInsightsCard` React component implemented and wired to SSE stream
- [ ] Full demo narrative rehearsed: toggle CRM from Salesforce → HubSpot mid-demo
- [ ] README updated with full setup instructions for integration stack

---

## 20. Testing & Verification Strategy

### 20.1 Unit Test: CDP Semantic Relevance

A robust CDP integration should pass three semantic relevance tests that are verifiable against the Kaggle ground truth:

```python
# tests/test_cdp_integration.py

import pytest
import asyncio
from app.vector_client import VectorClient

@pytest.mark.asyncio
async def test_premium_churn_risk_query():
    """
    Query: 'high value customer churn risk app failure'
    Expected: top results should have income > 70000 AND mnt_wines > 400
    Verifies that vector search correctly identifies frustrated VIPs.
    """
    vc = VectorClient()
    results = await vc.semantic_search_cdp("high value customer churn risk app failure", top_k=5)
    
    assert len(results) > 0
    top = results[0]
    
    # The generated notes for HIGH-tier customers contain friction vocabulary
    assert top["value_tier"] == "HIGH", f"Expected HIGH tier, got {top['value_tier']}"
    assert top["income"] > 70000, f"Expected income > 70000, got {top['income']}"
    # Verify the note contains relevant vocabulary
    assert any(word in top["customer_notes"].lower() for word in ["vip", "premium", "dissatisfi", "frustrat", "crash"])

@pytest.mark.asyncio
async def test_deal_seeker_query():
    """
    Query: 'budget conscious family deal seeker promotional buyer'
    Expected: top results should have high NumDealsPurchases and kidhome > 0
    """
    vc = VectorClient()
    results = await vc.semantic_search_cdp(
        "budget conscious family deal seeker promotional buyer", top_k=5
    )
    
    assert len(results) > 0
    # Average income should be lower for this segment
    avg_income = sum(r["income"] for r in results) / len(results)
    assert avg_income < 70000, f"Expected avg income < 70k for LOW tier, got {avg_income}"

@pytest.mark.asyncio
async def test_hybrid_brief_intelligence():
    """
    Cross-table query: audience profiles + matching DAM assets
    Both result sets should be non-empty and semantically relevant.
    """
    vc = VectorClient()
    result = await vc.hybrid_brief_intelligence(
        audience_query="premium lifestyle buyers frustrated with digital experience",
        asset_query="premium skincare serum studio shot minimal white background",
        value_tier="HIGH",
        brand="PaulasChoice"
    )
    
    assert len(result["audience_profiles"]) > 0
    assert len(result["recommended_assets"]) > 0
    
    # All audience results should be HIGH tier (filter applied)
    for profile in result["audience_profiles"]:
        assert profile["value_tier"] == "HIGH"
    
    # All DAM assets should be PaulasChoice brand (filter applied)
    for asset in result["recommended_assets"]:
        assert asset["mapped_brand"] == "PaulasChoice"
```

### 20.2 Unit Test: Adspirer Mock Integrity

```python
# tests/test_adspirer_mock.py

import pytest
from app.mock_adspirer import MockAdspirer

def test_campaign_created_in_paused_state():
    client = MockAdspirer()
    result = client.create_campaign(
        campaign_name="Test Campaign",
        platforms=["meta", "tiktok"],
        budget=50000.0
    )
    
    assert result["status"] == "PAUSED"
    assert len(result["platforms"]) == 2
    for platform in result["platforms"]:
        assert platform["status"] == "PAUSED"
    assert result["hitl_gate"]["required"] is True

def test_platform_budget_split_evenly():
    client = MockAdspirer()
    result = client.create_campaign(
        "Split Test", ["meta", "tiktok", "google_pmax"], budget=30000.0
    )
    
    budgets = [p["budget_allocation"] for p in result["platforms"]]
    assert all(abs(b - 10000.0) < 0.01 for b in budgets)

def test_asset_binding_requires_valid_campaign():
    client = MockAdspirer()
    result = client.upload_assets("invalid_id", "meta", "http://example.com/img.png", ["Headline"])
    assert result["status"] == "ERROR"

def test_manifest_reflects_all_operations():
    client = MockAdspirer()
    campaign = client.create_campaign("Demo", ["meta"], 10000.0)
    client.upload_assets(campaign["campaign_id"], "meta", "http://cdn.example.com/product.jpg", ["Elevate your routine"])
    
    manifest = client.get_deployment_manifest()
    assert len(manifest["campaigns"]) == 1
    assert manifest["total_assets_bound"] == 1
    assert len(manifest["audit_log"]) == 2  # CREATE + UPLOAD
```

### 20.3 Integration Test: CRM → CDP → DAM Pipeline Path

```python
# tests/test_integration_e2e.py

import pytest
import asyncio
from app.nodes import load_crm_context, enrich_brief_with_cdp

@pytest.mark.asyncio
async def test_crm_to_cdp_enrichment_flow():
    """
    Simulates the first three pipeline nodes:
    load_crm_context → load_brand_context → enrich_brief_with_cdp
    Verifies that CRM data flows correctly into CDP enrichment.
    """
    # Mock tool context with session state
    class MockState(dict):
        pass
    
    class MockContext:
        def __init__(self):
            self.state = MockState()
    
    ctx = MockContext()
    ctx.state["crm_provider"] = "salesforce"
    
    # Node 1: CRM
    crm_result = await load_crm_context({}, ctx)
    assert "brief" in ctx.state
    assert ctx.state["brief"]["brand"] == "Maille"
    assert "target_audience" in ctx.state["brief"]
    
    # Node 3: CDP (skip load_brand_context for this test)
    cdp_result = await enrich_brief_with_cdp(crm_result, ctx)
    assert "audience_insights" in ctx.state
    assert "segment_id" in ctx.state["audience_insights"]
    assert ctx.state["audience_insights"]["pgvector_match_count"] > 0
```

---

## 21. Demo Narrative & Presentation Flow

### 21.1 The Core Pitch

The presentation walks through five beats that map to the five integration layers. The critical framing is that each integration **removes a friction point that exists in today's enterprise marketing workflows**:

> *"A brand manager today opens four separate browser tabs: Salesforce for their campaign objective, a CDP portal for audience data, Cloudinary for product assets, and Google Ads for deployment. They manually copy-paste information between all four. Every handoff is a potential error, a compliance gap, or a wasted hour. CampaignOS eliminates every one of those manual handoffs."*

### 21.2 Demo Run Script

**Setup (1 minute):**
- Show the empty pipeline UI
- Highlight the CRM source selector: "The workflow doesn't start with a blank text box — it starts inside your CRM"

**Beat 1 — CRM Integration (2 minutes):**
- Select "Salesforce" in the toggle
- The campaign dropdown populates from the mock Salesforce record
- Select *"2026_Q3_Maille_Premium_Reengagement"*
- The pipeline brief fields auto-populate
- *Key message: "No re-typing. No human error. The business logic from Salesforce becomes the AI's brief."*

**Beat 2 — CDP Intelligence (2 minutes):**
- Watch the `enrich_brief_with_cdp` node fire in the pipeline visualiser
- The purple `AudienceInsightsCard` appears: *"VIP customer contact log updated. Strong affinity for reserve selections..."*
- *Key message: "The agent just read 2,240 customer profiles in real-time and extracted the three most relevant narratives. A human research team would take a week to produce the same insight."*

**Beat 3 — DAM Asset Retrieval (2 minutes):**
- The `dam_retrieval_agent` fires in parallel with KV concept generation
- Show the retrieved product shot: a real live CDN URL from the Marqo dataset
- *Key message: "The agent didn't generate an imaginary product. It pulled the brand-approved master shot from the digital asset warehouse. Nano Banana then composes the approved asset into the scene."*

**Beat 4 — KV Generation (3 minutes):**
- Watch the four KV branches fan out and fan back in
- Show the four finished key visuals in the HITL gate
- *Key message: "Four creative directions, built in parallel, each grounded in the same brand data. The human selects the strongest one. Everything else is automated."*

**Beat 5 — Adspirer Deployment (2 minutes):**
- The execution agent fires and the Deployment Manifest appears
- Show the three PAUSED campaign rows: Meta, TikTok, Google PMax
- *Key message: "PAUSED. One click from live. The brand manager reviews a complete, ready-to-launch package — not a mood board."*

**The Pivot (1 minute — the masterstroke):**
- Flip the CRM toggle from Salesforce to HubSpot
- Run again with the Paula's Choice HubSpot record
- *Key message: "Different CRM. Different brand. Different product. Same architecture. No code changes. This is what vendor-agnostic means."*

---

## 22. Security & Compliance Considerations

### 22.1 Data Privacy

The Kaggle Customer Personality Analysis dataset is synthetic marketing research data with no personally identifiable information. There are no real customer identities, email addresses, or GDPR-sensitive fields. The dataset is entirely safe to use in a demo environment without any anonymisation requirements.

However, the architecture should be designed from day one to handle real PII correctly, since the production equivalent (a real enterprise CDP) will contain it:

- **No PII in embedding inputs**: The `generate_crm_note` function constructs notes from numerical attributes only. No real names, addresses, or contact details are ever embedded into the vector space.
- **Database access controls**: The `mcp_user` Postgres role should have `SELECT`-only access to the CDP tables. Write access is restricted to the seeding scripts and never exposed via MCP.
- **Connection string security**: The `pgvector_password` must be loaded from environment variables (never hardcoded). In production, use GCP Secret Manager.

### 22.2 Campaign Safety (Adspirer PAUSED State)

The PAUSED-state default is a critical security control, not just a UX choice. It ensures:

- No budget is ever spent without explicit human approval
- No creative goes live without a HITL review
- The AI system cannot autonomously publish to ad platforms, regardless of how confident the model is

This must be enforced at the `MockAdspirer` level (status hardcoded to `"PAUSED"` in `create_campaign`) and documented explicitly in the deployment manifest.

### 22.3 Prompt Injection Awareness

The CDP `customer_notes` field contains user-generated-style text that will be injected into agent instruction prompts via `{audience_insights}` session state placeholders. While the notes are synthetically generated in this implementation, the architecture must guard against prompt injection in production:

- Strip HTML/markdown from any text retrieved from the CDP before injecting into agent instructions
- Use the `qualitative_signals` field as a **quoted block** in agent prompts, never as raw instruction text
- In production, validate all MCP tool outputs against expected JSON schemas before injecting into session state

### 22.4 API Key Management

The mock implementation requires no live API keys. When transitioning to production:

- Salesforce OAuth tokens: stored in GCP Secret Manager, injected at runtime via Workload Identity
- HubSpot OAuth tokens: same pattern
- Never log access tokens, even in debug mode
- MCP server configurations should reference `${ENV_VAR}` placeholders, not literal values

---

*This document represents the complete architectural specification for integrating the five external layers into the CampaignOS ADK 2.0 pipeline. The implementation is designed to be modular — each phase is independently deployable and testable without requiring all other phases to be complete.*
