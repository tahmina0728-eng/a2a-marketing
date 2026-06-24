# CampaignOS — GCP Migration Guide

**Source project:** `dauntless-karma-497108-b0`
**Target:** Organisation GCP account (new project)

---

## Table of Contents

1. [GCP Services Overview](#1-gcp-services-overview)
2. [Cloud Run](#2-cloud-run)
3. [Cloud Build](#3-cloud-build)
4. [Cloud Storage (GCS)](#4-cloud-storage-gcs)
5. [BigQuery](#5-bigquery)
6. [Cloud SQL](#6-cloud-sql)
7. [Vertex AI](#7-vertex-ai)
8. [Secret Manager](#8-secret-manager)
9. [Container Registry (GCR)](#9-container-registry-gcr)
10. [IAM](#10-iam)
11. [APIs to Enable](#11-apis-to-enable)
12. [External Services (Non-GCP)](#12-external-services-non-gcp)
13. [Running Without Docker](#13-running-without-docker)
14. [Migration Checklist](#14-migration-checklist)

---

## 1. GCP Services Overview

| Service | Used for |
|---|---|
| Cloud Run | Host FastAPI backend + React frontend |
| Cloud Build | CI/CD — build Docker image, push to GCR, deploy to Cloud Run |
| Cloud Storage | Brand assets, generated images, videos, landing pages |
| BigQuery | Campaign audit logging, source data (benchmarks, Fan Truths) |
| Cloud SQL | PostgreSQL + pgvector for semantic search |
| Vertex AI (Gemini) | Text generation, image generation |
| Vertex AI (Veo) | Campaign reel video generation |
| Vertex AI (Embeddings) | 768-dim vectors for pgvector semantic search |
| Vertex AI Search | Brand guidelines + BigQuery data search engine |
| Secret Manager | API keys, access tokens, credentials |
| Container Registry | Docker image storage |

---

## 2. Cloud Run

### Services deployed

#### `campaignos-harness` (FastAPI backend)

| Setting | Value |
|---|---|
| Region | `us-central1` |
| Image | `gcr.io/dauntless-karma-497108-b0/campaignos-harness:latest` |
| Memory | 4Gi |
| CPU | 2 |
| Timeout | 3600s |
| Concurrency | 10 |
| Auth | `--allow-unauthenticated` |
| Service URL | `https://campaignos-harness-958438970145.us-central1.run.app` |
| Service account | `958438970145-compute@developer.gserviceaccount.com` (default Compute Engine SA) |
| Cloud SQL | Attached via Unix socket: `dauntless-karma-497108-b0:us-central1:campaignos-pgvector` |

#### `campaignos-frontend` (React/Vite UI)

| Setting | Value |
|---|---|
| Region | `us-central1` |
| Image | `gcr.io/dauntless-karma-497108-b0/campaignos-frontend:latest` |
| Memory | 256Mi |
| CPU | 1 |
| Build arg | `VITE_API_URL` → harness Cloud Run URL |

### Environment variables injected into `campaignos-harness`

```
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GCS_BUCKET=dauntless-karma-497108-b0-campaignos
BRAND_ASSETS_MODE=gcs
SEARCH_MODE=live
SEARCH_ENGINE_ID=campaignos-briefing-search
SEARCH_LOCATION=global
GEMINI_MODEL_REASONING=gemini-3.5-flash
CREATIVE_MODEL=gemini-3.5-flash
GEMINI_MODEL_IMAGE=gemini-3-pro-image
GEMINI_MODEL_IMAGE_ADAPTER=gemini-3-pro-image
VEO_MODEL=veo-3.1-generate-001
REEL_ENABLED=true
USE_GEMINI_EMBEDDINGS=true
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
PGVECTOR_HOST=/cloudsql/dauntless-karma-497108-b0:us-central1:campaignos-pgvector
PGVECTOR_PORT=5432
PGVECTOR_USER=campaignos
PGVECTOR_DB=marketing
PGVECTOR_PASSWORD=campaignos123
BQ_DATASET=briefing_agent
BQ_OUTPUT_DATASET=campaign_outputs
BQ_LOGGING_ENABLED=true
ENVIRONMENT=production
LOG_LEVEL=INFO
HARNESS_URL=https://campaignos-harness-958438970145.us-central1.run.app
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM_NAME=CampaignOS
INSTAGRAM_BUSINESS_ACCOUNT_ID=17841415786098555
META_APP_ID=2002436330660173
```

### Secrets injected (from Secret Manager)

```
GROQ_API_KEY=GROQ_API_KEY:latest
GOOGLE_API_KEY=GOOGLE_EMBEDDING_KEY:latest
EMAIL_APP_PASSWORD=EMAIL_APP_PASSWORD:latest
EMAIL_FROM=EMAIL_FROM:latest
INSTAGRAM_ACCESS_TOKEN=INSTAGRAM_ACCESS_TOKEN:latest
```

---

## 3. Cloud Build

- **Config file:** `harness/cloudbuild.yaml`
- **Build machine:** `E2_HIGHCPU_8`
- **Logging:** `CLOUD_LOGGING_ONLY` (Cloud Logging)
- **Steps:**
  1. `docker build -t gcr.io/$PROJECT_ID/campaignos-harness:latest .`
  2. `docker push gcr.io/$PROJECT_ID/campaignos-harness:latest`
  3. `gcloud run deploy campaignos-harness ...` (with all env vars and secrets above)

---

## 4. Cloud Storage (GCS)

**Bucket name:** `dauntless-karma-497108-b0-campaignos`
**Region:** `us-central1`
**Access:** Uniform Bucket-Level Access (UBA) — public read (`allUsers: roles/storage.objectViewer`)

### Folder structure

```
brands/
  {brand}/
    Guidelines/
      brand_guidelines.md        ← indexed by Vertex AI Search
    Logos/                       ← brand logo files (PNG/SVG)
    Products/                    ← product images
    Font/                        ← TTF brand font files (used by Pillow for KV overlay)
    Assets/                      ← reference campaign images (passed to Gemini as context)
    Colours/                     ← colour swatch images

outputs/
  {campaign_id}/
    kv_image_1.jpg               ← generated KV image concept 1
    kv_image_2.jpg               ← generated KV image concept 2
    channels/
      {channel}.jpg              ← channel-adapted images (instagram_feed, tiktok, etc.)
    landing.html                 ← brand landing page (persisted across Cloud Run restarts)
    reel.mp4                     ← Veo-generated campaign reel
    reel_retry.mp4               ← Veo retry output (fallback path)
```

### How it is used

| Code location | Usage |
|---|---|
| `app/brand_assets.py` | Reads guidelines, lists logos/products/assets |
| `app/runner.py` | Uploads KV images + channel adaptations; reads reel MP4 |
| `main.py` | Uploads/downloads landing pages; uploads Instagram images; reads logos |
| `app/creative_pipeline.py` | Reads brand asset images as multimodal Gemini inputs |

---

## 5. BigQuery

### Dataset: `briefing_agent` (region: `US`)

Source/reference data loaded at runtime.

| Table | Contents |
|---|---|
| `historical_campaigns` | Brand/product/market/season campaign performance history |
| `fan_truth_library` | Fan Truth examples with PASS/FAIL scores (specific/shared/special) |
| `channel_benchmarks` | Per-channel CTR, CPM, engagement, completion benchmarks |

### Dataset: `campaign_outputs` (region: `US`)

Pipeline audit log — one row per run.

| Table | Contents |
|---|---|
| `machine_briefs` | campaign_id, brand, market, product_category, season, channels, validation_score, fan_truth_score, brief_json (up to 50KB) — time-partitioned by `created_at` |

### Access

- Library: `google-cloud-bigquery >= 3.41.0`
- Client: `google.cloud.bigquery.Client(project=GCP_PROJECT)`
- Writes: `insert_rows_json` (fire-and-forget, non-blocking)
- Config: `BQ_LOGGING_ENABLED=true` to enable writes

---

## 6. Cloud SQL

| Setting | Value |
|---|---|
| Instance name | `campaignos-pgvector` |
| Full connection name | `dauntless-karma-497108-b0:us-central1:campaignos-pgvector` |
| Engine | PostgreSQL 16 + `pgvector` extension |
| Region | `us-central1` |
| Database | `marketing` |
| User | `campaignos` |
| Password | `campaignos123` (**hardcoded in cloudbuild.yaml — move to Secret Manager in new project**) |
| Production connection | Unix socket via `--add-cloudsql-instances` in Cloud Run |
| Local dev connection | TCP `127.0.0.1:5433` (Cloud SQL Auth Proxy or local pgvector container) |

### Tables

All tables have HNSW vector indexes with `vector_cosine_ops` (768 dimensions).

| Table | Contents |
|---|---|
| `fan_truths` | Fan Truth examples with embeddings |
| `campaign_benchmarks` | Historical campaign performance with embeddings |
| `channel_benchmarks` | Per-channel performance data with embeddings |
| `customer_segments` | Synthetic CDP customer segments with embeddings |
| `customer_insights` | Kaggle CDP real data with embeddings |
| `brand_guidelines_chunks` | Chunked brand guidelines for RAG search |

### Setup scripts

- `harness/scripts/setup_pgvector.py` — creates extension + tables
- Seed scripts in `harness/scripts/` — populate data and generate embeddings

---

## 7. Vertex AI

### 7a. Gemini — Text Generation

All called via `genai.Client(vertexai=True, project=..., location=...)` using `client.models.generate_content()`.

| Env var | Model | Used for |
|---|---|---|
| `GEMINI_MODEL_REASONING` | `gemini-3.5-flash` | Brief validation, strategy, copy, forecast, Veo prompt |
| `CREATIVE_MODEL` | `gemini-3.5-flash` | Creative pipeline (culture research, brand summarizer, creative director) |
| Fallback | `gemini-2.0-flash` | Auto-fallback on 429 / rate limit |

### 7b. Gemini — Image Generation

| Env var | Model | Used for |
|---|---|---|
| `GEMINI_MODEL_IMAGE` | `gemini-3-pro-image` | KV image generation with multimodal brand photo references |
| `GEMINI_MODEL_IMAGE_ADAPTER` | `gemini-3-pro-image` | Channel adaptation image resizing |

Called via `client.models.generate_content()` with `response_modalities=["IMAGE", "TEXT"]` and `ImageConfig(aspect_ratio="16:9")`.

**Note:** `gemini-3-pro-image` is a Preview model with ~1 RPM quota. Images are generated sequentially with a 65s gap between concepts to avoid quota exhaustion.

### 7c. Veo — Video Generation

| Env var | Model | Used for |
|---|---|---|
| `VEO_MODEL` | `veo-3.1-generate-001` | 6-second campaign reel, 16:9, with audio |

- Called via `client.models.generate_videos()` with `GenerateVideosConfig`
- Output written directly to GCS: `gs://{bucket}/outputs/{campaign_id}/reel.mp4`
- Polled up to 8 minutes for completion
- 429 retry: 60s wait then retry once
- Self-service quota increase: **capped at 1 req/min** on `us-central1` — increase requires Google Cloud Sales contact

### 7d. Gemini Embeddings

| Env var | Model | Used for |
|---|---|---|
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-2` | 768-dim vectors for pgvector semantic search |

**Important:** Uses **Google AI API endpoint** (`vertexai=False`), NOT Vertex AI. Requires a separate `GOOGLE_API_KEY` (mapped from Secret Manager secret `GOOGLE_EMBEDDING_KEY`).

### 7e. Vertex AI Search (Discovery Engine)

| Setting | Value |
|---|---|
| Search engine ID | `campaignos-briefing-search` |
| Location | `global` |
| Library | `google-cloud-discoveryengine >= 0.13.12, < 0.14.0` |

**Two datastores:**

| Datastore | Source |
|---|---|
| `campaignos-brand-guidelines` (GCS unstructured) | `gs://{bucket}/brands/*/Guidelines/*.md` |
| BigQuery structured | `briefing_agent.historical_campaigns`, `fan_truth_library`, `channel_benchmarks` |

Used by `app/search_client.py` for: brand rules, Fan Truth examples, campaign benchmarks, channel benchmarks, moment type rules.

### 7f. Google ADK

- Version: `google-adk==2.0.0b1`
- Session service: `InMemorySessionService` (no Firestore/Vertex AI session persistence)
- `google.adk.tools.google_search` used in `creative_pipeline.py` (culture researcher agent)

---

## 8. Secret Manager

Stored in source project `dauntless-karma-497108-b0`. Must be re-created in new project.

| Secret name | Env var in Cloud Run | Purpose |
|---|---|---|
| `GROQ_API_KEY` | `GROQ_API_KEY` | Groq API key (alternative LLM backend) |
| `GOOGLE_EMBEDDING_KEY` | `GOOGLE_API_KEY` | Google AI API key for `gemini-embedding-2` |
| `EMAIL_APP_PASSWORD` | `EMAIL_APP_PASSWORD` | Gmail SMTP app password |
| `EMAIL_FROM` | `EMAIL_FROM` | From address for campaign emails |
| `INSTAGRAM_ACCESS_TOKEN` | `INSTAGRAM_ACCESS_TOKEN` | Meta Instagram Graph API long-lived token |

---

## 9. Container Registry (GCR)

| Image | Purpose |
|---|---|
| `gcr.io/dauntless-karma-497108-b0/campaignos-harness:latest` | FastAPI backend |
| `gcr.io/dauntless-karma-497108-b0/campaignos-frontend:latest` | React/Vite frontend |

In the new project, images are automatically pushed to `gcr.io/{NEW_PROJECT_ID}/...` when Cloud Build runs.

---

## 10. IAM

### Service account (production)

Currently uses the **default Compute Engine service account**: `958438970145-compute@developer.gserviceaccount.com`.

For the new project, create a named service account (e.g., `campaignos-sa@{NEW_PROJECT_ID}.iam.gserviceaccount.com`) and grant:

| Role | Purpose |
|---|---|
| `roles/aiplatform.user` | Vertex AI — Gemini, Veo, Vertex AI Search |
| `roles/bigquery.dataEditor` | Read/write BigQuery tables |
| `roles/bigquery.jobUser` | Run BigQuery jobs |
| `roles/storage.objectAdmin` | Read/write GCS bucket |
| `roles/secretmanager.secretAccessor` | Read secrets at runtime |
| `roles/cloudsql.client` | Connect to Cloud SQL via socket |
| `roles/run.invoker` | Allow Cloud Run to invoke other services |

### GCS bucket IAM (public read)

```bash
gcloud storage buckets add-iam-policy-binding gs://{NEW_BUCKET} \
  --member=allUsers \
  --role=roles/storage.objectViewer
```

---

## 11. APIs to Enable

Run in new project:

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  discoveryengine.googleapis.com \
  containerregistry.googleapis.com
```

---

## 12. External Services (Non-GCP)

These are not migrated — they exist outside GCP but need credentials updated in Secret Manager.

| Service | Details |
|---|---|
| **Instagram Graph API (Meta)** | Account ID: `17841415786098555`, App ID: `2002436330660173`, long-lived token in Secret Manager. Token expires every ~60 days — refresh via Meta Graph API Explorer. |
| **Gmail SMTP** | `smtp.gmail.com:587`, app password stored in Secret Manager |
| **Groq API** | Alternative LLM backend, key in Secret Manager |

---

## 13. Running Without Docker

Docker is only required for Cloud Run deployment. Local development and all migration setup scripts run directly with `uv`.

### Local dev

```bash
cd harness

# One-time: install uv
pip install uv

# Install dependencies from pyproject.toml + uv.lock
uv sync

# Run the server (reads harness/.env automatically)
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### Run setup/seed scripts

```bash
cd harness
uv run python scripts/setup_bigquery.py
uv run python scripts/setup_pgvector.py
uv run python scripts/setup_search.py
uv run python scripts/index_brand_assets.py
uv run python scripts/index_gcs_guidelines.py
```

### Cloud SQL locally (without Docker)

Use [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/postgres/sql-proxy) to tunnel the Cloud SQL instance to a local TCP port:

```bash
./cloud-sql-proxy {NEW_PROJECT_ID}:us-central1:campaignos-pgvector --port 5433
```

Then `.env` points to `127.0.0.1:5433` as normal.

### System dependencies (Windows)

Pillow bundles libjpeg/zlib on Windows — the system packages installed in the Dockerfile (`libjpeg-dev`, `zlib1g-dev`, `libfreetype6-dev`) are Linux-only and not needed locally.

---

## 14. Migration Checklist

### Step 1 — New GCP project setup

- [ ] Create new GCP project in organisation account
- [ ] Enable all APIs listed in Section 11
- [ ] Create service account `campaignos-sa` with all IAM roles in Section 10
- [ ] Link billing account

### Step 2 — Cloud Storage

- [ ] Create new GCS bucket: `{NEW_PROJECT_ID}-campaignos` (or preferred name) in `us-central1`
- [ ] Enable Uniform Bucket-Level Access
- [ ] Grant `allUsers: roles/storage.objectViewer`
- [ ] Copy all `brands/` assets from old bucket:
  ```bash
  gcloud storage cp -r gs://dauntless-karma-497108-b0-campaignos/brands gs://{NEW_BUCKET}/brands
  ```

### Step 3 — Cloud SQL

- [ ] Create new PostgreSQL 16 instance with `pgvector` extension in `us-central1`
- [ ] Create database `marketing`, user `campaignos`
- [ ] Store password in Secret Manager (do **not** hardcode in cloudbuild.yaml)
- [ ] Run `uv run python scripts/setup_pgvector.py` against new instance
- [ ] Run seed scripts to populate and embed data

### Step 4 — BigQuery

- [ ] Run `uv run python scripts/setup_bigquery.py` in new project
- [ ] Verify datasets `briefing_agent` and `campaign_outputs` created in `US` region
- [ ] Seed `historical_campaigns`, `fan_truth_library`, `channel_benchmarks`

### Step 5 — Vertex AI Search

- [ ] Run `uv run python scripts/setup_search.py` to create engine + datastores
- [ ] Run `uv run python scripts/index_brand_assets.py`
- [ ] Run `uv run python scripts/index_gcs_guidelines.py`
- [ ] Verify search engine ID in new project (update `SEARCH_ENGINE_ID` env var if different)

### Step 6 — Secret Manager

Re-create all 5 secrets with real values:

- [ ] `GROQ_API_KEY`
- [ ] `GOOGLE_EMBEDDING_KEY` (Google AI API key for embeddings)
- [ ] `EMAIL_APP_PASSWORD`
- [ ] `EMAIL_FROM`
- [ ] `INSTAGRAM_ACCESS_TOKEN`
- [ ] `PGVECTOR_PASSWORD` (move from plain env var to secret)

### Step 7 — Update project references in code

Search and replace `dauntless-karma-497108-b0` in:

| File | What to update |
|---|---|
| `harness/cloudbuild.yaml` | GCS bucket name, Cloud SQL instance name, harness URL, `PGVECTOR_HOST` |
| `harness/scripts/setup_search.py` | Project ID, bucket name |
| `harness/scripts/setup_bigquery.py` | Project ID |
| `infra/setup_gcp.sh` | Project ID, bucket name |

Also update:
- `HARNESS_URL` env var in `cloudbuild.yaml` (new Cloud Run URL, known after first deploy)
- `VITE_API_URL` build arg in frontend Cloud Build / deploy config

### Step 8 — Cloud Build + Cloud Run

- [ ] Connect new project's Cloud Build to the GitHub repo
- [ ] Trigger Cloud Build — images pushed to new project's GCR automatically
- [ ] Verify Cloud Run services start and health check passes
- [ ] Update `harness/.env` with new project ID, bucket name, Cloud SQL connection for local dev

### Step 9 — Post-migration verification

- [ ] Run a full campaign end-to-end (brief → strategy → KV images → reel → landing page)
- [ ] Verify Instagram publishing works (token is project-agnostic — same token works)
- [ ] Check BigQuery `machine_briefs` receives rows
- [ ] Check GCS `outputs/` receives generated files
- [ ] Verify landing page hero image loads (public GCS HTTPS URL)
