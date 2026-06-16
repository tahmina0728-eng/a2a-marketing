# CampaignOS — Technical Presentation Script
### Full System Architecture, Agent Pipeline & Frontend–Backend Integration

---

## SLIDE 1 — Opening: What Is CampaignOS?

**[SPEAKER]**

CampaignOS is an end-to-end AI-powered campaign production platform. A marketing team fills in one brief — brand, product, audience, budget, channels — and the system produces a validated strategy, campaign copy, hero visual, a six-second video reel, and a pre-launch performance forecast. Everything a team would normally spend two weeks producing, delivered in under five minutes.

The platform is built on three pillars:

**First** — A multi-agent AI pipeline powered by Google's Agent Development Kit, where specialised agents each own one part of the creative process and hand off structured data to the next agent in the chain.

**Second** — A React frontend that streams live progress from the pipeline over Server-Sent Events, showing every agent working in real time.

**Third** — Google Cloud infrastructure: Vertex AI for language and image models, Veo for video, Vertex AI Search for brand intelligence retrieval, Cloud SQL with pgvector for audience embeddings, BigQuery for campaign audit logging, and Cloud Storage for brand assets.

Let me walk you through the complete technical architecture, layer by layer.

---

## SLIDE 2 — Frontend Technology Stack

**[SPEAKER]**

The frontend is a **React 18 + TypeScript** single-page application built with **Vite** as the bundler. It lives in the `frontend/src/` directory and the entire UI — all components, state management, API integration, and styling — is contained in a single file: `App.tsx`. This is an intentional architectural decision for a demo platform: one file, zero magic, every line visible.

**Key technology choices:**

**React 18** — we use functional components with hooks throughout. No class components, no Redux, no Context API. State management is done with `useState`, `useReducer` patterns, and a custom hook called `usePipeline`.

**TypeScript** — every agent output, every API response, every piece of state is typed. The types mirror the Python Pydantic models on the backend exactly. If the backend produces a `PerformanceForecast`, there is a matching TypeScript interface.

**Vite** — ultra-fast dev server with hot module replacement. The build output is a static bundle that can be served from any CDN or Cloud Run container.

**No UI library** — all components are built from scratch using inline styles and CSS-in-JS patterns. This means full control over every pixel, no version conflicts, and a consistent design system enforced entirely through shared style constants defined at the top of `App.tsx`.

**CSS animations** — agent status animations (pulsing orbs, wave dots, fade-ins) are pure CSS keyframe animations injected via a `<style>` tag. The `icon-breathe` animation runs on the orbiting agent icons while their agent is working.

**Environment variables** — the API base URL is read from `VITE_API_URL` at build time, defaulting to `http://localhost:8000` for local development. In Cloud Run, this points to the deployed harness URL.

---

## SLIDE 3 — Frontend Architecture: The Three Screens

**[SPEAKER]**

The frontend has three distinct screen states, all managed through a single `status` field in `PipelineState`:

**Screen 1 — Idle / Brief Form (`status: "idle"`)**
The user sees the animated agent network — eight agent nodes orbiting a central A2A logo, connected by animated lines. This is built with SVG and trigonometric positioning: each node sits at angle `(i / 8) * 2π` on a circle, calculated in the `AgentNetworkDiagram` component. Clicking any node opens an info card with the agent's name, role description, and colour.

Below the network is a six-step wizard form: campaign basics, audience definition, channel selection, Fan Truth statement, tone, and budget. The wizard is built as a controlled component — each step validates before the user can advance.

**Screen 2 — Running (`status: "running"`)**
Once the brief is submitted, the screen splits into three panels:

- **Left panel** — `StepsPanel`: a vertical timeline showing workflow stages (Brief Intake → Creative Direction → Channel Adoption → Performance → Activation). Each stage expands to show its sub-agents with live animated dots while running and a green tick when done.
- **Middle panel** — Live agent detail view: as each agent becomes active, clicking its node in the network opens a full-page panel showing its output as it arrives (strategy card, copy variants, key visual, etc.)
- **Right panel** — The agent network diagram continuously updates: running agents pulse, done agents glow, and a progress ring fills around the outer circle.

