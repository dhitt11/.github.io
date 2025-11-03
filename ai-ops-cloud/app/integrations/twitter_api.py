"""Twitter API Integration"""
import tweepy
import logging
import requests

logger = logging.getLogger(__name__)

class TwitterPublisher:
    """Twitter API v2 for posting"""

    def __init__(self, api_key: str, api_secret: str, access_token: str, access_secret: str):
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret
        )

        # For media upload, need v1.1 API
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        self.api_v1 = tweepy.API(auth)

    def post_thread(self, tweets: list, video_url: str = None) -> dict:
        """
        Post thread to Twitter

        Args:
            tweets: List of tweet texts
            video_url: Optional video for first tweet

        Returns:
            Thread data with IDs
        """
        try:
            thread_ids = []
            reply_to_id = None

            for i, tweet_text in enumerate(tweets):
                # First tweet gets video
                if i == 0 and video_url:
                    # Download and upload video
                    media_id = self._upload_video(video_url)

                    response = self.client.create_tweet(
                        text=tweet_text,
                        media_ids=[media_id],
                        in_reply_to_tweet_id=reply_to_id
                    )
                else:
                    response = self.client.create_tweet(
                        text=tweet_text,
                        in_reply_to_tweet_id=reply_to_id
                    )

                tweet_id = response.data['id']
                thread_ids.append(tweet_id)
                reply_to_id = tweet_id

            logger.info(f"Posted Twitter thread: {len(thread_ids)} tweets")
            return {"success": True, "thread_ids": thread_ids}

        except Exception as e:
            logger.error(f"Twitter API error: {str(e)}")
            return {"success": False, "error": str(e)}

    def _upload_video(self, video_url: str) -> str:
        """Download and upload video to Twitter"""
        # Download video
        response = requests.get(video_url)
        video_path = "/tmp/twitter_video.mp4"

        with open(video_path, 'wb') as f:
            f.write(response.content)

        # Upload using v1.1 API
        media = self.api_v1.media_upload(video_path)
        return media.media_id_string
