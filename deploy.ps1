# deploy.ps1 - Deploy CampaignOS harness + frontend to Cloud Run
# Usage:
#   .\deploy.ps1              # deploy both
#   .\deploy.ps1 harness      # deploy harness only
#   .\deploy.ps1 frontend     # deploy frontend only

param([string]$Service = "all")

$PROJECT  = "dauntless-karma-497108-b0"
$REGION   = "us-central1"
$REGISTRY = "gcr.io/$PROJECT"

Write-Host "=== CampaignOS Cloud Run Deployment ===" -ForegroundColor Cyan
Write-Host "Project: $PROJECT | Region: $REGION`n"

# ── Read .env file ────────────────────────────────────────────────────────────
function Read-EnvFile {
    $envFile = "harness\.env"
    $vars = @{}
    if (-not (Test-Path $envFile)) { return $vars }
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#')) {
            $idx = $line.IndexOf('=')
            if ($idx -gt 0) {
                $key = $line.Substring(0, $idx).Trim()
                $val = $line.Substring($idx + 1).Trim()
                $vars[$key] = $val
            }
        }
    }
    return $vars
}

# ── Store secrets in Secret Manager ──────────────────────────────────────────
function Set-Secrets {
    Write-Host "Setting up Secret Manager secrets..." -ForegroundColor Yellow
    $env = Read-EnvFile
    $secretKeys = @("GROQ_API_KEY", "PGVECTOR_HOST", "PGVECTOR_PORT", "PGVECTOR_PASSWORD", "PGVECTOR_USER", "PGVECTOR_DB")

    foreach ($key in $secretKeys) {
        if ($env.ContainsKey($key) -and $env[$key]) {
            $val = $env[$key]
            Write-Host "  Storing secret: $key"
            $existing = gcloud secrets describe $key --project=$PROJECT 2>$null
            if ($LASTEXITCODE -eq 0) {
                $val | gcloud secrets versions add $key --data-file=- --project=$PROJECT | Out-Null
            } else {
                $val | gcloud secrets create $key --data-file=- --project=$PROJECT | Out-Null
            }
        }
    }
    Write-Host "  Secrets ready`n" -ForegroundColor Green
}

# ── Deploy Harness ────────────────────────────────────────────────────────────
function Deploy-Harness {
    Write-Host "Deploying harness to Cloud Run..." -ForegroundColor Yellow
    $IMAGE = "$REGISTRY/campaignos-harness:latest"

    Write-Host "  Building Docker image..."
    docker build -t $IMAGE harness/
    if ($LASTEXITCODE -ne 0) { Write-Error "Docker build failed"; exit 1 }

    Write-Host "  Pushing to Container Registry..."
    docker push $IMAGE
    if ($LASTEXITCODE -ne 0) { Write-Error "Docker push failed"; exit 1 }

    Write-Host "  Deploying to Cloud Run..."
    gcloud run deploy campaignos-harness `
        --image $IMAGE `
        --region $REGION `
        --platform managed `
        --allow-unauthenticated `
        --port 8080 `
        --memory 2Gi `
        --cpu 2 `
        --timeout 300 `
        --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=$REGION,BRAND_ASSETS_MODE=gcs,GCS_BUCKET=dauntless-karma-497108-b0-campaignos,SEARCH_MODE=live,SEARCH_ENGINE_ID=campaignos-briefing-search,BQ_DATASET=briefing_agent,BQ_LOGGING_ENABLED=true,ENVIRONMENT=production,LOG_LEVEL=INFO,GEMINI_MODEL_REASONING=groq/llama-3.3-70b-versatile" `
        --set-secrets "GROQ_API_KEY=GROQ_API_KEY:latest,PGVECTOR_HOST=PGVECTOR_HOST:latest,PGVECTOR_PORT=PGVECTOR_PORT:latest,PGVECTOR_PASSWORD=PGVECTOR_PASSWORD:latest" `
        --project $PROJECT

    if ($LASTEXITCODE -ne 0) { Write-Error "Harness deployment failed"; exit 1 }

    $url = gcloud run services describe campaignos-harness --region $REGION --project $PROJECT --format "value(status.url)" 2>$null
    Write-Host "  Harness deployed: $url`n" -ForegroundColor Green
    return $url
}

# ── Deploy Frontend ───────────────────────────────────────────────────────────
function Deploy-Frontend {
    param([string]$HarnessUrl = "")

    Write-Host "Deploying frontend to Cloud Run..." -ForegroundColor Yellow

    if (-not $HarnessUrl) {
        $HarnessUrl = gcloud run services describe campaignos-harness --region $REGION --project $PROJECT --format "value(status.url)" 2>$null
    }

    Write-Host "  Harness API URL: $HarnessUrl"
    $IMAGE = "$REGISTRY/campaignos-frontend:latest"

    Write-Host "  Building Docker image (with VITE_API_URL=$HarnessUrl)..."
    docker build -t $IMAGE --build-arg "VITE_API_URL=$HarnessUrl" frontend/
    if ($LASTEXITCODE -ne 0) { Write-Error "Docker build failed"; exit 1 }

    Write-Host "  Pushing to Container Registry..."
    docker push $IMAGE
    if ($LASTEXITCODE -ne 0) { Write-Error "Docker push failed"; exit 1 }

    Write-Host "  Deploying to Cloud Run..."
    gcloud run deploy campaignos-frontend `
        --image $IMAGE `
        --region $REGION `
        --platform managed `
        --allow-unauthenticated `
        --port 8080 `
        --memory 256Mi `
        --cpu 1 `
        --project $PROJECT

    if ($LASTEXITCODE -ne 0) { Write-Error "Frontend deployment failed"; exit 1 }

    $url = gcloud run services describe campaignos-frontend --region $REGION --project $PROJECT --format "value(status.url)" 2>$null
    Write-Host "  Frontend deployed: $url`n" -ForegroundColor Green
    return $url
}

# ── Main ──────────────────────────────────────────────────────────────────────
Set-Secrets

$harnessUrl  = ""
$frontendUrl = ""

if ($Service -eq "all" -or $Service -eq "harness") {
    $harnessUrl = Deploy-Harness
}

if ($Service -eq "all" -or $Service -eq "frontend") {
    $frontendUrl = Deploy-Frontend -HarnessUrl $harnessUrl
}

Write-Host "=== Deployment Complete ===" -ForegroundColor Green
if ($harnessUrl)  { Write-Host "Harness:  $harnessUrl"  -ForegroundColor Cyan }
if ($frontendUrl) { Write-Host "Frontend: $frontendUrl" -ForegroundColor Cyan }