**Screen 3 — Done (`status: "done"`)**
The `ResultsView` component renders a vertical timeline of all seven pipeline stages as cards. Each step shows the actual output: Fan Truth score gauge, big idea quote, copy variants by channel, key visual with variation selector, channel adaptations, the Nexus performance forecast, and finally the launch panel where channels are selected and activated.

---

## SLIDE 4 — State Management: `usePipeline` Hook

**[SPEAKER]**

All pipeline state lives in a custom React hook: `usePipeline`, defined in `frontend/src/hooks/usePipeline.ts`.

The state shape is:

```typescript
interface PipelineState {
  campaign_id:     string | null;
  status:          "idle" | "running" | "done" | "error";
  pipeline_output: Record<string, unknown> | null;  // final result
  agentStatus:     Record<string, AgentStatus>;      // per-agent: pending/running/done/error
  liveLog:         AgentEvent[];                     // every SSE event
  milestones:      Record<string, Record<string,unknown>>; // agent data snapshots
  error:           string | null;
}
```

The hook exposes three functions:

**`startFullCampaign(brief)`** — the main path used by the UI:
1. POSTs the brief JSON to `POST /campaign` on the harness
2. Gets back a `campaign_id` immediately (the pipeline starts in the background)
3. Opens a `EventSource` connection to `GET /events/{campaign_id}`
4. Processes every incoming SSE event and updates state

**`startCampaign(brief)`** — the synchronous fallback path via `POST /brief-full`. Used for quick tests. No streaming — waits for the full response.

**`reset()`** — closes the SSE connection and resets state to idle.

---

## SLIDE 5 — Frontend to Backend: The SSE Connection

**[SPEAKER]**

This is the most important integration point. Let me explain exactly how data flows from the backend agents to the frontend UI in real time.

**Step 1 — Submit the brief**
The frontend POSTs to `POST /campaign`:
```
POST http://localhost:8000/campaign
Content-Type: application/json

{ "campaign_name": "Sunglow Summer", "brand": "Sunglow", "channels": ["instagram", "tiktok"], ... }
```

The harness responds immediately — within milliseconds — with just:
```json
{ "campaign_id": "campaign-sunglow-summer-27b422", "status": "started" }
```
The actual pipeline starts as an async background task in Python. The HTTP response closes. The frontend now has the campaign ID.

**Step 2 — Open the SSE stream**
The frontend immediately opens:
```
GET http://localhost:8000/events/campaign-sunglow-summer-27b422
Accept: text/event-stream
```

This is a long-lived HTTP connection. The server holds it open and pushes events as they happen. The browser's native `EventSource` API handles reconnection if the connection drops.

**Step 3 — Events arrive**
Every event has this shape:
```json
{ "agent": "briefing", "status": "running", "message": "Validating brief…", "t": 1749821645 }
```

The frontend processes events by `status` type:

| Status | What happens |
|---|---|
| `"running"` | Updates `agentStatus[agent] = "running"`, adds to `liveLog` |
| `"done"` | Updates `agentStatus[agent] = "done"`, extracts inline milestone data if present |
| `"milestone"` | Parses JSON from `message` and merges into `milestones[agent]` |
| `"step_data"` | Same as milestone — merges partial data (used during KV pipeline steps) |
| `"__done__"` | Pipeline finished — parses full result JSON, sets `status: "done"` |
| `"__error__"` | Pipeline failed — sets `status: "error"` with the error message |

**Step 4 — Milestone data populates UI panels**
When Nexus (the performance agent) completes, the backend emits:
```json
{ "agent": "performance", "status": "milestone", "message": "{\"headline_prediction\": \"Strong campaign...\", \"predicted_total_reach\": \"8.2M\", ...}" }
```
The frontend parses the JSON and stores it as `milestones["performance"]`. The `PerformanceIntakeView` component reads `milestone={state.milestones["performance"]}` and renders the full forecast card. Until the milestone arrives, it shows the pulsing loading state.

**Step 5 — Final `__done__` event**
When all agents finish, the backend sends:
```json
{ "agent": "__done__", "status": "done", "message": "<full result JSON>" }
```
The frontend parses `result.performance_forecast`, `result.creative_strategy`, `result.creative_pipeline`, etc. and sets `pipeline_output`. This triggers the `ResultsView` to render the complete campaign results timeline.

