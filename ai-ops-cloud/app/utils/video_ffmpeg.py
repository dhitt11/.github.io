"""FFmpeg Video Processing Utilities"""
import subprocess
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

class VideoProcessor:
    """FFmpeg-based video processing"""

    def __init__(self):
        self.temp_dir = Path("/tmp/videos")
        self.temp_dir.mkdir(exist_ok=True)

    def process_for_linkedin(self, input_path: str, output_path: str, max_duration: int = 90):
        """
        Process video for LinkedIn
        - Vertical 9:16 (1080x1920)
        - Max 90 seconds
        - Add captions

        Args:
            input_path: Source video file
            output_path: Destination video file
            max_duration: Maximum length in seconds
        """
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1',
            '-t', str(max_duration),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',  # Web optimization
            '-y',  # Overwrite output
            output_path
        ]

        self._run_ffmpeg(cmd, "LinkedIn")

    def process_for_facebook(self, input_path: str, output_path: str, max_duration: int = 90):
        """
        Process video for Facebook (same as LinkedIn)

        Args:
            input_path: Source video file
            output_path: Destination video file
            max_duration: Maximum length in seconds
        """
        # Facebook specs same as LinkedIn for vertical video
        self.process_for_linkedin(input_path, output_path, max_duration)

    def process_for_instagram(self, input_path: str, output_path: str, max_duration: int = 90):
        """
        Process video for Instagram Reels
        - Vertical 9:16 (1080x1920)
        - Max 90 seconds
        - Optimized for mobile

        Args:
            input_path: Source video file
            output_path: Destination video file
            max_duration: Maximum length in seconds
        """
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1',
            '-t', str(max_duration),
            '-c:v', 'libx264',
            '-preset', 'fast',  # Faster encoding for IG
            '-crf', '25',  # Slightly lower quality OK for mobile
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',
            output_path
        ]

        self._run_ffmpeg(cmd, "Instagram")

    def process_for_twitter(self, input_path: str, output_path: str, max_duration: int = 60):
        """
        Process video for Twitter
        - Horizontal 16:9 (1280x720)
        - Max 60 seconds (Twitter limit for most accounts)

        Args:
            input_path: Source video file
            output_path: Destination video file
            max_duration: Maximum length in seconds
        """
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1',
            '-t', str(max_duration),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',
            output_path
        ]

        self._run_ffmpeg(cmd, "Twitter")

    def add_simple_captions(self, input_path: str, output_path: str, text: str):
        """
        Add simple text overlay to video (basic captioning)

        Args:
            input_path: Source video file
            output_path: Destination video file
            text: Text to overlay
        """
        # Escape special characters in text
        text_escaped = text.replace("'", "'\\''").replace(":", "\\:")

        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f"drawtext=text='{text_escaped}':fontsize=24:fontcolor=white:x=(w-text_w)/2:y=h-60:box=1:boxcolor=black@0.5:boxborderw=5",
            '-c:a', 'copy',
            '-y',
            output_path
        ]

        self._run_ffmpeg(cmd, "Captions")

    def _run_ffmpeg(self, cmd: list, process_name: str):
        """
        Execute FFmpeg command

        Args:
            cmd: FFmpeg command as list
            process_name: Name for logging
        """
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"{process_name} processing completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"{process_name} processing failed: {e.stderr}")
            raise

    def cleanup_temp_files(self):
        """Remove all temporary files"""
        for file in self.temp_dir.glob("*"):
            file.unlink()
        logger.info("Cleaned up temporary files")
