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
async def video_uploaded(video_name: str, day_number: int, background_tasks: BackgroundTasks):
    """
    Triggered when video uploaded to Cloud Storage

    Args:
        video_name: Name of uploaded video in bucket
        day_number: Which day (1-30)
    """
    logger.info(f"Video upload webhook received: {video_name} for Day {day_number}")

    def process_video():
        try:
            from app.workflows.video_processor import VideoProcessingWorkflow
            workflow = VideoProcessingWorkflow()
            video_urls = workflow.process_uploaded_video(video_name, day_number)

            # TODO: Save video URLs to Firestore (next prompt)
            # TODO: Update Notion with videos (next prompt)

            logger.info(f"Video processing completed: {video_urls}")
        except Exception as e:
            logger.error(f"Video processing failed: {str(e)}")

    background_tasks.add_task(process_video)

    return {
        "status": "processing",
        "message": f"Video for Day {day_number} is being processed"
    }

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

@app.get("/test/agents")
async def test_agents():
    """Test all agents"""
    from app.agents.visionary import VisionaryAgent
    from app.agents.operator import OperatorAgent
    from app.agents.implementer import ImplementerAgent
    from app.agents.sme import SMEAgent

    # Test with sample metrics
    sample_metrics = {
        "linkedin": {"impressions": 45000, "engagement": 1200},
        "facebook": {"impressions": 12000, "engagement": 300},
        "instagram": {"impressions": 8000, "engagement": 450},
        "twitter": {"impressions": 20000, "engagement": 600}
    }

    try:
        visionary = VisionaryAgent()
        vision = visionary.analyze_and_recommend(sample_metrics)

        operator = OperatorAgent()
        brief = operator.create_clear_picture(vision)

        implementer = ImplementerAgent()
        captions = implementer.generate_captions(brief)

        sme = SMEAgent()
        review = sme.review_content(captions, brief)

        return {
            "vision": vision,
            "brief": brief,
            "captions": captions,
            "review": review
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=8080)