---

## SLIDE 6 — Backend: FastAPI Application (`main.py`)

**[SPEAKER]**

The backend is a **FastAPI** application in Python, running inside a `uv`-managed virtual environment. It starts with `uv run uvicorn main:app`.

**Key routes:**

| Route | Method | Purpose |
|---|---|---|
| `/campaign` | POST | Start campaign — returns `campaign_id` immediately |
| `/events/{id}` | GET | SSE stream of progress events for a running campaign |
| `/brief` | POST | Run briefing stage only (ADK pipeline) |
| `/brief-full` | POST | Run brief + strategy + copy synchronously (no streaming) |
| `/pipeline` | POST | Run full ADK DAG pipeline (no streaming) |
| `/health` | GET | Liveness probe for Cloud Run |
| `/readiness` | GET | Readiness probe — checks agents and search client are loaded |
| `/landing/{id}` | GET | Serve the generated brand landing page HTML |

**The SSE event store:**
```python
_pipelines: dict[str, dict] = {}
# { campaign_id: { "events": [...], "signal": asyncio.Event } }
```
Each running campaign has a list of events and an asyncio Event signal. When the SSE generator has read all events, it calls `await signal.wait()` — blocking the connection but using zero CPU. When `push_event()` is called from the background task, it appends to the list and calls `signal.set()`, waking the generator which immediately sends the new event.

**CORS:**
All origins are allowed (`*`) for local development. In production, this should be locked to the frontend domain.

---

## SLIDE 7 — Backend Folder Structure Deep Dive

**[SPEAKER]**

Let me go through every file in `harness/app/` and explain its role:

**`config.py`**
Centralised settings using `pydantic-settings`. Every environment variable is declared here as a typed field with defaults. Reading `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GCS_BUCKET`, `GEMINI_MODEL_REASONING`, `SEARCH_ENGINE_ID`, etc. The `get_settings()` function is `@lru_cache` decorated — the settings object is created once and reused across all requests. The `reasoning_model` property dynamically returns either a Gemini model string or a `LiteLlm` wrapper for Groq.

**`models.py`**
Every data structure in the pipeline is a Pydantic `BaseModel`. This gives: automatic JSON serialisation, runtime type validation, and clear data contracts between agents. The models are organised by pipeline stage:
- `BriefRequest` — what the human fills in
- `BriefingContext` — all pre-loaded brand data
- `MachineBrief` — validated brief with Fan Truth score
- `CreativeStrategy` / `BigIdea` — the campaign concept
- `CampaignCopy` — all copy variants
- `KVConcept` — a single key visual direction
- `ChannelPlan` / `ContentPackage` — per-channel assets
- `PerformanceForecast` / `ChannelForecast` — Nexus predictions

**`pipeline.py`**
Defines the ADK Workflow DAG using `google.adk.Workflow` and `JoinNode`. This is the pure ADK path. The graph is expressed as a list of `edges` — tuples of nodes. A `JoinNode` handles the KV fan-in: it waits for both `kv_image_agent_1` and `kv_image_agent_2` to complete before continuing to `aggregate_kv_concepts`. Two pipelines are exported: `briefing_pipeline` (brief stage only) and `root_agent` (full DAG).

**`agents.py`**
All 14+ agent instances are defined here as module-level constants. Each agent is a `google.adk.Agent` with: `name`, `model`, `description`, `instruction` (from `instructions.py`), and optional `output_key`, `output_schema`, `tools`, and `mode`. Agents with `mode="single_turn"` complete in one LLM call. Agents without it (like `culture_analyst`) can make multiple tool calls across several turns.

