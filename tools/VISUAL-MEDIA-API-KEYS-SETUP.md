# Visual Media Generator - API Keys Setup Guide

**Date**: 2025-11-03
**Purpose**: Configure API keys for all image/video generation providers

---

## Quick Status Check

Run this command to see what's already configured:

```bash
echo "=== Current API Key Status ==="
echo "OpenAI (DALL-E 3, Sora 2): $([ -n "$OPENAI_API_KEY" ] && echo '✅ Configured' || echo '❌ Missing')"
echo "Together AI (Flux Schnell FREE): $([ -n "$TOGETHER_API_KEY" ] && echo '✅ Configured' || echo '❌ Missing')"
echo "Replicate (Flux Dev): $([ -n "$REPLICATE_API_KEY" ] && echo '✅ Configured' || echo '❌ Missing')"
echo "Fal.ai (Flux Pro): $([ -n "$FAL_API_KEY" ] && echo '✅ Configured' || echo '❌ Missing')"
echo "Google Cloud (Imagen/nano banana): $([ -n "$GOOGLE_API_KEY" ] && echo '✅ Configured' || echo '❌ Missing')"
echo "Stability AI (SD3): $([ -n "$STABILITY_API_KEY" ] && echo '✅ Configured' || echo '❌ Missing')"
```

---

## Priority Setup Order

### 🚀 Tier 1 - Start Here (FREE Testing)

**1. Together AI** - Get FREE Flux Schnell generations
- **Cost**: FREE tier available
- **Why first**: Test image generation at no cost
- **Models**: Flux Schnell (ultra-fast, free)

### 💎 Tier 2 - Production Quality

**2. Replicate** - Best value for production
- **Cost**: Pay-as-you-go, ~$0.025/image
- **Why**: Excellent quality, reasonable pricing
- **Models**: Flux Dev, Flux Pro, SDXL

**3. Fal.ai** - Fastest inference
- **Cost**: ~$0.05/image for Flux Pro
- **Why**: Fastest Flux Pro variant
- **Models**: Flux Pro (fastest), Flux Schnell, SD3

### 🏢 Tier 3 - Enterprise/Alternatives

**4. Google Cloud** - Imagen 3 ("nano banana")
- **Cost**: ~$0.02-0.04/image
- **Why**: Google ecosystem, excellent prompt following
- **Models**: Imagen 3

**5. Stability AI** - Fallback option
- **Cost**: ~$0.035/image
- **Why**: Alternative to Flux/DALL-E
- **Models**: Stable Diffusion 3

---

## Detailed Setup Instructions

### 1. Together AI (FREE Tier) 🎉

**Sign up**: https://api.together.xyz

**Steps**:
```bash
# 1. Create account (no credit card required for free tier)
# 2. Navigate to: Settings → API Keys
# 3. Click "Create new API key"
# 4. Copy the key

# 5. Add to your environment
echo 'export TOGETHER_API_KEY="your_key_here"' >> ~/.zshrc
source ~/.zshrc

# 6. Verify
echo $TOGETHER_API_KEY
```

**Free Tier Limits**:
- Unlimited Flux Schnell generations
- No credit card required
- Perfect for testing

**Test Command**:
```bash
curl -X POST "https://api.together.xyz/v1/images/generations" \
  -H "Authorization: Bearer $TOGETHER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "black-forest-labs/FLUX.1-schnell-Free",
    "prompt": "A test image of a robot",
    "width": 1024,
    "height": 1024
  }'
```

---

### 2. Replicate (Production Quality)

**Sign up**: https://replicate.com

**Steps**:
```bash
# 1. Create account at https://replicate.com/signin
# 2. Navigate to: Account → API tokens
# 3. Copy your API token

# 4. Add to environment
echo 'export REPLICATE_API_KEY="your_token_here"' >> ~/.zshrc
source ~/.zshrc

# 5. Verify
echo $REPLICATE_API_KEY
```

