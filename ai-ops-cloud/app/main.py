from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.config import get_settings
from app.utils.logger import setup_logger

# Initialize FastAPI
app = FastAPI(title="AI Ops Builder", version="1.0.0")

# Setup logging
setup_logger()
logger = logging.getLogger(__name__)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AI Ops Builder"}

@app.post("/webhooks/video-uploaded")
async def video_uploaded(background_tasks: BackgroundTasks):
    """Triggered when video uploaded to Cloud Storage"""
    logger.info("Video upload webhook received")
    # Will implement in next prompt
    return {"status": "processing"}

@app.post("/webhooks/notion-approved")
async def notion_approved(background_tasks: BackgroundTasks):
    """Triggered when content approved in Notion"""
    logger.info("Notion approval webhook received")
    # Will implement in next prompt
    return {"status": "publishing"}

@app.post("/workflows/overnight-prep")
async def overnight_prep():
    """Scheduled job - runs at 2 AM"""
    logger.info("Overnight prep started")
    # Will implement in next prompt
    return {"status": "completed"}

@app.post("/workflows/monitor-engagement")
async def monitor_engagement():
    """Scheduled job - runs every 5 minutes"""
    logger.info("Engagement monitoring started")
    # Will implement in next prompt
    return {"status": "completed"}

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=8080)
