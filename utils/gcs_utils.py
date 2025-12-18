#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
from flask import current_app

logger = logging.getLogger(__name__)

try:
    from google.cloud import storage
except ImportError:
    storage = None

def get_gcs_config():
    """Get GCS configuration from current_app config"""
    bucket_name = current_app.config.get("GCS_BUCKET")
    return bucket_name

def get_gcs_client():
    """Initialize GCS client if configured"""
    if not storage:
        return None
    
    bucket_name = get_gcs_config()
    if not bucket_name:
        return None
        
    try:
        # Uses GOOGLE_APPLICATION_CREDENTIALS or metadata server
        return storage.Client()
    except Exception as e:
        logger.error(f"Failed to initialize GCS Client: {e}")
        return None

def upload_to_gcs(storage_object, final_name, subfolder=""):
    """Helper to upload a file to GCS bucket"""
    bucket_name = get_gcs_config()
    client = get_gcs_client()
    
    if not client or not bucket_name:
        return None
        
    try:
        bucket = client.bucket(bucket_name)
        blob_path = f"{subfolder}/{final_name}" if subfolder else final_name
        blob = bucket.blob(blob_path)
        
        # Determine content type
        content_type = None
        if final_name.lower().endswith(".pdf"):
            content_type = "application/pdf"
        elif final_name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
            ext = final_name.lower().split(".")[-1]
            content_type = f"image/{ext}"
            if ext == "jpg": content_type = "image/jpeg"
            if ext == "svg": content_type = "image/svg+xml"

        # If it's a BytesIO or file-like object
        if hasattr(storage_object, 'seek'):
            storage_object.seek(0)
            blob.upload_from_file(storage_object, content_type=content_type)
        else:
            # Assume it's a path or bytes
            blob.upload_from_string(storage_object, content_type=content_type)
            
        logger.info(f"File uploaded to GCS: {blob_path}")
        return blob_path
    except Exception as e:
        logger.error(f"Error uploading to GCS: {e}")
        return None

def delete_from_gcs(blob_path):
    """Helper to delete a file from GCS bucket"""
    bucket_name = get_gcs_config()
    client = get_gcs_client()
    
    if not client or not bucket_name or not blob_path:
        return False
        
    try:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.delete()
        logger.info(f"File deleted from GCS: {blob_path}")
        return True
    except Exception as e:
        logger.error(f"Error deleting from GCS ({blob_path}): {e}")
        return False
