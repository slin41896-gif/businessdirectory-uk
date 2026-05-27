# deploy-main.ps1 — 本機直接部署 businessdirectory-uk.com 主站到 CF Pages
#
# 使用方式：
#   cd C:\Users\chenc\Documents\Claude Wmzic\businessdirectory-uk\landing
#   $env:CF_API_TOKEN = "your-token"; .\deploy-main.ps1
#
# 或直接傳入 token：
#   $env:CF_API_TOKEN = "xxx"; $env:CF_ACCOUNT_ID = "xxx"; .\deploy-main.ps1
#
# CF Pages project name：businessdirectory-uk（需已在 CF Dashboard 建立）

param(
    [string]$ProjectName = "businessdirectory-uk",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

# 確認 token
if (-not $env:CF_API_TOKEN) {
    Write-Error "Missing CF_API_TOKEN. Set: `$env:CF_API_TOKEN = 'your-token'"
    exit 1
}
if (-not $env:CF_ACCOUNT_ID) {
    Write-Error "Missing CF_ACCOUNT_ID. Set: `$env:CF_ACCOUNT_ID = 'your-account-id'"
    exit 1
}

$LandingDir = $PSScriptRoot

Write-Host "Deploying $LandingDir → CF Pages project: $ProjectName" -ForegroundColor Cyan

$env:CLOUDFLARE_API_TOKEN = $env:CF_API_TOKEN
$env:CLOUDFLARE_ACCOUNT_ID = $env:CF_ACCOUNT_ID

npx wrangler pages deploy $LandingDir `
    --project-name $ProjectName `
    --branch $Branch `
    --commit-dirty=true

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deploy complete: https://$ProjectName.pages.dev" -ForegroundColor Green
} else {
    Write-Error "Deploy failed (exit code $LASTEXITCODE)"
    exit $LASTEXITCODE
}
