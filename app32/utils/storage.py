import os
import uuid
import logging
from flask import current_app
from werkzeug.utils import secure_filename
from utils.gcs_utils import upload_to_gcs, delete_from_gcs, get_gcs_config

logger = logging.getLogger(__name__)

def save_file(file, subfolder=""):
    """
    Saves a file to local storage or GCS depending on configuration.
    Returns the relative path to be stored in the database.
    """
    if not file or not file.filename:
        return None
    
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    
    # Try GCS first if configured
    if get_gcs_config():
        gcs_path = upload_to_gcs(file, unique_name, subfolder=subfolder)
        if gcs_path:
            return gcs_path
            
    # Local fallback
    upload_base = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    upload_dir = os.path.join(upload_base, subfolder) if subfolder else upload_base
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)
    
    # Return path relative to UPLOAD_FOLDER
    rel_path = os.path.join(subfolder, unique_name).replace("\\", "/") if subfolder else unique_name
    return rel_path

def delete_file(relative_path):
    """
    Deletes a file from either GCS or local storage.
    """
    if not relative_path:
        return False
        
    if get_gcs_config():
        return delete_from_gcs(relative_path)
        
    # Local fallback
    try:
        upload_base = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        full_path = os.path.join(upload_base, relative_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
    except Exception as e:
        logger.error(f"Error deleting local file {relative_path}: {e}")
        
    return False

def get_file_url(relative_path):
    """
    Converts relative path from database to a public URL.
    """
    if not relative_path:
        return None
    
    # If it's a full URL already (e.g. stored in DB from GCS directly)
    if relative_path.startswith(('http://', 'https://')):
        return relative_path
        
    return f"/uploads/{relative_path}"
