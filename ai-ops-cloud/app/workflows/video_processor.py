"""Video Processing Pipeline"""
import logging
from pathlib import Path
from typing import Dict
from app.integrations.cloud_storage import CloudStorageClient
from app.utils.video_ffmpeg import VideoProcessor
from app.config import get_settings

logger = logging.getLogger(__name__)

class VideoProcessingWorkflow:
    """Orchestrates video processing pipeline"""

    def __init__(self):
        settings = get_settings()
        self.storage = CloudStorageClient(
            project_id=settings.google_cloud_project,
            bucket_raw=settings.gcs_bucket_raw,
            bucket_processed=settings.gcs_bucket_processed
        )
        self.processor = VideoProcessor()

    def process_uploaded_video(self, video_blob_name: str, day_number: int) -> Dict[str, str]:
        """
        Process uploaded video for all platforms

        Args:
            video_blob_name: Name of video in raw bucket
            day_number: Which day (1-30)

        Returns:
            Dictionary with public URLs for each platform's video
        """
        logger.info(f"Processing video for Day {day_number}")

        # Create temporary paths
        temp_dir = Path("/tmp/videos")
        temp_dir.mkdir(exist_ok=True)

        raw_video_path = temp_dir / f"day_{day_number}_raw.mp4"

        # Download raw video from Cloud Storage
        self.storage.download_file(video_blob_name, str(raw_video_path), bucket_type='raw')

        # Process for each platform
        processed_videos = {}

        # LinkedIn
        linkedin_path = temp_dir / f"day_{day_number}_linkedin.mp4"
        self.processor.process_for_linkedin(str(raw_video_path), str(linkedin_path))
        linkedin_url = self.storage.upload_file(
            str(linkedin_path),
            f"day_{day_number}/linkedin.mp4",
            bucket_type='processed'
        )
        processed_videos['linkedin'] = linkedin_url
        logger.info(f"LinkedIn video processed: {linkedin_url}")

        # Facebook
        facebook_path = temp_dir / f"day_{day_number}_facebook.mp4"
        self.processor.process_for_facebook(str(raw_video_path), str(facebook_path))
        facebook_url = self.storage.upload_file(
            str(facebook_path),
            f"day_{day_number}/facebook.mp4",
            bucket_type='processed'
        )
        processed_videos['facebook'] = facebook_url
        logger.info(f"Facebook video processed: {facebook_url}")

        # Instagram
        instagram_path = temp_dir / f"day_{day_number}_instagram.mp4"
        self.processor.process_for_instagram(str(raw_video_path), str(instagram_path))
        instagram_url = self.storage.upload_file(
            str(instagram_path),
            f"day_{day_number}/instagram.mp4",
            bucket_type='processed'
        )
        processed_videos['instagram'] = instagram_url
        logger.info(f"Instagram video processed: {instagram_url}")

        # Twitter
        twitter_path = temp_dir / f"day_{day_number}_twitter.mp4"
        self.processor.process_for_twitter(str(raw_video_path), str(twitter_path))
        twitter_url = self.storage.upload_file(
            str(twitter_path),
            f"day_{day_number}/twitter.mp4",
            bucket_type='processed'
        )
        processed_videos['twitter'] = twitter_url
        logger.info(f"Twitter video processed: {twitter_url}")

        # Cleanup
        self.processor.cleanup_temp_files()

        logger.info(f"All videos processed for Day {day_number}")
        return processed_videos
