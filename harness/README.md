# CampaignOS — ADK 2.0

Multi-agent marketing pipeline built on Google ADK 2.0. Takes a campaign brief and produces validated, brand-compliant key visuals through a Workflow DAG with human-in-the-loop gates.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — fast Python package manager
- A GCP project with ADC configured (`gcloud auth application-default login`)

---

## Setup

### 1. Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your shell after installing. Verify with `uv --version`.

### 2. Sync the environment

Run from the **`harness/` directory** (where `pyproject.toml` lives):

```bash
cd harness
uv sync
```

This creates a `.venv`, pins all dependencies from `pyproject.toml`, and installs them. You never need to activate the venv manually — prefix commands with `uv run` and it is used automatically.

> **ADK version lock:** `google-adk` is pinned to `2.0.0b1` in `pyproject.toml`. Do not upgrade — later versions contain a bug that breaks the graph visualisation in `adk web`. This pin will be lifted once a stable release ships with the fix.

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your values. Minimum required for local dev:

| Variable | Notes |
|---|---|
| `GCP_PROJECT` | Your GCP project ID |
| `GCS_BUCKET` | Bucket holding brand assets |
| `BRAND_ASSETS_MODE` | `local` to use `bucket/` folder, `gcs` to read from GCS |
| `SEARCH_MODE` | `gcs_files` (stubs benchmarks) until Vertex AI Search is set up |
| `BQ_LOGGING_ENABLED` | `false` until BigQuery tables are provisioned |

---

## Running the ADK web UI

The ADK web UI lets you chat with the agent, inspect session state step-by-step, and view generated images in the Artifacts panel.

**Always uv run from `harness/`** — the directory that contains the `app/` folder:

```bash
cd harness
uv run adk web .
```

Then open `http://localhost:8000`.

### Why `harness/` specifically?

`adk web` discovers agents by scanning for subdirectories that contain an `agent.py` file. `app/agent.py` exists purely for this purpose — it re-exports `root_agent` so the full Workflow DAG is visible in the UI:

```python
# app/agent.py
from app.pipeline import root_agent  # noqa: F401
```

Running from `harness/` means `adk web .` finds `app/agent.py` at exactly one level down. Running from the workspace root would miss it.

### Cloud Shell

Cloud Shell only exposes port 8080 through its web preview. Use this command instead:

```bash
cd harness
uv run adk web --port 8080 --allow_origins "regex:https://.*\.cloudshell\.dev"
```

Then click the **Web Preview** button in Cloud Shell and select port 8080.

---

## Project layout

```
harness/
├── app/
│   ├── agent.py          ← adk web entry point — re-exports root_agent
│   ├── agents.py         ← all ADK Agent instances
│   ├── pipeline.py       ← Workflow DAG (root_agent + briefing_pipeline)
│   ├── nodes.py          ← deterministic function nodes (zero LLM cost)
│   ├── tools.py          ← async tools that require ToolContext
│   ├── instructions.py   ← all agent instruction strings
│   ├── models.py         ← Pydantic models
│   ├── config.py         ← settings via pydantic-settings (reads .env)
│   ├── brand_assets.py   ← brand asset loader (local and GCS backends)
│   ├── data_loader.py    ← BigQuery audit log writer
│   └── search_client.py  ← Vertex AI Search client
├── main.py               ← FastAPI app (POST /brief, POST /pipeline)
├── pyproject.toml        ← dependencies and uv config
├── .env.example          ← config template — copy to .env
└── bucket/               ← local brand asset store (mirrors GCS structure)
    └── brands/
        └── {BrandName}/
            ├── Guidelines/brand_guidelines.md
            ├── Products/
            ├── Font/
            ├── Logos/
            └── Assets/
```

---

## Pipeline overview

```
load_brand_context  (function node — zero LLM)
  └── briefing_agent
        └── HITL brief approval
              └── strategy_agent
                    ├── kv_generator_1 → kv_image_agent_1 → copy_renderer_1 → kv_swap_agent_1 ─┐
                    ├── kv_generator_2 → kv_image_agent_2 → copy_renderer_2 → kv_swap_agent_2  ├─ aggregate_kv_concepts
                    ├── kv_generator_3 → kv_image_agent_3 → copy_renderer_3 → kv_swap_agent_3  │      └── kv_ranker
                    └── kv_generator_4 → kv_image_agent_4 → copy_renderer_4 → kv_swap_agent_4 ─┘            └── HITL KV selection
                                                                                                                    └── channel_router → content_agent → execution_agent
                                                                                                                                              └── aggregation_agent → performance_agent
```

**KV image pipeline — 3 stages per branch:**

