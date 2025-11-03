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

    def process_and_save():
        try:
            # Process video
            from app.workflows.video_processor import VideoProcessingWorkflow
            workflow = VideoProcessingWorkflow()
            video_urls = workflow.process_uploaded_video(video_name, day_number)

            # Get existing content data
            from app.integrations.firestore_db import FirestoreDB
            from app.integrations.notion_api import NotionClient
            from app.integrations.slack_api import SlackNotifier

            settings = get_settings()
            db = FirestoreDB(settings.google_cloud_project)
            content_data = db.get_content_day(day_number)

            # Update with video URLs
            if content_data:
                content_data['videos'] = video_urls
                content_data['status'] = 'review'
            else:
                content_data = {'videos': video_urls, 'status': 'review'}

            db.save_content_day(day_number, content_data)

            # Create Notion review card
            notion = NotionClient()
            page_id = notion.create_review_card(day_number, content_data)

            # Save Notion page ID to Firestore
            content_data['notion_page_id'] = page_id
            db.save_content_day(day_number, content_data)

            # Notify
            slack = SlackNotifier(settings.slack_webhook_url)
            slack.send_message(
                f"✅ Day {day_number} ready for review!\n\n"
                f"Videos processed for all platforms.\n"
                f"Check Notion to review and approve."
            )

            logger.info(f"Video processing completed for Day {day_number}")

        except Exception as e:
            logger.error(f"Video processing failed: {str(e)}")

    background_tasks.add_task(process_and_save)

    return {
        "status": "processing",
        "message": f"Video for Day {day_number} is being processed"
    }

@app.post("/webhooks/notion-approved")
async def notion_approved(day_number: int, background_tasks: BackgroundTasks):
    """Triggered when content approved in Notion"""
    logger.info(f"Notion approval webhook received for Day {day_number}")

    def publish():
        try:
            from app.workflows.multiplatform import MultiPlatformPublisher
            publisher = MultiPlatformPublisher()
            results = publisher.publish_day(day_number)
            logger.info(f"Publishing results: {results}")
        except Exception as e:
            logger.error(f"Publishing failed: {str(e)}")

    background_tasks.add_task(publish)
    return {"status": "publishing", "day": day_number}

@app.post("/publish/day/{day_number}")
async def publish_day(day_number: int, background_tasks: BackgroundTasks):
    """Manual trigger to publish a specific day"""
    logger.info(f"Manual publish triggered for Day {day_number}")

    def publish():
        try:
            from app.workflows.multiplatform import MultiPlatformPublisher
            publisher = MultiPlatformPublisher()
            results = publisher.publish_day(day_number)
            logger.info(f"Publishing results: {results}")
        except Exception as e:
            logger.error(f"Publishing failed: {str(e)}")

    background_tasks.add_task(publish)
    return {"status": "publishing", "day": day_number}

@app.post("/workflows/overnight-prep")
async def overnight_prep(day_number: int):
    """
    Scheduled job - runs at 2 AM

    Args:
        day_number: Which day to prep (1-30)
    """
    logger.info(f"Overnight prep triggered for Day {day_number}")

    from app.workflows.overnight_prep import OvernightPrepWorkflow
    workflow = OvernightPrepWorkflow()
    success = workflow.run(day_number)

    if success:
        return {"status": "completed", "day": day_number}
    else:
        raise HTTPException(status_code=500, detail="Overnight prep failed")

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