**`instructions.py`**
The system prompt for every agent. Instructions follow the ADK principle of describing role and behaviour only — never output schema (that's in `models.py`). Prompts use `{BriefingContext.field_name}` template variables that ADK automatically substitutes from session state before sending to the LLM.

**`nodes.py`**
Deterministic Python function nodes — zero LLM cost. `load_brand_context` is the most important: it runs before any agent and pre-loads all brand data so `briefing_agent` receives everything it needs without making tool calls. `persist_brief`, `persist_culture`, `persist_strategy`, `persist_copy` save each agent's output into ADK session state and as JSON artifacts. `aggregate_kv_concepts` is the fan-in function: it reads `kv_concept_1` and `kv_concept_2` from state and merges them into `kv_concepts_all` for the ranker.

**`runner.py`**
The execution engine for the `/campaign` route. Contains:
- `run_agent()` — executes any ADK agent or workflow
- `_vertex_generate()` — async Vertex AI call with retry on 429 and automatic fallback to a cheaper model
- `run_strategy_with_groq()` — strategy generation via Vertex AI
- `run_copy_agent()` — copy generation scoped to selected channels
- `run_creative_pipeline_direct()` — the full KV + Veo pipeline (2,000+ lines)
- `run_performance_forecast()` — Nexus pre-launch predictor

**`tools.py`**
Custom ADK tools — functions that agents can call via tool use. `generate_and_save_kv_image` is the main tool: it takes a KV concept's image prompt, calls Gemini's image generation API, applies Pillow text overlay (headline, brand colour, logo), saves to GCS, and returns the artifact key.

**`brand_assets.py`**
`BrandAssetLoader` — resolves brand assets from either local disk (`bucket/brands/{brand}/`) or GCS (`gs://{bucket}/brands/{brand}/`), depending on `BRAND_ASSETS_MODE`. Lists product images, logos, fonts, guidelines markdown. Used by `load_brand_context` at the start of every pipeline run.

**`search_client.py`**
Wraps Vertex AI Search. The `get_search_client()` function returns a singleton search client pointed at the `SEARCH_ENGINE_ID` app. The `search()` function queries the app and returns a summarised result string. Used in `nodes.py` to retrieve: brand rules, Fan Truth library, historical campaign benchmarks, channel benchmarks, and moment type rules.

**`pgvector_client.py`**
PostgreSQL + pgvector client for semantic audience search. Takes the audience description from the brief, generates a 768-dimension embedding using **Gemini Embedding 2** (task type `RETRIEVAL_QUERY`), and queries the `audience_profiles` table for the nearest matching customer segments. Returns audience intelligence used in the `MachineBrief`. The data was originally embedded with task type `RETRIEVAL_DOCUMENT` during setup.

**`data_loader.py`**
BigQuery read helpers for the agent pipeline — queries `briefing_agent.historical_campaigns`, `briefing_agent.fan_truth_library`, `briefing_agent.channel_benchmarks`. Also contains `log_brief_to_bigquery()` for writing pipeline audit records.

**`creative_pipeline.py`**
The image and video generation pipeline: Gemini image model calls, Pillow crop and overlay, Veo video generation (polls the long-running operation until completion or timeout), and channel adaptation (smart-crops the KV to Instagram 1:1, Stories 9:16, TikTok, Website 16:9, Email 3:1).

**`publisher.py`**
Campaign distribution: mock Google Ads submission with realistic preview data, branded HTML landing page generation (per-brand colour and font configuration for Sunglow, Rnorr, Boozt), and Gmail SMTP email sending with HTML creative.

---

## SLIDE 8 — The 16-Step Agent Pipeline End-to-End

**[SPEAKER]**

Let me walk through exactly what happens from the moment "Generate Campaign" is clicked to the moment the results appear.

---

### Step 0 — Brief Submission
The marketer completes the six-step wizard and clicks "Generate". The frontend calls `startFullCampaign(brief)` which POSTs to `/campaign`. The harness creates a campaign ID, registers an event store, launches `_run_campaign_background()` as an asyncio task, and returns the campaign ID within milliseconds. The frontend opens the SSE stream.

---

### Step 1 — `load_brand_context` (no LLM)
**What receives:** The raw `BriefRequest` JSON
**What it does:**
- Calls `BrandAssetLoader.load_guidelines(brand)` → reads `brand_guidelines.md` from GCS
- Calls `BrandAssetLoader.list_products/logos/assets(brand)` → lists all image URIs
- Makes 5 parallel Vertex AI Search queries: brand rules, Fan Truth benchmarks, campaign benchmarks, channel benchmarks, moment type rules
- Calls `pgvector_client.search_audience(audience_description)` → semantic search returns nearest CDP profiles
- Packages everything into `BriefingContext`

**What it outputs:** `BriefingContext` — the complete brief plus all brand intelligence

**SSE events:** None (runs synchronously before the first event)

---

### Step 2 — `briefing_agent` → **Logos**
**What receives:** The full `BriefingContext` — brand guidelines text, Fan Truth examples from the library, channel CTR/CPM benchmarks, historical campaign ROAS data, CDP audience profiles, and the raw brief

**What it does:**
- Reads the Fan Truth statement from the brief
- Scores it on three dimensions (Specific / Shared / Special) each 0–100
- Computes overall score — PASS if ≥70, FAIL if <70
- Cross-checks KPIs against historical benchmarks (flags AMBITIOUS or UNREALISTIC)
- Extracts brand locks from the guidelines — font, primary colour, accent colour, forbidden words
- Checks for legal/compliance issues → produces `ComplianceFlag` list

**What it outputs:** `MachineBrief`
```
fan_truth_score: { specific: 82, shared: 79, special: 85, overall: 82, verdict: "PASS" }
validation: { score: 88, status: "READY" }
kpi_flags: [ { kpi: "CTR 3.5%", flag: "AMBITIOUS", benchmark: "avg 2.3%" } ]
brand_locks: { font: "Alatsi", primary_colour: "#B00064" }
```

**SSE events:**
```
{ "agent": "briefing", "status": "running", "message": "Loading brand guidelines & audience data…" }
{ "agent": "briefing", "status": "done", "message": "{\"_text\": \"Brief validated ✓ — Fan Truth PASS 82/100\", \"fan_truth\": {...}, \"kpis\": [...] }" }
```
The `done` event carries inline milestone data (`_text` + structured fields). The frontend shows the Fan Truth score gauge and KPI panel.

**BigQuery:** A row is immediately written to `campaign_outputs.machine_briefs` (fire-and-forget asyncio task).

---

### Step 3 — `creative_director` / `run_strategy_with_groq` → **Helia**
**What receives:** `MachineBrief` + brand guidelines text + brand locks JSON

**What it does:**
- Synthesises brief, fan truth, cultural signal, and brand voice into a Big Idea
- Defines the hero message — the single most powerful line of the campaign (≤8 words, Fan-to-Fan voice)
- Sets the strategic framework — the "why this, why now, why us" narrative
- Assigns channel priorities and budget split percentages
- Writes the handoff message to the KV art directors

**What it outputs:** `CreativeStrategy`
```
big_idea.title: "Golden Radiance"
big_idea.essence: "This campaign makes people feel seen in their own skin"
hero_message: "Let it glow."
channel_priorities: [ { channel: "Instagram", priority: 9, rationale: "visual-first audience" } ]
budget_allocation: { "instagram": 40, "tiktok": 35, "google": 25 }
```

**SSE events:**
```
{ "agent": "strategy", "status": "running", "message": "Building creative strategy & hero message…" }
{ "agent": "strategy", "status": "done", "message": "{\"_text\": \"Strategy ready — 'Let it glow.'\", \"hero_message\": \"Let it glow.\", ...}" }
{ "agent": "strategy", "status": "milestone", "message": "{\"hero_image_b64\": \"<base64 brand image>\"}" }
```

---

### Step 4 — `copy_agent` / `run_copy_agent` → **Ideon**
**What receives:** `CreativeStrategy` + `MachineBrief` + brand locks + selected channel list

**What it does:**
- Writes three copy length variants: short (billboard, ≤6 words), medium (social, ≤10 words), long (editorial, ≤60 words)
- Generates channel-specific copy for every selected channel
- Enforces brand locks: no tagline in captions, CTA max 3 words, no corporate language

**What it outputs:**
```
short:   { headline: "Let It Glow." }
medium:  { headline: "Real glow. No filter needed.", subline: "Formulated for Black hair from the start." }
cta: "Glow Now"
instagram_caption: "Your glow was never lost. Just waiting. ✨ #LetItGlow #SunglowHair"
tiktok_hook: "POV: your hair finally has its moment"
google_headline: "Black Hair That Glows"
```

**SSE events:**
```
{ "agent": "copy", "status": "done", "message": "{\"_text\": \"Copy ready — 'Let It Glow.'\", \"short_headline\": \"Let It Glow.\", ...}" }
```

---

### Step 5 — Cultural Intelligence → **Aether**
**What receives:** Campaign brief context (brand, product, market, season, audience)

**What it does:**
- Makes multiple live Google Search calls (not simulated — real live web results)
- Searches for: trending conversations around the brand's audience, cultural moments in the market, competitor activity, hashtag trends, creator economy signals
- Aggregates research across several search rounds
- `culture_formatter` then structures the raw research into `CultureAnalysis`

**What it outputs:**
```
summary: "The natural hair movement is accelerating on TikTok, led by Gen Z creators sharing 'big chop' journeys..."
recommendations: [
  "Tap into #NaturalHair TikTok — 2.3B views, high engagement",
  "Align with 'Summer Glow' search trend peaking June–August"
]
```

**SSE events:**
```
{ "agent": "culture", "status": "running", "message": "Researching cultural trends for Sunglow audience…" }
{ "agent": "culture", "status": "milestone", "message": "{\"brief\": \"The natural hair movement is accelerating...\"}" }
```

---

### Step 6 — Key Visual Generation → **Morphis** (Gemini Image + Fan-Out)
**What receives:** `CreativeStrategy` + `CampaignCopy` + brand guidelines + product images from GCS

**What it does (fan-out — runs PARALLEL):**

`kv_generator_1` — graphic-led art director: designs a KV where layout, colour fields, and typography are the primary design decisions. Produces a detailed **Gemini image generation prompt**.

`kv_generator_2` — image-led art director: starts with a single powerful photographic or CGI moment. The typography is designed into the image composition.

Then `kv_image_agent_1` and `kv_image_agent_2` run in parallel:
- Each calls `generate_and_save_kv_image` tool
- Tool sends the image prompt to **Gemini 3 Pro Image (Imagen 4)** via Vertex AI
- Response is a base64 JPEG
- Pillow applies: headline text overlay, brand colour bars, logo placement
- Final image saved to GCS and returned as base64

`kv_ranker` then evaluates both completed concepts and selects the stronger one based on brand alignment and strategic fit.

**What it outputs:** Two `KVConcept` objects each with `image_b64`, `gcs_uri`, plus the ranker's selection

**SSE events:**
```
{ "agent": "kv", "status": "running", "message": "Generating 2 campaign visuals with brand references…" }
{ "agent": "kv", "status": "step_data", "message": "{\"images_b64\": [\"<base64 image 1>\", \"<base64 image 2>\"]}" }
```
Both images arrive simultaneously in `milestones["kv"].images_b64` — the frontend shows a carousel with a variation selector.

---

### Step 7 — Video Reel → **Kinetik** (Veo)
**What receives:** The brand, Big Idea, hero message, season, product name, audience description, GCS bucket config

**What it does:**
- Constructs a Veo 3.1 video prompt from the campaign creative brief
- Submits to `veo-3.1-generate-001` via Vertex AI (starts a long-running operation)
- Polls every 15 seconds for up to 8 minutes
- When complete, downloads the video from GCS and returns `video_b64`

**What it outputs:** A 6-second MP4 campaign reel, base64 encoded

**SSE events:**
```
{ "agent": "reel", "status": "running", "message": "Generating 6-second campaign reel with Veo…" }
{ "agent": "reel", "status": "milestone", "message": "{\"video_b64\": \"<base64 video>\"}" }
{ "agent": "reel", "status": "done", "message": "Campaign reel ready ✓" }
```

---

### Step 8 — Channel Adaptation → **Poly**
**What receives:** The KV hero image + channel list from the brief + copy from Ideon

**What it does:**
- Smart-crops the KV image for every channel's aspect ratio using Pillow:
  - Instagram Feed: 1:1 (1080×1080)
  - Instagram Stories / TikTok: 9:16 (1080×1920)
  - Website Banner: 16:9 (1920×1080)
  - Email Banner: 3:1 (600×200)
- Builds channel-ready content packages (headline + CTA + format specs)
- Stores channel adaptations for the landing page generator

**What it outputs:** `channel_adaptations` dict + `ContentPackage`

**SSE events:**
```
{ "agent": "channel", "status": "running", "message": "Packaging key visual for each channel…" }
{ "agent": "channel", "status": "done", "message": "Campaign ready for 4 channels ✓" }
{ "agent": "channel", "status": "milestone", "message": "{\"instagram\": {...}, \"tiktok\": {...}, \"google\": {...}, \"email\": {...}}" }
```

---

### Step 9 — Pre-Launch Forecast → **Nexus**
**What receives:** `MachineBrief` (includes Fan Truth score) + `CreativeStrategy` + `CampaignCopy` + channel list + `campaign_id`

**What it does:**
- Reads Fan Truth score from `MachineBrief.fan_truth_score.overall`
- Applies adjustments:
  - Fan Truth ≥ 80 → +15% organic reach uplift → `overall_confidence: HIGH`
  - Fan Truth 60–79 → standard benchmarks → `overall_confidence: MEDIUM`
  - Fan Truth < 60 → -20% on all reach forecasts → `overall_confidence: LOW`
- Applies per-channel historical benchmarks (Instagram: CTR 1.8–2.5%, ROAS 2.5–3.5x; TikTok: CTR 2.5–4%, ROAS 2.0–3.0x; Google Ads: CTR 3–6%, ROAS 4–6x)
- Produces channel-level forecasts: reach range, CTR, ROAS, engagement rate, confidence, budget split
- Generates 48h watchlist and top risk/opportunity

**What it outputs:** `PerformanceForecast`
```
headline_prediction: "Strong campaign — Fan Truth 82/100 drives 12.4M estimated reach"
overall_confidence: "HIGH"
predicted_total_reach: "10.2M – 14.6M across 3 channels"
predicted_blended_roas: "3.4x"
channel_forecasts: [
  { channel: "Instagram", predicted_reach: "4.8M–6.2M", predicted_ctr: "2.4%",
    predicted_roas: "3.1x", predicted_engagement: "5.8%", confidence: "HIGH", budget_pct: 0.40 },
  { channel: "TikTok", predicted_reach: "5.4M–8.4M", predicted_ctr: "3.2%",
    predicted_roas: "2.8x", predicted_engagement: "7.2%", confidence: "HIGH", budget_pct: 0.35 }
]
top_risk: "TikTok algorithm volatility during peak summer period"
top_opportunity: "High Fan Truth score enables organic seeding via creator partnership"
first_48h_watchlist: ["Instagram Stories swipe-up rate", "TikTok completion rate", "Google Search CTR"]
recommended_budget_split: { "instagram": 0.40, "tiktok": 0.35, "google": 0.25 }
```

**SSE events:**
```
{ "agent": "performance", "status": "running", "message": "Nexus is forecasting reach, ROAS and channel performance…" }
{ "agent": "performance", "status": "milestone", "message": "{\"headline_prediction\": \"...\", \"channel_forecasts\": [...], ...}" }
{ "agent": "performance", "status": "done", "message": "Forecast ready — HIGH confidence ✓" }
```

---

### Step 10 — Final `__done__` Event
The backend assembles the full result JSON including `machine_brief`, `creative_strategy`, `campaign_copy`, `creative_pipeline`, and `performance_forecast`, and emits the `__done__` event. The frontend closes the SSE connection, sets `status: "done"`, and renders `ResultsView`.

---

## SLIDE 9 — Google Cloud Infrastructure

**[SPEAKER]**

**Vertex AI**
All language model calls go to Vertex AI using the `google-genai` Python SDK with `vertexai=True`. Models used:
- `gemini-3.5-flash` — primary reasoning model for all agents
- `gemini-3-pro-image` (Imagen 4) — key visual generation
- `veo-3.1-generate-001` — 6-second video reel generation
- `gemini-embedding-2` — 768-dimension embeddings for pgvector

**Vertex AI Search**
One Search App with two data sources:
- GCS datastore: `brands/{brand}/Guidelines/brand_guidelines.md` — queried for brand rules
- BigQuery datastore: `briefing_agent.historical_campaigns`, `fan_truth_library`, `channel_benchmarks` — queried for benchmarks

Queries return grounded, summarised results. The search location is `global` (Vertex AI Search requirement). The model inference location is `us-central1`.

**Cloud SQL + pgvector**
PostgreSQL 15 with `pgvector` extension. Tables:
- `audience_profiles` — CDP customer segment records, embedded with Gemini Embedding 2
- `fan_truths` — Fan Truth statement library with scoring examples
- `channel_benchmarks` — per-channel performance data
- `campaign_benchmarks` — historical campaign ROAS and reach data

All data was embedded offline using `setup_pgvector.py` and is queried at runtime via cosine similarity (`<=>` operator).

**BigQuery**
Dataset: `campaign_outputs`. Table: `machine_briefs` — partitioned by DAY on `created_at`. A row is written for every campaign run with the full `MachineBrief` JSON, Fan Truth score, validation score, and brand metadata. Used for analytics, trend monitoring, and future agent training data.

Dataset: `briefing_agent`. Tables: `historical_campaigns`, `fan_truth_library`, `channel_benchmarks` — the source data for Vertex AI Search.

**Cloud Storage**
Bucket: `dauntless-karma-497108-b0-campaignos`
Structure:
```
brands/
  Sunglow/
    Guidelines/brand_guidelines.md
    Logos/sunglow_logo.png
    Products/scalp_oil.jpg
    Assets/campaign_ref_1.jpg
outputs/
  {campaign_id}/
    machine_brief.json
    kv_concept_1.json
    kv_image_1.jpg
```

**Cloud Run**
The harness runs as a containerised FastAPI app on Cloud Run. Deployed via Cloud Build (`cloudbuild.yaml`). Auto-scales to zero when idle. The frontend is served as a static build from a separate Cloud Run container or CDN.

---

## SLIDE 10 — Data Security & Architecture Principles

**[SPEAKER]**

**No model hallucination on brand data**
Brand guidelines, logos, and colour codes are loaded from GCS at the start of every pipeline run — they are never in the model's training data. The `load_brand_context` function node retrieves the current, authoritative guidelines and injects them directly into the agent's context window. Brand locks (font, colours, forbidden words) are enforced at every stage via the `BrandLocks` model passed through the pipeline.

**Structured outputs via Pydantic**
Every agent produces a typed Pydantic model as output. If the LLM returns malformed JSON, `_parse_agent_response()` in `runner.py` strips markdown fences and retries. This means downstream agents always receive clean, typed data — never raw text they need to interpret.

**Fan Truth as a quality gate**
The Fan Truth score is not decorative. It directly governs:
- Whether the brief passes to the creative stage (FAIL → flag, NEEDS_REVIEW status)
- The performance forecast confidence level (≥80 = HIGH, <60 = LOW with -20% reach adjustment)
- The BigQuery audit record for historical analysis

**Fire-and-forget BigQuery logging**
The BigQuery write runs as `asyncio.create_task()` — it never blocks the pipeline. If it fails, a warning is logged but the campaign continues normally.

**SSE vs WebSocket**
We use Server-Sent Events rather than WebSockets. SSE is unidirectional (server → client), simpler to scale on Cloud Run, and automatically handled by the browser's native `EventSource` API with built-in reconnection. No WebSocket upgrade handshake overhead.

---

## SLIDE 11 — Summary: Full Technology Stack

**[SPEAKER]**

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Vite |
| **UI Components** | Custom (no library), CSS keyframe animations |
| **State Management** | React hooks, custom `usePipeline` hook |
| **Real-time streaming** | Server-Sent Events (`EventSource`) |
| **Backend framework** | FastAPI (Python), uvicorn ASGI server |
| **AI agents** | Google ADK 2.0 Workflow DAG |
| **Language models** | Gemini 3.5 Flash (Vertex AI) |
| **Image generation** | Gemini 3 Pro Image / Imagen 4 (Vertex AI) |
| **Video generation** | Veo 3.1 (Vertex AI) |
| **Embeddings** | Gemini Embedding 2 (768 dim, Vertex AI) |
| **Brand intelligence** | Vertex AI Search (GCS + BigQuery datastores) |
| **Audience intelligence** | Cloud SQL + pgvector (cosine similarity) |
| **Audit logging** | BigQuery (`campaign_outputs.machine_briefs`) |
| **Brand assets** | Google Cloud Storage |
| **Image processing** | Pillow (Python) — overlays, smart-crop |
| **Deployment** | Cloud Run + Cloud Build |
| **Package management** | uv (Python), npm (Node) |

---

*CampaignOS — A2A Marketing Intelligence Platform*
*Powered by Infosys Aster × Google Cloud*
