
from google.cloud import storage
import os
from datetime import datetime

# Configure bucket name directly since we found it
BUCKET_NAME = "vrs-eco-backup-db"

def find_latest_backup():
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        
        blobs = list(bucket.list_blobs())
        
        if not blobs:
            print("No backups found in bucket.")
            return

        # Sort by time, newest last
        blobs.sort(key=lambda x: x.updated)
        
        print(f"Found {len(blobs)} files in {BUCKET_NAME}.")
        print("Latest 3 files:")
        for blob in blobs[-3:]:
            print(f" - {blob.name} ({blob.size/1024/1024:.2f} MB) - {blob.updated}")
            
        latest = blobs[-1]
        print(f"\nLAST_BACKUP={latest.name}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_latest_backup()
