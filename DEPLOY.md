# AI Automation Suite - Deployment Guide

## Step 1: Set Up Neon Database (Manual - 2 minutes)

1. Go to https://vercel.com/dashboard
2. Click **Integrations** → **Marketplace** → Search **"Neon Postgres"**
3. Click **Install** → Choose **Vercel-Managed**
4. Select all projects when prompted
5. Neon auto-creates DB and injects `DATABASE_URL` env var

## Step 2: Run Database Schema

Go to Neon Dashboard (from Vercel integration) → SQL Editor → Paste contents of `schema.sql` → Run

## Step 3: Deploy Each API

For each project (chatbot-api, lead-api, document-api, appointment-api, report-api):

```powershell
cd ai-automation-suite\<project-name>
vercel --yes --prod
```

## Step 4: Set Environment Variables

After deploying each project, set these env vars:

```powershell
cd ai-automation-suite\<project-name>
echo "sk-e7fd3c4129794bbc82ff30493cda2248" | vercel env add DEEPSEEK_API_KEY production
echo "rush-key-2026" | vercel env add API_KEY production
```

Note: `DATABASE_URL` is auto-set by Neon integration.

## Step 5: Update Portfolio

1. Clone your portfolio repo (if not already local):
```powershell
git clone https://github.com/emmanalcazarjr-ops/portfolio.git C:\Users\Emman\OneDrive\Desktop\AI\portfolio
```

2. Copy RushChatbot.tsx to portfolio components:
```powershell
Copy-Item ai-automation-suite\portfolio-components\RushChatbot.tsx C:\Users\Emman\OneDrive\Desktop\AI\portfolio\app\components\
```

3. Follow instructions in `portfolio-components\portfolio-updates.tsx` to add project cards and demos to `page.tsx`

4. Push portfolio:
```powershell
cd C:\Users\Emman\OneDrive\Desktop\AI\portfolio
git add -A
git commit -m "Add AI Automation Suite - Rush chatbot + 5 new APIs"
git push
```

## Expected Vercel URLs

| Project | URL |
|---------|-----|
| chatbot-api | https://chatbot-api.vercel.app |
| lead-api | https://lead-api.vercel.app |
| document-api | https://document-api.vercel.app |
| appointment-api | https://appointment-api.vercel.app |
| report-api | https://report-api.vercel.app |

## API Key

All APIs use: `rush-key-2026`

Header: `Authorization: Bearer rush-key-2026`

## Quick Deploy Script (PowerShell)

```powershell
$projects = @("chatbot-api", "lead-api", "document-api", "appointment-api", "report-api")

foreach ($project in $projects) {
    Write-Host "Deploying $project..." -ForegroundColor Cyan
    cd "ai-automation-suite\$project"
    vercel --yes --prod
    echo "sk-e7fd3c4129794bbc82ff30493cda2248" | vercel env add DEEPSEEK_API_KEY production 2>$null
    echo "rush-key-2026" | vercel env add API_KEY production 2>$null
    cd ..\..
    Write-Host "$project deployed!" -ForegroundColor Green
}
```
