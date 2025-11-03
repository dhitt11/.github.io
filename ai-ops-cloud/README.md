# AI Ops Cloud Builder

Automated multi-platform social media content system using AI Operations principles.

## Architecture
- **Platform**: Google Cloud Run (serverless)
- **Database**: Firestore (NoSQL)
- **Storage**: Cloud Storage (videos)
- **AI**: Anthropic Claude Sonnet 4.5
- **Platforms**: LinkedIn, Facebook, Instagram, Twitter

## Cost Estimate
- **Monthly**: $0-5 (within free tiers)
- Google Cloud Run: Free tier (2M requests/month)
- Firestore: Free tier (1GB storage)
- Cloud Storage: Free tier (5GB)
- Anthropic API: ~$2-3/month (estimated)

## Setup Instructions
See deployment prompts for detailed setup.

## Quick Start
1. Clone repository
2. Copy `.env.example` to `.env`
3. Configure environment variables
4. Run `./scripts/setup_gcp.sh`
5. Run `./scripts/deploy.sh`

## Usage
1. Record video on PC
2. Upload to Cloud Storage bucket
3. Review in Notion (mobile-friendly)
4. Approve → Auto-publishes to all platforms
