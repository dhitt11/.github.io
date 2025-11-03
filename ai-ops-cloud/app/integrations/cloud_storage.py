"""Google Cloud Storage Integration"""
import logging
from google.cloud import storage
from typing import BinaryIO
from pathlib import Path

logger = logging.getLogger(__name__)

class CloudStorageClient:
    """Google Cloud Storage operations"""

    def __init__(self, project_id: str, bucket_raw: str, bucket_processed: str):
        self.client = storage.Client(project=project_id)
        self.bucket_raw = self.client.bucket(bucket_raw)
        self.bucket_processed = self.client.bucket(bucket_processed)

    def upload_file(self, file_path: str, destination_blob_name: str, bucket_type: str = 'raw') -> str:
        """
        Upload file to Cloud Storage

        Args:
            file_path: Local file path
            destination_blob_name: Name in bucket
            bucket_type: 'raw' or 'processed'

        Returns:
            Public URL of uploaded file
        """
        bucket = self.bucket_raw if bucket_type == 'raw' else self.bucket_processed
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(file_path)
        logger.info(f"Uploaded {file_path} to {destination_blob_name}")

        # Make blob publicly readable
        blob.make_public()
        return blob.public_url

    def download_file(self, source_blob_name: str, dest_file_path: str, bucket_type: str = 'raw'):
        """
        Download file from Cloud Storage

        Args:
            source_blob_name: Name in bucket
            dest_file_path: Local destination path
            bucket_type: 'raw' or 'processed'
        """
        bucket = self.bucket_raw if bucket_type == 'raw' else self.bucket_processed
        blob = bucket.blob(source_blob_name)

        blob.download_to_filename(dest_file_path)
        logger.info(f"Downloaded {source_blob_name} to {dest_file_path}")

    def list_files(self, prefix: str = None, bucket_type: str = 'raw') -> list:
        """
        List files in bucket

        Args:
            prefix: Filter by prefix
            bucket_type: 'raw' or 'processed'

        Returns:
            List of blob names
        """
        bucket = self.bucket_raw if bucket_type == 'raw' else self.bucket_processed
        blobs = bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]

    def delete_file(self, blob_name: str, bucket_type: str = 'raw'):
        """
        Delete file from bucket

        Args:
            blob_name: Name of file to delete
            bucket_type: 'raw' or 'processed'
        """
        bucket = self.bucket_raw if bucket_type == 'raw' else self.bucket_processed
        blob = bucket.blob(blob_name)
        blob.delete()
        logger.info(f"Deleted {blob_name}")