**Pricing**:
- Flux Dev: $0.025/image
- Flux Pro: $0.055/image
- Pay only for what you use

**Test Command**:
```bash
curl -X POST "https://api.replicate.com/v1/predictions" \
  -H "Authorization: Bearer $REPLICATE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "black-forest-labs/flux-dev",
    "input": {
      "prompt": "A test image"
    }
  }'
```

---

### 3. Fal.ai (Fastest Flux Pro)

**Sign up**: https://fal.ai

**Steps**:
```bash
# 1. Create account at https://fal.ai
# 2. Navigate to: Dashboard → API Keys
# 3. Create new key

# 4. Add to environment
echo 'export FAL_API_KEY="your_key_here"' >> ~/.zshrc
source ~/.zshrc

# 5. Verify
echo $FAL_API_KEY
```

**Pricing**:
- Flux Pro: $0.05/image (fastest inference)
- Flux Schnell: $0.003/image
- SD3: varies

**Test Command**:
```bash
curl -X POST "https://fal.run/fal-ai/flux-pro" \
  -H "Authorization: Key $FAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A test image",
    "image_size": "square_hd"
  }'
```

---

### 4. Google Cloud (Imagen 3 / "nano banana")

**Setup**: https://cloud.google.com/vertex-ai/docs/generative-ai/image/overview

**Steps**:
```bash
# 1. Create Google Cloud account
# 2. Create new project or select existing
# 3. Enable Vertex AI API:
#    https://console.cloud.google.com/apis/library/aiplatform.googleapis.com

# 4. Install gcloud CLI (if not already)
brew install --cask google-cloud-sdk

# 5. Authenticate
gcloud auth login
gcloud auth application-default login

# 6. Set project
gcloud config set project YOUR_PROJECT_ID

# 7. Get API key OR use service account
# Option A: API Key (simpler)
#   - Go to: https://console.cloud.google.com/apis/credentials
#   - Create API key
echo 'export GOOGLE_API_KEY="your_key_here"' >> ~/.zshrc

# Option B: Service Account (more secure)
gcloud iam service-accounts keys create ~/google-cloud-key.json \
  --iam-account=YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com
echo 'export GOOGLE_APPLICATION_CREDENTIALS="$HOME/google-cloud-key.json"' >> ~/.zshrc

source ~/.zshrc
```

**Pricing**:
- Imagen 3: ~$0.02-0.04/image
- Pay per request

**Test Command**:
```bash
# Using API
curl -X POST \
  "https://us-central1-aiplatform.googleapis.com/v1/projects/YOUR_PROJECT/locations/us-central1/publishers/google/models/imagen-3:predict" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [
      {
        "prompt": "A test image"
      }
    ]
  }'
```

---

### 5. Stability AI (Stable Diffusion 3)

**Sign up**: https://platform.stability.ai

**Steps**:
```bash
# 1. Create account at https://platform.stability.ai/account
# 2. Add credits (minimum $10)
# 3. Navigate to: API Keys tab
# 4. Create new key

# 5. Add to environment
echo 'export STABILITY_API_KEY="your_key_here"' >> ~/.zshrc
source ~/.zshrc

# 6. Verify
echo $STABILITY_API_KEY
```

**Pricing**:
- SD3 Medium: $0.035/image
- SD3 Large: $0.065/image
- Prepaid credits required

**Test Command**:
```bash
curl -X POST "https://api.stability.ai/v2beta/stable-image/generate/sd3" \
  -H "Authorization: Bearer $STABILITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A test image",
    "output_format": "png"
  }'
```

---

## OpenAI (Already Configured)

You already have `OPENAI_API_KEY` configured for DALL-E 3 and future Sora 2 access.

**Verify**:
```bash
echo $OPENAI_API_KEY
```

**DALL-E 3 Test**:
```bash
curl https://api.openai.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "dall-e-3",
    "prompt": "A test image",
    "n": 1,
    "size": "1024x1024"
  }'
```

---

## Environment Variable Summary