1. **`kv_image_agent_N`** — Gemini text-to-image; actual product photos are passed as multi-modal inputs so the model sees real photography rather than inferring from text
2. **`copy_renderer_N`** — Pillow flat text overlay (headline, brand name, tagline) using the brand font → pixel-precise positional stencil `kv_ref_N.png`
3. **`kv_swap_agent_N`** — Nano Banana 2 (Gemini image-to-image); re-renders the flat Pillow text into the scene with lighting, shadow, and material integration → `kv_final_N.png`

---

## Adding a new brand

1. Create `bucket/brands/{BrandName}/` with the folder structure above
2. Add `Guidelines/brand_guidelines.md` — include a YAML block with brand lock values
3. Drop product images into `Products/` and font files into `Font/`
4. Set `BRAND_ASSETS_MODE=local` in `.env`
5. Submit a brief with `"brand": "{BrandName}"` — `load_brand_context` picks everything up automatically

---

## FastAPI routes

```bash
uv run uvicorn main:app --reload
```

| Route | What it runs |
|---|---|
| `POST /brief` | `load_brand_context` + `briefing_agent` — fast brief validation only |
| `POST /pipeline` | Full Workflow DAG including KV generation and all HITL gates |
| `GET /health` | Liveness probe |
| `GET /readiness` | Readiness probe |
| `POST /refresh` | Re-init the Vertex AI Search client after data changes |

---

## ADK 2.0 features in use

### Workflow DAG

The pipeline is defined as a `Workflow` with explicit edge tuples. ADK resolves the graph, handles fan-out/fan-in, and runs parallel branches concurrently without any threading code.

```python
root_agent = Workflow(
    name  = "campaignos_pipeline",
    edges = [
        ("START", load_brand_context, briefing_agent, ...),
        (strategy_agent, kv_generator_1),  # fan-out
        (strategy_agent, kv_generator_2),
        ...
        (kv_swap_agent_1, kv_join_node),   # fan-in
        ...
    ],
)
```

### Function nodes (zero LLM cost)

`load_brand_context` and `aggregate_kv_concepts` are plain Python functions registered as graph nodes. They run deterministically with no model call, no latency, and no token cost.

`load_brand_context` loads brand guidelines, product image map, font paths, and benchmark data before any LLM agent runs. This means no agent ever needs to call a data-loading tool — the context is already in state.

### Session state injection

Agent instruction strings use `{key_name}` placeholders that ADK resolves from session state at call time. This is how brand context propagates to all parallel KV generator branches without passing it through the graph edges:

```python
# In load_brand_context:
return Event(
    output = briefing_context,
    state  = {
        "brand_guidelines":  brand_guidelines,
        "brand_name":        brand,
        "brand_locks_json":  json.dumps(brand_locks_dict),
        "product_image_map": json.dumps(product_image_map),
        ...
    },
)

# In KV_GENERATOR_INSTRUCTIONS:
# "Brand: {brand_name}  ·  Guidelines: {brand_guidelines}"
```

### JoinNode fan-in

`JoinNode` blocks until all four parallel branches (`kv_swap_agent_1..4`) complete before releasing to `aggregate_kv_concepts`. No polling or manual synchronisation.

### ADK Artifact Service

All generated images (`kv_image_N.png`, `kv_ref_N.png`, `kv_final_N.png`) and the machine brief JSON are saved via `tool_context.save_artifact(filename, Part.from_bytes(...))`.

- In development (`adk web`) they are stored in-memory and visible in the **Artifacts** panel in the UI
- In production the exact same code writes to the configured GCS bucket — no code changes needed between environments
- ADK versions each save automatically, so re-runs produce `v1`, `v2`, ... of the same key

Artifacts are loaded in subsequent stages with `tool_context.load_artifact(filename)` — the copy renderer and swap agent never touch GCS URIs directly.

### HITL gates

Two `Agent` nodes act as human-in-the-loop suspension points:

- `hitl_brief_approval` — presents the validated brief and waits for `APPROVE` before strategy begins
- `hitl_kv_selection` — presents all four ranked key visual concepts and waits for a selection

The graph suspends at these nodes and resumes when the user replies in the `adk web` chat. Cross-request HITL persistence requires `VertexAiSessionService`; `InMemorySessionService` is used for local dev.

### Single-turn agents

Tool-calling agents (`kv_image_agent_N`, `copy_renderer_N`, `kv_swap_agent_N`, `briefing_agent`) are set to `mode="single_turn"` so they call their tool exactly once and return. This prevents the model from looping or re-calling tools unnecessarily.

### output_key state capture

Agents with `output_key="kv_concept_N"` write their final response directly to session state. This is how the kv_image and kv_swap agents enrich the concept JSON with `image_artifact_key` and make it available to downstream agents and `aggregate_kv_concepts` via state injection.

### Environment-agnostic asset loading

`brand_assets.py` implements a `BrandAssetLoader` with local and GCS backends behind a single interface. Switching between them is one env var: `BRAND_ASSETS_MODE=local|gcs`. The same interface is used to load brand fonts for the Pillow copy renderer.