Add these to your `~/.zshrc` or `~/.bashrc`:

```bash
# Visual Media Generation API Keys

# OpenAI (DALL-E 3, Sora 2)
export OPENAI_API_KEY="sk-..." # ✅ Already configured

# Together AI (Flux Schnell FREE)
export TOGETHER_API_KEY="..."  # 🎯 Setup first (FREE!)

# Replicate (Flux Dev/Pro)
export REPLICATE_API_KEY="..." # 💎 Setup second

# Fal.ai (Fastest Flux Pro)
export FAL_API_KEY="..."       # Optional

# Google Cloud (Imagen 3 / nano banana)
export GOOGLE_API_KEY="..."    # Optional
# OR
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/google-cloud-key.json"

# Stability AI (SD3)
export STABILITY_API_KEY="..." # Optional fallback
```

**Apply changes**:
```bash
source ~/.zshrc
```

---

## Verification Script

Save this as `check-media-apis.sh`:

```bash
#!/bin/bash

echo "🎬 Visual Media Generator - API Key Status"
echo "==========================================="
echo ""

check_api() {
  local name=$1
  local var=$2
  local status="❌ Not configured"

  if [ -n "${!var}" ]; then
    status="✅ Configured (${#!var} chars)"
  fi

  printf "%-30s %s\n" "$name:" "$status"
}

check_api "OpenAI (DALL-E 3)" "OPENAI_API_KEY"
check_api "Together AI (Flux FREE)" "TOGETHER_API_KEY"
check_api "Replicate (Flux Dev)" "REPLICATE_API_KEY"
check_api "Fal.ai (Flux Pro)" "FAL_API_KEY"
check_api "Google Cloud (Imagen)" "GOOGLE_API_KEY"
check_api "Stability AI (SD3)" "STABILITY_API_KEY"

echo ""
echo "📊 Recommendation:"
if [ -z "$TOGETHER_API_KEY" ]; then
  echo "  → Set up Together AI first (FREE Flux Schnell)"
  echo "  → https://api.together.xyz"
elif [ -z "$REPLICATE_API_KEY" ]; then
  echo "  → Set up Replicate next (Production quality)"
  echo "  → https://replicate.com"
else
  echo "  ✅ Ready for production image generation!"
fi
```

**Run it**:
```bash
chmod +x check-media-apis.sh
./check-media-apis.sh
```

---

## Restart Bifrost After Adding Keys

After configuring new API keys, restart the Bifrost gateway:

```bash
# Restart full Infinity stack
./tools/start-infinity-gateway.sh

# Or restart just Bifrost
pkill -f "bifrost"
cd tools/bifrost-cli
npm run start
```

---

## Cost Comparison Matrix

| Model | Provider | Cost/Image | Speed | Quality | Free Tier |
|-------|----------|------------|-------|---------|-----------|
| **Flux Schnell** | Together AI | $0.003 | ⚡⚡⚡ 2-3s | Good | ✅ Yes |
| **Flux Dev** | Replicate | $0.025 | ⚡⚡ 5-8s | Excellent | ❌ No |
| **Flux Pro** | Fal.ai | $0.05 | ⚡ 10-15s | Exceptional | ❌ No |
| **DALL-E 3** | OpenAI | $0.04-0.12 | ⚡⚡ 5-10s | Excellent | ❌ No |
| **Imagen 3** | Google | $0.02-0.04 | ⚡⚡ 5-10s | Excellent | ❌ No |
| **SD3** | Stability | $0.035 | ⚡⚡ 3-5s | Good-Excellent | ❌ No |

---

## Next Steps

1. ✅ Start with Together AI (FREE testing)
2. ✅ Add Replicate for production
3. ✅ Configure others as needed
4. ✅ Restart Bifrost gateway
5. ✅ Test Visual Media Generator agent

**Test command in Claude Code**:
```
Generate a test image using Flux Schnell
```

---

*Visual Media Generator - Complete API Setup Guide*
*Updated: 2025-11-03*
